import datetime
import hashlib
import re
import time
import urllib

import langid
import requests
from bs4 import BeautifulSoup
from django.conf import settings

from .google_news_decode import decode_google_news_url

# class DummyObj:
#     def __init__(self, **kwargs):
#         for k, v in kwargs.items():
#             setattr(self, k, v)
#
# def flatten_extend(matrix):
#     flat_list = []
#     for row in matrix:
#         flat_list.extend(row)
#     return flat_list
#
#
# def dummy_test_news_feed():
#     publishers = {
#         "FT": DummyObj(
#             pk=1, name="Financial Times", link="www.ft.com", paywall="Y", unique_article_id="guid", language="en"
#         ),
#         "Tagesschau": DummyObj(
#             pk=2,
#             name="Tagesschau",
#             link="http://www.tagesschau.de",
#             paywall="N",
#             unique_article_id="url",
#             language="de",
#         ),
#         "Google News": DummyObj(
#             pk=3, name="Google News", link="http://news.google.com", paywall="N", unique_article_id="url",
#             language=None
#         ),
#         "The Verge": DummyObj(
#             pk=4, name="The Verge", link="http://www.theverge.com", paywall="N", unique_article_id="url",
#             language="en"
#         ),
#         "RND": DummyObj(
#             pk=5, name="The Verge", link="http://www.rdn.de", paywall="N", unique_article_id="url", language="de"
#         ),
#         "TechCrunch": DummyObj(
#             pk=6, name="TechCrunch", link="http://www.rdn.de", paywall="N", unique_article_id="url", language=""
#         ),
#     }
#
#     feeds = {
#         "FT Home": DummyObj(
#             name="Homepage",
#             publisher=publishers["FT"],
#             url="https://www.ft.com/rss/home/international",
#             feed_ordering="r",
#             full_text_fetch="Y",
#             source_categories="frontpage",
#         ),
#         "Tagesschau Home": DummyObj(
#             name="Startseite",
#             publisher=publishers["Tagesschau"],
#             url="https://www.tagesschau.de/index~rss2.xml",
#             feed_ordering="d",
#             full_text_fetch="Y",
#             source_categories="frontpage",
#         ),
#         'Search "Hedge Funds"': DummyObj(
#             name='Search "Hedge Funds"',
#             publisher=publishers["Google News"],
#             url="https://news.google.com/rss/search?q=hedge+fund",
#             feed_ordering="d",
#             full_text_fetch="Y",
#             source_categories="google news;hedge funds;funds;sidebar",
#         ),
#         "Verge Home": DummyObj(
#             name="Home",
#             publisher=publishers["The Verge"],
#             url="http://www.theverge.com/rss/full.xml",
#             feed_ordering="r",
#             full_text_fetch="Y",
#             source_categories="tech;",
#         ),
#         "RND Home": DummyObj(
#             name="Home",
#             publisher=publishers["RND"],
#             url="https://www.rnd.de/arc/outboundfeeds/rss/category/politik/",
#             feed_ordering="r",
#             full_text_fetch="Y",
#             source_categories="",
#         ),
#         "TechCrunch Home": DummyObj(
#             name="Home",
#             publisher=publishers["TechCrunch"],
#             url="https://techcrunch.com/feed/",
#             feed_ordering="r",
#             full_text_fetch="Y",
#             source_categories="tech",
#         ),
#     }
#
#     fetched_feed_google = feedparser.parse(feeds['Search "Hedge Funds"'].url)
#     fetched_feed_ft = feedparser.parse(feeds["FT Home"].url)
#     fetched_feed_tagesschau = feedparser.parse(feeds["Tagesschau Home"].url)
#     fetched_feed_verge = feedparser.parse(feeds["Verge Home"].url)
#     fetched_feed_rnd = feedparser.parse(feeds["RND Home"].url)
#     fetched_feed_tc = feedparser.parse(feeds["TechCrunch Home"].url)
#
#     articles = flatten_extend(
#         [
#             [
#                 dict(feed_entry=fetched_feed_google.entries[i], source_feed=feeds['Search "Hedge Funds"']),
#                 dict(feed_entry=fetched_feed_ft.entries[i], source_feed=feeds["FT Home"]),
#                 dict(feed_entry=fetched_feed_tagesschau.entries[i], source_feed=feeds["Tagesschau Home"]),
#                 dict(feed_entry=fetched_feed_verge.entries[i], source_feed=feeds["Verge Home"]),
#                 dict(feed_entry=fetched_feed_rnd.entries[i], source_feed=feeds["RND Home"]),
#                 dict(feed_entry=fetched_feed_tc.entries[i], source_feed=feeds["TechCrunch Home"]),
#             ]
#             for i in range(10)
#         ]
#     )
#
#     for article in articles:
#         Artcile_obj = ScrapedArticle(**article)
#
#         guid = Artcile_obj.final_guid
#         full_text_fetch = Artcile_obj.prop_full_text_fetch
#
#         if guid is None:
#             print("Error no GUID without scrape_source()")
#
#         # check if article already exists
#         matching_articles = []
#
#         if len(matching_articles) == 0:
#             if full_text_fetch:
#                 Artcile_obj.scrape_source()
#
#         out = Artcile_obj.get_final_attributes()
#
#         print("")


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

        # special logic for "summary" attribute
        if hasattr(self.feed_article_obj, "summary"):
            # check if summary is in html or plain text
            if (
                hasattr(self.feed_article_obj, "summary_detail")
                and hasattr(self.feed_article_obj.summary_detail, "type")
                and "html" in str(self.feed_article_obj.summary_detail.type).lower()
            ):
                # is html
                self.feed_article_summary_html = self.feed_article_obj.summary
                self.feed_article_summary_text = BeautifulSoup(
                    self.feed_article_summary_html, features="lxml"
                ).get_text()
            else:
                # is plain text
                self.feed_article_summary_text = BeautifulSoup(
                    self.feed_article_obj.summary, features="lxml"
                ).get_text()
                self.feed_article_summary_html = (
                    f"<p>{self.feed_article_obj.summary}</p>"
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
            hasattr(self.feed_article_obj, "summary_detail")
            and hasattr(self.feed_article_obj.summary_detail, "language")
            and self.feed_article_obj.summary_detail.language is not None
        ):
            self.feed_article_language = self.feed_article_obj.summary_detail.language
        elif (
            hasattr(self.feed_article_obj, "title_detail")
            and hasattr(self.feed_article_obj.title_detail, "language")
            and self.feed_article_obj.title_detail.language is not None
        ):
            self.feed_article_language = self.feed_article_obj.title_detail.language

    def scrape_source(self):
        """Use full-text scraper to get additional data beyond the RSS feed"""
        article_url = (
            self.true_article_url_str
            if hasattr(self, "true_article_url_str")
            else self.feed_article_url_str
        )
        request_url = (
            f'{settings.FULL_TEXT_URL}extract.php?url={urllib.parse.quote(article_url, safe="")}'
        )
        response = requests.get(request_url)
        if response.status_code == 200:
            self.status_fetched_full_text = True
            self.status_calculated_final_props = False
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
                    self.scrape_article_summary_text = full_text_data[attr]
                    self.scrape_article_summary_html = (
                        f"<p>{self.scrape_article_summary_text}</p>"
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

        else:
            print(
                f"Error scraping full-text from for {self.source_publisher_name}:"
                f' "{self.feed_article_title}" from "{article_url}"'
            )

    def __html_body_clean_up__(self):
        """Clean up the html body/full text"""
        if (
            hasattr(self, "final_full_text")
            and self.final_full_text is not None
            and len(self.final_full_text) > 20
        ):
            soup = BeautifulSoup(self.final_full_text, "html.parser")
            for img in soup.find_all("img"):
                img["style"] = (
                    "max-width: 100%; max-height: 80vh; width: auto; height: auto;"
                )
                if img["src"] == "src":
                    if "data-url" in img:
                        img["src"] = img["data-url"].replace("${formatId}", "906")
                    elif "data-src" in img:
                        img["src"] = img["data-src"]
                img["referrerpolicy"] = "no-referrer"
            for a in soup.find_all("a"):
                a["target"] = "_blank"
                a["referrerpolicy"] = "no-referrer"
            for link in soup.find_all("link"):
                if link is not None:
                    link.decompose()
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
                ("ul", "toolbar-item-dropdown-share-2909"),
            ]:
                div = soup.find(div_type, id=id)
                if div is not None:
                    div.decompose()
            self.final_full_text = soup.prettify()

    def calculate_guid(self):
        """Function which calculates the Unique GUID"""
        if self.prop_unique_guid_method.lower() == "guid":
            return f"{self.source_publisher_pk}_{self.feed_article_guid}"
        elif self.prop_unique_guid_method.lower() == "url":
            self.__calculate_final_value__(
                final_attr_name="final_link",
                feed_attr_name="feed_article_url_str",
                scrape_attr_name="true_article_url_str",
            )
            return f"{self.source_publisher_pk}_{hashlib.sha256(self.final_link.encode('utf-8')).hexdigest()}"
        elif self.prop_unique_guid_method.lower() == "title":
            self.__calculate_final_value__(
                final_attr_name="final_title",
                feed_attr_name="feed_article_title",
                scrape_attr_name="scrape_article_title",
            )
            return f"{self.source_publisher_pk}_{hashlib.sha256(self.final_title.encode('utf-8')).hexdigest()}"
        else:
            raise Exception(
                f'Undefined "unique_article_id"={self.prop_unique_guid_method.lower()}'
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
                self.final_title = self.final_title(potential_inluded_name, "")

        # Summary
        self.__calculate_final_value__(
            final_attr_name="final_summary",
            feed_attr_name="feed_article_summary_text",
            scrape_attr_name="scrape_article_summary_text",
        )

        # News type
        if (
            hasattr(self, "final_title")
            and any(
                [
                    i in self.final_title.lower()
                    for i in ["breaking news", "liveticker", "liveblog", "live blog"]
                ]
            )
        ) or (
            hasattr(self, "final_summary")
            and any(
                [
                    i in self.final_summary.lower()
                    for i in ["breaking news", "liveticker", "liveblog", "live blog"]
                ]
            )
        ):
            self.final_content_type = "ticker"
            self.final_type = "breaking"
        else:
            self.final_content_type = "article"
            self.final_type = "normal"

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
            # body_text = ""
        elif scrape_article_body_cnt != 0 and (
            feed_article_body_cnt == 0 or self.publisher_equal_source is False
        ):
            self.final_full_text = self.scrape_article_body_html
            # body_text = self.scrape_article_body_text
            body_cnt = scrape_article_body_cnt
        elif feed_article_body_cnt != 0 and scrape_article_body_cnt == 0:
            self.final_full_text = self.feed_article_body_html
            # body_text = self.feed_article_body_text
            body_cnt = feed_article_body_cnt
        elif (feed_article_body_cnt * 1.5 < scrape_article_body_cnt) or (
            feed_article_body_cnt * 100 < scrape_article_body_cnt
        ):
            self.final_full_text = self.scrape_article_body_html
            # body_text = self.scrape_article_body_text
            body_cnt = scrape_article_body_cnt
        else:
            self.final_full_text = self.feed_article_body_html
            # body_text = self.feed_article_body_text
            body_cnt = feed_article_body_cnt

        if body_cnt > 80:
            self.final_has_full_text = True
        else:
            self.final_has_full_text = False

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
            lang = langid.classify(f"{self.final_title}\n{self.final_summary}")
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
        self.final_hash = self.final_guid = self.calculate_guid()

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


# if __name__ == "__main__":
#    dummy_test_news_feed()
