# -*- coding: utf-8 -*-
"""This file is doing the article scraping"""

import datetime
import hashlib
import html
import math
import random
import re
import threading
import time
import urllib

import feedparser
import langid
import ratelimit
import requests  # type: ignore
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, F, Max, Q
from openai import OpenAI
from webpush import send_group_notification

from articles.models import Article, FeedPosition
from feeds.models import Feed, Publisher

from .google_news_decode import decode_google_news_url


def postpone(function):
    """
    Reusable decorator function to run any function async to Django User request - i.e. that the user does not
    have to wait for completion of function to get the requested view
    """

    def decorator(*args, **kwargs):
        t = threading.Thread(target=function, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()

    return decorator


def update_feeds():
    """Main function that refreshes/scrapes articles from article feed sources."""
    start_time = time.time()

    # delete feed positions of inactive feeds
    inactive_feeds = Feed.objects.filter(~Q(active=True))
    for feed in inactive_feeds:
        delete_feed_positions(feed=feed)

    all_articles = Article.objects.exclude(content_type="video")
    all_articles.update(min_feed_position=None)
    all_articles.update(max_importance=None)
    all_articles.update(min_article_relevance=None)

    # get acctive feeds
    feeds = Feed.objects.filter(active=True, feed_type="rss")
    if settings.TESTING:
        # when testing is turned on only fetch 10% of feeds to not having to wait too long
        feeds = [
            feeds[i] for i in range(0, len(feeds), len(feeds) // (len(feeds) // 10))
        ]

    added_articles = 0
    for feed in feeds:
        # added_articles += fetch_feed(feed)
        added_articles += fetch_feed_new(feed)

    # apply publisher feed position
    publishers = Publisher.objects.all()
    for publisher in publishers:
        articles = (
            Article.objects.filter(feedposition__feed__publisher__pk=publisher.pk)
            .exclude(min_feed_position__isnull=True)
            .exclude(min_article_relevance__isnull=True)
            .exclude(content_type="video")
            .annotate(feed_count=Count("feedposition"))
            .annotate(
                calc_rel_feed_pos=F("min_feed_position")
                * 1000
                / (F("max_importance") + 4)
            )
            .order_by(
                "-calc_rel_feed_pos",
                "feed_count",
            )
        )
        len_articles = len(articles)
        for i, article in enumerate(articles):
            setattr(article, "publisher_article_position", int(len_articles - i))
            setattr(
                article,
                "min_article_relevance",
                min(
                    float(
                        round(
                            (len_articles - i)
                            * float(getattr(article, "min_article_relevance")),
                            6,
                        )
                    ),
                    10_000,
                ),
            )
            article.save()

    # calculate next refesh time
    end_time = time.time()

    now = datetime.datetime.now()
    if now.hour >= 18 or now.hour < 6 or now.weekday() in [5, 6]:
        print(
            "No AI summaries are generated during non-business "
            "hours (i.e. between 18:00-6:00 and on Saturdays and Sundays)"
        )
    else:
        min_article_relevance = (
            Article.objects.filter(
                has_full_text=True, categories__icontains="FRONTPAGE"
            )
            .exclude(publisher__name__in=["Risk.net", "The Economist"])
            .exclude(min_article_relevance__isnull=True)
            .order_by("min_article_relevance")[:20]
            .aggregate(Max("min_article_relevance"))["min_article_relevance__max"]
        )
        articles_add_ai_summary = (
            Article.objects.filter(
                has_full_text=True,
                ai_summary__isnull=True,
                categories__icontains="FRONTPAGE",
                min_article_relevance__lte=min_article_relevance,
            )
            .exclude(publisher__name__in=["Risk.net", "The Economist"])
            .exclude(min_article_relevance__isnull=True)
            .order_by("min_article_relevance")
        )
        add_ai_summary(article_obj_lst=articles_add_ai_summary)

    old_articles = (
        Article.objects.filter(
            min_article_relevance__isnull=True,
            feedposition=None,
            added_date__lte=settings.TIME_ZONE_OBJ.localize(
                datetime.datetime.now() - datetime.timedelta(days=21)
            ),
        )
        .exclude(read_later=True)
        .exclude(archive=True)
    )
    if len(old_articles) > 0:
        print(f"Delete {len(old_articles)} old articles")
        old_articles.delete()
    else:
        print("No old articles to delete")

    print(
        f"Refreshed articles and added {added_articles} articles in"
        f" {int(end_time - start_time)} seconds"
    )

    # connection.close()


def calcualte_relevance(publisher, feed, feed_position, hash, pub_date):
    """
    This function calsucates the relvanec score for all artciles and videos depensing on user
    settings and article positions
    """
    random.seed(hash)

    random_int = random.randrange(0, 9) / 10000
    feed__importance = feed.importance  # 0-4
    feed__ordering = feed.feed_ordering  # r or d
    publisher__renowned = publisher.renowned  # -3-3
    # content_type = "art" if feed.feed_type == "rss" else "vid"
    # publisher_article_count = cache.get(
    #    f"feed_publisher_{content_type}_cnt_{feed.publisher.pk}"
    # )
    if pub_date is None:
        article_age = 3
    else:
        article_age = (
            settings.TIME_ZONE_OBJ.localize(datetime.datetime.now()) - pub_date
        ).total_seconds() / 3600

    factor_publisher__renowned = {
        3: 2 / 9,  # Top Publisher = 4.5x
        2: 4 / 6,  # Higly Renowned Publisher = 1.5x
        1: 5 / 6,  # Renowned Publisher = 1.2x
        0: 6 / 6,  # Regular Publisher = 1x
        -1: 8 / 6,  # Lesser-known Publisher = 0.75x
        -2: 10 / 6,  # Unknown Publisher = 0.6x
        -3: 12 / 6,  # Inaccurate Publisher = 0.5x
    }[publisher__renowned]

    # Publisher artcile ccount normalization
    # factor_article_normalization = max(min(100 / publisher_article_count, 3), 0.5)
    factor_article_normalization = 1

    factor_feed__importance = {
        4: 1 / 4,  # Lead Articles News: 4x
        3: 2 / 4,  # Breaking & Top News: 2x
        2: 3 / 4,  # Frontpage News: 1.3x
        1: 4 / 4,  # Latest News: 1x
        0: 5 / 4,  # Normal: 0.8x
    }[feed__importance]

    # age factor
    if feed.feed_type != "rss":  # videos
        factor_age = 10 / (1 + math.exp(-0.01 * article_age + 4)) + 1
    elif feed__ordering == "r":
        factor_age = 3 / (1 + math.exp(-0.25 * article_age + 4)) + 1
    else:  # d
        factor_age = 4 / (1 + math.exp(-0.25 * article_age + 4)) + 1

    article_relevance = round(
        # feed_position *
        factor_publisher__renowned
        * factor_article_normalization
        * factor_feed__importance
        * factor_age
        + random_int,
        6,
    )
    article_relevance = min(float(article_relevance), 999999.0)

    return int(feed__importance), float(article_relevance)


def delete_feed_positions(feed):
    """Deletes all feed positions of a respective feed"""
    all_feedpositions = feed.feedposition_set.all()
    all_feedpositions.delete()


@ratelimit.sleep_and_retry
@ratelimit.limits(calls=30, period=60)
def check_limit_openai():
    """Empty function just to check for calls to API"""
    # limit of 90k tokens per minute = 90k / 3k per request = 30 requets
    # limit of 3500 requests per minute
    # min(3.5k, 30) = 30 requests per minute
    return


def add_ai_summary(article_obj_lst):
    """Use OpenAI's ChatGPT API to get artcile summaries"""
    if settings.OPENAI_API_KEY is None:
        print("Not Requesting AI article summaries as OPENAI_API_KEY not set.")
    else:
        print(f"Requesting AI article summaries for {len(article_obj_lst)} articles.")

        # openai.api_key = settings.OPENAI_API_KEY
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        TOTAL_API_COST = (
            0
            if cache.get("OPENAI_API_COST_LAUNCH") is None
            else cache.get("OPENAI_API_COST_LAUNCH")
        )
        COST_TOKEN_INPUT = 0.0015
        COST_TOKEN_OUTPUT = 0.002
        NET_USD_TO_GROSS_GBP = 1.2 * 0.785
        token_cost = 0
        articles_summarized = 0

        for article_obj in article_obj_lst:
            logging = [
                str(datetime.datetime.now().isoformat()),
                str(article_obj.publisher.name),
                str(article_obj.pk),
                str(article_obj.min_article_relevance),
                str(article_obj.title),
            ]
            try:
                soup = BeautifulSoup(article_obj.full_text_html, "html5lib")
                article_text = " ".join(html.unescape(soup.text).split())
                # article_text = re.sub(r'\n+', '\n', article_text).strip()
                if len(article_text) > 3000 * 5:
                    article_text = article_text[: 3000 * 5]
                if len(article_text) / 5 < 500:
                    continue
                elif len(article_text) / 5 < 1000:
                    bullets = 2
                elif len(article_text) / 5 < 2000:
                    bullets = 3
                else:
                    bullets = 4
                check_limit_openai()
                completion = client.chat.completions.create(
                    # completion = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Summarize this article in {bullets} bullet"
                                f' points:\n"{article_text}"'
                            ),
                        }
                    ],
                )
                article_summary = completion["choices"][0]["message"]["content"]
                article_summary = article_summary.replace("- ", "<li>").replace(
                    "\n", "</li>\n"
                )
                article_summary = "<ul>\n" + article_summary + "</li>\n</ul>"
                token_cost += round(
                    (completion["usage"]["prompt_tokens"] * COST_TOKEN_INPUT)
                    + (completion["usage"]["completion_tokens"] * COST_TOKEN_OUTPUT),
                    4,
                )
                setattr(article_obj, "ai_summary", article_summary)
                article_obj.save()
                articles_summarized += 1
                logging.extend(["SUCCESS", str(token_cost)])
            except Exception as e:
                print(f"Error getting AI article summary for {article_obj}:", e)
                logging.extend(["ERROR", str(0)])

            with open(
                str(settings.BASE_DIR) + "/data/ai_summaries.csv", "a+"
            ) as myfile:
                myfile.write(";".join(logging) + "\n")

        THIS_RUN_API_COST = round(float(token_cost / 1000 * NET_USD_TO_GROSS_GBP), 4)
        TOTAL_API_COST += THIS_RUN_API_COST
        cache.set("OPENAI_API_COST_LAUNCH", TOTAL_API_COST, 3600 * 1000)
        print(
            f"Summarized {articles_summarized} articles costing"
            f" {THIS_RUN_API_COST} GBP. Total API cost since container launch"
            f" {TOTAL_API_COST} GBP."
        )


def fetch_feed_new(feed):
    """Fetch/update/scrape all articles for a specific source feed"""
    added_articles = 0

    feed_url = feed.url
    if "http://FEED-CREATOR.local" in feed_url:
        feed_url = feed_url.replace(
            "http://FEED-CREATOR.local", settings.FEED_CREATOR_URL
        )
    if "http://FULL-TEXT.local" in feed_url:
        feed_url = feed_url.replace("http://FULL-TEXT.local", settings.FULL_TEXT_URL)

    fetched_feed = feedparser.parse(feed_url)

    if len(fetched_feed.entries) > 0:
        delete_feed_positions(feed)

    for article_feed_position, scraped_article in enumerate(fetched_feed.entries):
        article_feed_position += 1

        ScrapedArticle_obj = ScrapedArticle(
            feed_entry=scraped_article, source_feed=feed
        )

        guid = ScrapedArticle_obj.final_guid
        full_text_fetch = ScrapedArticle_obj.prop_full_text_fetch

        if guid is None:
            print("Error no GUID without scrape_source()")

        # Check if artcile already exists
        matches = Article.objects.filter(guid=guid)
        if len(matches) == 0:
            hash = ScrapedArticle_obj.final_hash
            matches = Article.objects.filter(hash=hash)

        if len(matches) > 0:
            article_obj = matches[0]
            ScrapedArticle_obj.get_final_attributes()
            # check if artcile needs refreshing
            if (
                article_obj.importance_type == "breaking"
                or article_obj.content_type == "ticker"
                or (
                    article_obj.full_text_html is None
                    and full_text_fetch
                    and article_obj.image_url is None
                )
            ):
                if full_text_fetch:
                    ScrapedArticle_obj.scrape_source()
                # get article props and update if changed
                article_kwargs = ScrapedArticle_obj.get_final_attributes()
                for prop in [
                    "title",
                    "extract",
                    "importance_type",
                    "content_type",
                    "full_text_html",
                    "has_full_text",
                    "author",
                    "image_url",
                    "language",
                ]:
                    if (
                        prop in article_kwargs
                        and article_kwargs[prop] is not None
                        and article_kwargs[prop] != ""
                    ):
                        new_value = article_kwargs[prop]
                        current_value = getattr(article_obj, prop)
                        if new_value != current_value:
                            setattr(article_obj, prop, new_value)
                article_obj.save()
        else:
            if full_text_fetch:
                ScrapedArticle_obj.scrape_source()
            # add article
            article_kwargs = ScrapedArticle_obj.get_final_attributes()
            # add publisher is new one
            if type(article_kwargs["publisher"]) is dict:
                url = ".".join(article_kwargs["publisher"]["link"].split(".")[-2:])
                matching_publishers = Publisher.objects.filter(link__icontains=url)
                if len(matching_publishers) > 0:
                    article_kwargs["publisher"] = matching_publishers[0]
                else:
                    publisher_obj = Publisher(
                        **article_kwargs["publisher"], renowned=-2
                    )
                    publisher_obj.save()
                    article_kwargs["publisher"] = publisher_obj
            article_obj = Article(**article_kwargs)
            article_obj.save()
            added_articles += 1

        # Update article metrics
        (new_max_importance, new_min_article_relevance) = calcualte_relevance(
            publisher=feed.publisher,
            feed=feed,
            feed_position=article_feed_position,
            hash=guid,
            pub_date=ScrapedArticle_obj.final_pub_date,
        )
        new_categories = getattr(ScrapedArticle_obj, "final_categories", None)
        current_categories = getattr(article_obj, "categories", None)
        if new_categories is not None and new_categories != "":
            final_categories = current_categories
            for c in new_categories.split(";"):
                if c.lower() not in final_categories.lower():
                    final_categories += ";" + new_categories
            if final_categories[-1] != ";":
                final_categories += ";"
            setattr(article_obj, "categories", final_categories)
        article_obj.save()

        # Add feed position linking
        feed_position = FeedPosition(
            feed=feed,
            article=article_obj,
            position=article_feed_position,
            importance=new_max_importance,
            relevance=new_min_article_relevance,
        )
        feed_position.save()

        # check if important news for push notification
        now = datetime.datetime.now()
        notifications_sent = cache.get("notifications_sent", [])
        if (
            article_obj.pk not in notifications_sent
            and (
                article_obj.categories is None
                or "no push" not in str(article_obj.categories).lower()
            )
            and (
                (
                    "sidebar" in str(article_obj.categories).lower()
                    and article_obj.publisher.renowned >= 2
                )
                or (
                    "frontpage" in str(article_obj.categories).lower()
                    and article_obj.importance_type == "breaking"
                )
                or (
                    feed.importance == 4
                    and article_feed_position <= 3
                    and article_obj.publisher.renowned >= 2
                    and now.hour >= 6
                    and now.hour <= 19
                )
            )
            and (
                settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())
                - article_obj.added_date
            ).total_seconds()
            / 60
            < 15  # added less than 15min ago
            and (
                settings.TIME_ZONE_OBJ.localize(datetime.datetime.now())
                - article_obj.pub_date
            ).total_seconds()
            / (60 * 60)
            < 72  # published less than 72h/3d ago
        ):
            try:
                send_group_notification(
                    group_name="all",
                    payload={
                        "head": f"{article_obj.publisher.name}",
                        "body": f"{article_obj.title}",
                        "url": f"/view/{article_obj.pk}/",
                    },
                    ttl=60 * 90,  # keep 90 minutes on server
                )
                cache.set(
                    "notifications_sent",
                    notifications_sent + [article_obj.pk],
                    3600 * 1000,
                )
                print(
                    f"Web Push Notification sent for ({article_obj.pk})"
                    f" {article_obj.publisher.name} - {article_obj.title}"
                )
            except Exception as e:
                print(
                    "Error sending Web Push Notification for "
                    f"({article_obj.pk}) {article_obj.publisher.name} - {article_obj.title}: {e}"
                )

    print(
        f"Refreshed {feed} with {added_articles} new articles out of"
        f" {len(fetched_feed.entries)}"
    )
    return added_articles


@ratelimit.sleep_and_retry
@ratelimit.limits(calls=3, period=5)
def check_limit_full_text():
    """Empty function to limit url calls to not get blocked"""
    # every 5 seconds 3 calls
    return


class ScrapedArticle:
    """Class to scrape artcile and store all data with inteligent selction of final output attributes"""

    def __init__(self, feed_entry, source_feed):
        self.source_feed_obj = source_feed
        self.source_publisher_obj = source_feed.publisher
        self.feed_article_obj = feed_entry

        self.status_fetched_full_text = False
        self.status_calculated_final_props = False

        self.publisher_equal_source = None

        self.prop_unique_guid_method = (
            self.source_publisher_obj.unique_article_id.lower()
        )
        self.prop_feed_ordering = self.source_feed_obj.feed_ordering.lower()
        self.prop_full_text_fetch = self.source_feed_obj.full_text_fetch.upper() == "Y"

        # save all data already received from feedparser
        self.__use_source_data__()
        self.__use_feed_data__()
        self.final_guid = self.calculate_guid()
        final_link = (
            self.true_article_url_str
            if hasattr(self, "true_article_url_str")
            else self.feed_article_url_str
        )
        self.final_hash = (
            f"{hashlib.sha256(final_link.split('?')[0].encode('utf-8')).hexdigest()}"
        )

    def __use_source_data__(self):
        """Extract relevant data from source objects - i.e. source_feed_obj and source_publisher_obj"""
        self.status_calculated_final_props = False
        self.source_feed_url_str = self.source_feed_obj.url
        self.source_feed_url_parsed = urllib.parse.urlparse(self.source_feed_url_str)
        self.source_feed_categories = (
            ""
            if self.source_feed_obj.source_categories is None
            else ";".join(
                [
                    i
                    for i in self.source_feed_obj.source_categories.split(";")
                    if i != ""
                ]
            )
        )
        self.source_publisher_name = self.source_publisher_obj.name
        self.source_publisher_pk = self.source_publisher_obj.pk
        self.source_publisher_url_str = self.source_publisher_obj.link
        self.source_publisher_url_parsed = urllib.parse.urlparse(
            self.source_publisher_url_str
        )
        self.source_publisher_paywall = self.source_publisher_obj.paywall
        self.source_publisher_language = self.source_publisher_obj.language

    def __use_feed_data__(self):
        """Extract relevant data from feed scraper object - i.e. feed_article_obj"""
        self.status_calculated_final_props = False

        # copy normal atributes that don't require a special logic
        for target_attr, obj_attr in {
            "feed_article_title": "title",
            "feed_article_url_str": "link",
            "feed_article_guid": "id",
            "feed_article_guid_is_url": "guidislink",
            "feed_article_pub_date": "published_parsed",
            "feed_article_updated_date": "updated_parsed",
            "feed_article_author": "author",
        }.items():
            if hasattr(self.feed_article_obj, obj_attr):
                setattr(self, target_attr, getattr(self.feed_article_obj, obj_attr))

        # if article has url parse it
        if hasattr(self, "feed_article_url_str"):
            self.feed_article_url_parsed = urllib.parse.urlparse(
                self.feed_article_url_str
            )

        # special logic for "image"/"media" attribute
        if hasattr(self.feed_article_obj, "media_content"):
            tmp = [
                i["url"]
                for i in self.feed_article_obj.media_content
                if "image" in i["type"]
            ]
            if len(tmp) > 0:
                self.feed_article_image_url = tmp[0]

        # special logic for "tags"/"categories" attribute
        if hasattr(self.feed_article_obj, "tags"):
            self.feed_article_categories = ";".join(
                [i["term"] for i in self.feed_article_obj.tags]
            )

        # special logic for "extract" attribute
        if hasattr(self.feed_article_obj, "extract"):
            # check if extract is in html or plain text
            if (
                hasattr(self.feed_article_obj, "extract_detail")
                and hasattr(self.feed_article_obj.extract_detail, "type")
                and "html" in str(self.feed_article_obj.extract_detail.type).lower()
            ):
                # is html
                self.feed_article_extract_html = self.feed_article_obj.extract
                self.feed_article_extract_text = BeautifulSoup(
                    self.feed_article_extract_html, features="lxml"
                ).get_text()
            else:
                # is plain text
                self.feed_article_extract_text = BeautifulSoup(
                    self.feed_article_obj.extract, features="lxml"
                ).get_text()
                self.feed_article_extract_html = (
                    f"<p>{self.feed_article_obj.extract}</p>"
                )

        # special logic for "source" attribute
        if hasattr(self.feed_article_obj, "source"):
            self.feed_publisher_name = self.feed_article_obj.source["title"]
            self.feed_publisher_url_str = self.feed_article_obj.source["href"]
            self.feed_publisher_obj = {
                "name": self.feed_publisher_name,
                "link": self.feed_publisher_url_str,
            }
            self.feed_publisher_url_parsed = urllib.parse.urlparse(
                self.feed_publisher_url_str
            )
            source_main_domain = (
                str(self.source_feed_url_parsed.netloc).split(".")[-2].lower()
            )
            feed_main_domain = (
                str(self.feed_publisher_url_parsed.netloc).split(".")[-2].lower()
            )
            if (
                source_main_domain in feed_main_domain
                or feed_main_domain in source_main_domain
            ):
                self.publisher_equal_source = True
            else:
                self.publisher_equal_source = False
                # if google news decrypt url
                if "google" in source_main_domain:
                    self.true_article_url_str = decode_google_news_url(
                        self.feed_article_url_str
                    )
                    self.true_article_url_parsed = urllib.parse.urlparse(
                        self.true_article_url_str
                    )

        # special logic for "content"/"body" attribute
        if hasattr(self.feed_article_obj, "content"):
            self.feed_article_body_html = "\n\n".join(
                [
                    i.value if "html" in str(i.type).lower() else f"<p>{i.value}</p>"
                    for i in self.feed_article_obj.content
                ]
            )
            self.feed_article_body_text = "\n\n".join(
                [
                    (
                        BeautifulSoup(i.value, features="lxml").get_text()
                        if "html" in str(i.type).lower()
                        else i.value
                    )
                    for i in self.feed_article_obj.content
                ]
            )
            self.feed_article_body_cnt = len(
                re.findall(r"\S+", self.feed_article_body_text)
            )

        # special logic for language attribute extraction
        if (
            hasattr(self.feed_article_obj, "extract_detail")
            and hasattr(self.feed_article_obj.extract_detail, "language")
            and self.feed_article_obj.extract_detail.language is not None
        ):
            self.feed_article_language = self.feed_article_obj.extract_detail.language
        elif (
            hasattr(self.feed_article_obj, "title_detail")
            and hasattr(self.feed_article_obj.title_detail, "language")
            and self.feed_article_obj.title_detail.language is not None
        ):
            self.feed_article_language = self.feed_article_obj.title_detail.language

    def scrape_source(self):
        """Use full-text scraper to get additional data beyond the RSS feed"""
        check_limit_full_text()  # url request limit of 3 calls every 5 seconds to not get blocked
        article_url = (
            self.true_article_url_str
            if hasattr(self, "true_article_url_str")
            else self.feed_article_url_str
        )
        request_url = f'{settings.FULL_TEXT_URL}extract.php?url={urllib.parse.quote(article_url, safe="")}'
        response = requests.get(request_url)
        if response.status_code == 200:
            self.status_fetched_full_text = True
            self.status_calculated_final_props = False
            try:
                full_text_data = response.json()

                for attr in ["title", "og_title", "twitter_title"]:
                    if (
                        attr in full_text_data
                        and full_text_data[attr] is not None
                        and full_text_data[attr] != ""
                    ):
                        self.scrape_article_title = full_text_data[attr]
                        break

                for attr in ["og_image", "twitter_image"]:
                    if (
                        attr in full_text_data
                        and full_text_data[attr] is not None
                        and full_text_data[attr] != ""
                    ):
                        self.scrape_article_image_url = full_text_data[attr]
                        break

                for attr in ["og_description", "twitter_description", "excerpt"]:
                    if (
                        attr in full_text_data
                        and full_text_data[attr] is not None
                        and full_text_data[attr] != ""
                    ):
                        self.scrape_article_extract_text = full_text_data[attr]
                        self.scrape_article_extract_html = (
                            f"<p>{self.scrape_article_extract_text}</p>"
                        )
                        break

                for target_attr, src_attr in [
                    ("article_language", "language"),
                    ("article_author", "author"),
                    ("article_body_cnt", "word_count"),
                ]:
                    if (
                        src_attr in full_text_data
                        and full_text_data[src_attr] is not None
                        and full_text_data[src_attr] != ""
                    ):
                        setattr(self, f"scrape_{target_attr}", full_text_data[src_attr])

                if (
                    "date" in full_text_data
                    and full_text_data["date"] is not None
                    and full_text_data["date"] != ""
                ):
                    self.scrape_article_pub_date = time.strptime(
                        full_text_data["date"], "%Y-%m-%dT%H:%M:%S%z"
                    )

                if (
                    "content" in full_text_data
                    and full_text_data["content"] is not None
                    and full_text_data["content"] != ""
                ):
                    self.scrape_article_body_html = full_text_data["content"]
                    self.scrape_article_body_text = BeautifulSoup(
                        self.scrape_article_body_html, features="lxml"
                    ).get_text()

            except Exception:
                print(
                    f"Error scraping full-text from for {self.source_publisher_name}:"
                    f' "{self.feed_article_title}" from "{article_url}"'
                )
                return

        else:
            print(
                f"Error scraping full-text from for {self.source_publisher_name}:"
                f' "{self.feed_article_title}" from "{article_url}"'
            )

    def __html_body_clean_up__(self):
        """Clean up the html body/full text"""
        if (
            hasattr(self, "final_full_text_html")
            and self.final_full_text_html is not None
            and len(self.final_full_text_html) > 20
        ):
            soup = BeautifulSoup(self.final_full_text_html, "html.parser")
            for i, img in enumerate(soup.find_all("img")):
                img[
                    "style"
                ] = "max-width: 100%; max-height: 80vh; width: auto; height: auto;"
                if img["src"] == "src":
                    if hasattr(img, "data-url"):
                        img["src"] = str(getattr(img, "data-url")).replace(
                            "${formatId}", "906"
                        )
                    elif hasattr(img, "data-src"):
                        img["src"] = getattr(img, "data-src")
                if hasattr(img, "srcset"):
                    img["srcset"] = ""
                img["referrerpolicy"] = "no-referrer"
                if (
                    i == 0
                    and hasattr(self, "final_image_url")
                    and self.final_image_url.lower() in img["src"].lower()
                ):
                    img.decompose()
            for figure in soup.find_all("figure"):
                figure["class"] = "figure"
            for figcaption in soup.find_all("figcaption"):
                figcaption["class"] = "figure-caption"
            for span in soup.find_all("span", attrs={"data-caps": "initial"}):
                span["class"] = "h3"
            for a in soup.find_all("a"):
                a["target"] = "_blank"
                a["referrerpolicy"] = "no-referrer"
            for link in soup.find_all("link"):
                if link is not None:
                    link.decompose()
            for form in soup.find_all("form"):
                if form is not None:
                    form.decompose()
            for input in soup.find_all("input"):
                if input is not None:
                    input.decompose()
            for button in soup.find_all("button"):
                if button is not None:
                    button.decompose()
            for meta in soup.find_all("meta"):
                if meta is not None:
                    meta.decompose()
            for noscript in soup.find_all("noscript"):
                if noscript is not None:
                    noscript.name = "div"
            for div_type, id in [
                ("div", "barrierContent"),
                ("div", "nousermsg"),
                ("div", "trial_print_message"),
                ("div", "print_blocked_message"),
                ("div", "copy_blocked_message"),
                ("button", "toolbar-item-parent-share-2909"),
                ("button", "CreateFreeAccountButton-buttonContainer"),
                ("ul", "toolbar-item-dropdown-share-2909"),
            ]:
                div = soup.find(div_type, id=id)
                if div is not None:
                    div.decompose()
            self.final_full_text_html = soup.prettify()

    def calculate_guid(self):
        """Function which calculates the Unique GUID"""
        if self.prop_unique_guid_method.lower() == "guid" and hasattr(
            self, "feed_article_guid"
        ):
            return f"{self.source_publisher_pk}_{self.feed_article_guid}"
        elif self.prop_unique_guid_method.lower() == "title":
            self.__calculate_final_value__(
                final_attr_name="final_title",
                feed_attr_name="feed_article_title",
                scrape_attr_name="scrape_article_title",
            )
            return f"{self.source_publisher_pk}_{hashlib.sha256(self.final_title.encode('utf-8')).hexdigest()}"
        else:  # self.prop_unique_guid_method.lower() == "url":
            self.__calculate_final_value__(
                final_attr_name="final_link",
                feed_attr_name="feed_article_url_str",
                scrape_attr_name="true_article_url_str",
            )
            return (
                f"{self.source_publisher_pk}_"
                f"{hashlib.sha256(self.final_link.split('?')[0].encode('utf-8')).hexdigest()}"
            )

    def __calculate_final_value__(
        self, final_attr_name, feed_attr_name, scrape_attr_name
    ):
        """Creates the final output attributes by seleting the best data available"""
        if (
            self.publisher_equal_source is False
            and hasattr(self, scrape_attr_name)
            and getattr(self, scrape_attr_name) is not None
            and getattr(self, scrape_attr_name) != ""
        ):
            setattr(self, final_attr_name, getattr(self, scrape_attr_name))
        elif (
            hasattr(self, feed_attr_name)
            and getattr(self, feed_attr_name) is not None
            and getattr(self, feed_attr_name) != ""
        ):
            setattr(self, final_attr_name, getattr(self, feed_attr_name))
        elif (
            hasattr(self, scrape_attr_name)
            and getattr(self, scrape_attr_name) is not None
            and getattr(self, scrape_attr_name) != ""
        ):
            setattr(self, final_attr_name, getattr(self, scrape_attr_name))

    def calculate_final_values(self):
        """Creates/updates the final article props that are outputted named 'final_'."""
        # Already updated
        if self.status_calculated_final_props:
            return None

        # Publisher
        self.__calculate_final_value__(
            final_attr_name="final_publisher",
            feed_attr_name="source_publisher_obj",
            scrape_attr_name="feed_publisher_obj",
        )

        # Title
        self.__calculate_final_value__(
            final_attr_name="final_title",
            feed_attr_name="feed_article_title",
            scrape_attr_name="scrape_article_title",
        )
        # Remove Publisher Name from Title if included
        if hasattr(self, "feed_publisher_name"):
            potential_inluded_name = f" - {self.feed_publisher_name}"
            if potential_inluded_name in self.final_title:
                self.final_title = self.final_title.replace(potential_inluded_name, "")

            # Summary / Extract
        self.__calculate_final_value__(
            final_attr_name="final_extract",
            feed_attr_name="feed_article_extract_text",
            scrape_attr_name="scrape_article_extract_text",
        )
        self.final_has_extract = (
            (
                self.final_extract is None
                or self.final_extract == ""
                or self.final_extract == "None"
            )
            if hasattr(self, "final_extract")
            else False
        )

        # Full text / Body

        scrape_article_body_cnt = (
            self.scrape_article_body_cnt
            if hasattr(self, "scrape_article_body_cnt")
            else 0
        )
        feed_article_body_cnt = (
            self.feed_article_body_cnt if hasattr(self, "feed_article_body_cnt") else 0
        )

        if feed_article_body_cnt == 0 and scrape_article_body_cnt == 0:
            body_cnt = 0
            body_text = ""
        elif scrape_article_body_cnt != 0 and (
            feed_article_body_cnt == 0 or self.publisher_equal_source is False
        ):
            self.final_full_text_html = self.scrape_article_body_html
            body_text = self.scrape_article_body_text
            body_cnt = scrape_article_body_cnt
            self.final_full_text_text = body_text
        elif feed_article_body_cnt != 0 and scrape_article_body_cnt == 0:
            self.final_full_text_html = self.feed_article_body_html
            body_text = self.feed_article_body_text
            body_cnt = feed_article_body_cnt
            self.final_full_text_text = body_text
        elif (feed_article_body_cnt * 1.5 < scrape_article_body_cnt) or (
            feed_article_body_cnt * 100 < scrape_article_body_cnt
        ):
            self.final_full_text_html = self.scrape_article_body_html
            body_text = self.scrape_article_body_text
            body_cnt = scrape_article_body_cnt
            self.final_full_text_text = body_text
        else:
            self.final_full_text_html = self.feed_article_body_html
            body_text = self.feed_article_body_text
            body_cnt = feed_article_body_cnt
            self.final_full_text_text = body_text

        if body_cnt > 80:
            self.final_has_full_text = True
        else:
            self.final_has_full_text = False

        # News type
        BREAKING_NEWS_KEYWORDS = [
            "breaking news",
            "liveticker",
            "liveblog",
            "live blog",
            "developing story",
        ]
        if (
            (
                hasattr(self, "final_title")
                and any([i in self.final_title.lower() for i in BREAKING_NEWS_KEYWORDS])
            )
            or (
                hasattr(self, "final_extract")
                and any(
                    [i in self.final_extract.lower() for i in BREAKING_NEWS_KEYWORDS]
                )
            )
            or (any([i in body_text.lower() for i in BREAKING_NEWS_KEYWORDS]))
        ):
            self.final_content_type = "ticker"
            self.final_importance_type = "breaking"
        else:
            self.final_content_type = "article"
            self.final_importance_type = "normal"

        # Language
        if (
            hasattr(self, "feed_article_language")
            and len(self.feed_article_language) > 0
            and len(self.feed_article_language) < 6
        ):
            self.final_language = self.feed_article_language
        elif (
            hasattr(self, "scrape_article_language")
            and len(self.scrape_article_language) > 0
            and len(self.scrape_article_language) < 6
        ):
            self.final_language = self.scrape_article_language
        elif (
            hasattr(self, "source_publisher_language")
            and len(self.source_publisher_language) > 0
            and len(self.source_publisher_language) < 6
        ):
            self.final_language = self.source_publisher_language
        else:
            lang = langid.classify(f"{self.final_title}\n{self.final_extract}")
            self.final_language = lang[0]

        # URL/Link
        self.__calculate_final_value__(
            final_attr_name="final_link",
            feed_attr_name="feed_article_url_str",
            scrape_attr_name="true_article_url_str",
        )

        # Author
        self.__calculate_final_value__(
            final_attr_name="final_author",
            feed_attr_name="feed_article_author",
            scrape_attr_name="scrape_article_author",
        )

        # Image URL
        self.__calculate_final_value__(
            final_attr_name="final_image_url",
            feed_attr_name="feed_article_image_url",
            scrape_attr_name="scrape_article_image_url",
        )

        # Pub Date
        self.__calculate_final_value__(
            final_attr_name="final_pub_date",
            feed_attr_name="feed_article_pub_date",
            scrape_attr_name="scrape_article_pub_date",
        )
        if not hasattr(self, "final_pub_date"):
            self.final_pub_date = settings.TIME_ZONE_OBJ.localize(
                datetime.datetime.now()
            )
            print(f"Warning no pub_date for {self.final_publisher}")

        # Categories
        feed_article_categories = (
            ";".join([i for i in self.feed_article_categories.split(";") if i != ""])
            if hasattr(self, "feed_article_categories")
            else ""
        )
        source_feed_categories = (
            ";".join([i for i in self.source_feed_categories.split(";") if i != ""])
            if hasattr(self, "source_feed_categories")
            else ""
        )
        self.final_categories = (
            source_feed_categories
            + (
                ";"
                if len(feed_article_categories) > 0 and len(source_feed_categories) > 0
                else ""
            )
            + feed_article_categories
        )

        self.__html_body_clean_up__()
        self.final_guid = self.calculate_guid()

        self.status_calculated_final_props = True

    def get_final_attributes(self):
        """Output final attributes in dictionary to use with Django"""
        self.calculate_final_values()
        out_dict = {}
        for k, v in self.__dict__.items():
            if "final_" == k[:6]:
                if type(v) is time.struct_time:
                    v = datetime.datetime.fromtimestamp(time.mktime(v))
                    v = settings.TIME_ZONE_OBJ.localize(v)
                    setattr(self, k, v)
                out_dict[k[6:]] = v
        self.output_dict = out_dict
        return self.output_dict
