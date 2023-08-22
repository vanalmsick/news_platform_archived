from django.db.models import Q, Max, Avg
import os, openai, re, ratelimit
import feedparser, datetime, time, hashlib
from articles.models import Article, FeedPosition
from feeds.models import Feed, Publisher, NEWS_GENRES
import urllib, requests, random
from urllib.parse import urlparse
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

import requests, threading, html
from bs4 import BeautifulSoup


def postpone(function):
    def decorator(*args, **kwargs):
        t = threading.Thread(target = function, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
    return decorator

@postpone
def update_feeds():

    start_time = time.time()
    cache.set('currentlyRefresing', True, 60*60)

    old_articles = Article.objects.filter(min_article_relevance__isnull=True, pub_date__lte=settings.TIME_ZONE_OBJ.localize(datetime.datetime.now() - datetime.timedelta(days=3)))
    if len(old_articles) > 0:
        print(f'Delete {len(old_articles)} old articles')
        old_articles.delete()
    else:
        print(f'No old articles to delete')

    # delete all artcile positions
    all_articles = Article.objects.all()
    all_articles.update(min_feed_position=None)
    all_articles.update(max_importance=None)
    all_articles.update(min_article_relevance=None)

    # delete feed positions of inactive feeds
    feeds = Feed.objects.filter(~Q(active=True))
    for feed in feeds:
        delete_feed_positions(feed=feed)

    feeds = Feed.objects.filter(active=True)
    added_articles = 0
    for feed in feeds:
        added_articles += fetch_feed(feed)

    # calculate next refesh time
    end_time = time.time()
    now = datetime.datetime.now()
    if now.hour >= 6 and now.hour < 19:
        refresh_time = 60 * 15 - (end_time - start_time)
    else:
        refresh_time = 60 * 30 - (end_time - start_time)
    cache.set('upToDate', True, int(refresh_time))

    # Updating cached artciles
    articles = Article.objects.all().exclude(main_genre='sport').exclude(min_article_relevance__isnull=True).order_by('min_article_relevance')[:72]
    cache.set('homepage', articles, 60 * 60 * 48)
    cache.set('lastRefreshed', now, 60 * 60 * 48)

    now = datetime.datetime.now()
    if now.hour >= 18 and now.hour < 6:
        print('No AI summaries are generated between 18:00-6:00 as top artciles might change till user wakes up')
    else:
        median_relevance = articles[int(len(articles) / 2)].min_article_relevance
        articles_add_ai_summary = Article.objects.filter(has_full_text=True, ai_summary__isnull=True, min_article_relevance__lte=median_relevance).exclude(publisher__name__in=['Risk.net', 'The Economist'])
        add_ai_summary(article_obj_lst=articles_add_ai_summary)

    cache.set('currentlyRefresing', False, 60 * 60)

    print(f'Refreshed articles and added {added_articles} articles in {int(end_time - start_time)} seconds')

    connection.close()



def calcualte_relevance(publisher, feed, feed_position, hash, pub_date):
    random.seed(hash)

    importance = feed.importance
    if feed.feed_ordering == 'r':
        if feed_position <= 3:
            importance += 2
        elif feed_position <= 7:
            importance += 1
        importance = min(4, importance)

    duration = settings.TIME_ZONE_OBJ.localize(datetime.datetime.now()) - pub_date
    duration_in_s = duration.total_seconds()
    article_age_h = divmod(duration_in_s if duration_in_s != None else duration_in_s, 3600)[0]
    if article_age_h > 48:
        article_age_discount = 2
        age_factor = 1
    elif article_age_h > 24:
        article_age_discount = 1
        age_factor = 1
    else:
        article_age_discount = 0
        age_factor = 1
    if article_age_h > 24 * 5:
        age_factor = 3
    elif article_age_h > 24 * 14:
        age_factor = 30

    article_relevance = round(feed_position *
                              {3: 3 / 6, 2: 5 / 6, 1: 1, 0: 1, -1: 8 / 6, -2: 10 / 6, -3: 12 / 6}[
                                  publisher.renowned] *
                              {4: 1 / 6, 3: 2 / 6, 2: 4 / 6, 1: 1, 0: 8 / 6}[
                                  max((importance - article_age_discount), 0)] -
                              ((publisher.renowned + random.randrange(0, 9)) / 10000) *
                              age_factor,
                              6)

    return importance, article_relevance



def delete_feed_positions(feed):
    all_feedpositions = feed.feedposition_set.all()
    all_feedpositions.delete()


@ratelimit.sleep_and_retry
@ratelimit.limits(calls=60, period=60)
def check_limit():
    ''' Empty function just to check for calls to API '''
    # limit of 180k tokens per minute = 180k / 3k per request = 60 requets
    # limit of 3600 requests per minute
    # min(3.6k, 60) = 60 requests per minute
    return


def add_ai_summary(article_obj_lst):
    print(f'Requesting AI article summaries for {len(article_obj_lst)} articles.')

    openai.api_key = settings.OPENAI_API_KEY
    TOTAL_API_COST = 0 if cache.get('OPENAI_API_COST_LAUNCH') is None else cache.get('OPENAI_API_COST_LAUNCH')
    COST_TOKEN_INPUT = 0.003
    COST_TOKEN_OUTPUT = 0.004
    NET_USD_TO_GROSS_GBP = 1.2 * 0.785
    token_cost = 0
    articles_summarized = 0

    for article_obj in article_obj_lst:
        try:
            soup = BeautifulSoup(article_obj.full_text, 'html5lib')
            article_text = " ".join(html.unescape(soup.text).split())
            #article_text = re.sub(r'\n+', '\n', article_text).strip()
            if len(article_text) > 3000*5:
                article_text = article_text[:3000*5]
            if len(article_text) / 5 < 500:
                continue
            elif len(article_text) / 5 < 1000:
                bullets = 2
            elif len(article_text) / 5 < 2000:
                bullets = 3
            else:
                bullets = 4
            check_limit()
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {"role": "user", "content": f'Summarize this article in {bullets} bullet points:\n"{article_text}"'}
                ]
            )
            article_summary = completion["choices"][0]["message"]["content"]
            article_summary = article_summary.replace('- ', '<li>').replace('\n', '</li>\n')
            article_summary = '<ul>\n' + article_summary + '</li>\n</ul>'
            token_cost += round((completion["usage"]["prompt_tokens"] * COST_TOKEN_INPUT) + (completion["usage"]["completion_tokens"] * COST_TOKEN_OUTPUT),4)
            setattr(article_obj, 'ai_summary', article_summary)
            article_obj.save()
            articles_summarized += 1
        except Exception as e:
            print(f'Error getting AI article summary for {article_obj}:', e)

    THIS_RUN_API_COST = round(float(token_cost / 1000 * NET_USD_TO_GROSS_GBP), 4)
    TOTAL_API_COST += THIS_RUN_API_COST
    cache.set('OPENAI_API_COST_LAUNCH', TOTAL_API_COST, 3600 * 1000)
    print(f'Summarized {articles_summarized} articles costing {THIS_RUN_API_COST} GBP. Total API cost since container launch {TOTAL_API_COST} GBP.')




def scarpe_img(url):
    img_url = None
    try:
        _ = URLValidator(url)
        resp = requests.get(url)
        soup = BeautifulSoup(resp.content, 'html5lib')
        body = soup.find('body')
        images = body.find_all('img')
        new_images = []
        for i in images:
            i_alt = ''
            i_class = ''
            i_src = ''
            try:
                i_src = str(i['src']).lower()
                i_alt = str(i['alt']).lower()
                i_class = str(i['class']).lower()
            except:
                pass
            if len(i_src) > 3 and any([j in i_src for j in
                                       ['.avif', '.gif', '.jpg', '.jpeg', '.jfif', '.pjpeg', '.pjp', '.png', '.svg',
                                        '.webp']]) and 'logo' not in i_class and 'logo' not in i_alt and 'author' not in i_class and 'author' not in i_alt:
                new_images.append(i)
        if len(new_images) > 0:
            images = new_images
            image = images[0]['src']
            if 'www.' not in image and 'http' not in image:
                url_parts = urlparse(url)
                image = url_parts.scheme + '://' + url_parts.hostname + image
            img_url = image

    except Exception as e:
        print(f'Error sccraping image for acticle from "{url}"')
        print(e)

    return img_url


def fetch_feed(feed):
    added_articles = 0
    article_without_ai_summary = []

    feed_url = feed.url
    if 'http://FEED-CREATOR.local' in feed_url:
        feed_url = feed_url.replace('http://FEED-CREATOR.local', settings.FEED_CREATOR_URL)
    if 'http://FULL-TEXT.local' in feed_url:
        feed_url = feed_url.replace('http://FULL-TEXT.local', settings.FULL_TEXT)

    fetched_feed = feedparser.parse(feed_url)

    if len(fetched_feed.entries) > 0:
        delete_feed_positions(feed)

    for i, scraped_article in enumerate(fetched_feed.entries):
        hash_obj = hashlib.new('sha256')
        article__feed_position = i + 1
        article_kwargs = dict(min_feed_position=article__feed_position, publisher=feed.publisher)
        for kwarg_X, kwarg_Y in {'title': 'title', 'summary': 'summary', 'link': 'link', 'guid': 'id', 'pub_date': 'published_parsed'}.items():
            if hasattr(scraped_article, kwarg_Y) and scraped_article[kwarg_Y] is not None and scraped_article[kwarg_Y] != '':
                if kwarg_X in ['title', 'summary'] and scraped_article[kwarg_Y] is not None:
                    article_kwargs[kwarg_X] = html.unescape(scraped_article[kwarg_Y])
                else:
                    article_kwargs[kwarg_X] = scraped_article[kwarg_Y]

        # add unique id/hash
        if feed.publisher.unique_article_id == 'guid' and 'guid' in article_kwargs:
            article_kwargs['hash'] = f'{feed.publisher.pk}_{article_kwargs["guid"]}'
        elif feed.publisher.unique_article_id == 'title':
            hash_obj.update(str(article_kwargs["title"]).encode())
            hash_str = hash_obj.hexdigest()
            article_kwargs['hash'] = f'{feed.publisher.pk}_{hash_str}'
        else:
            hash_obj.update(str(article_kwargs["link"]).encode())
            hash_str = hash_obj.hexdigest()
            article_kwargs['hash'] = f'{feed.publisher.pk}_{hash_str}'


        # make sure pub_date exists and is in the right format
        if 'pub_date' not in article_kwargs and hasattr(fetched_feed, 'published_parsed'):
            article_kwargs['pub_date'] = full_text_data['published_parsed']
        else:
            article_kwargs['pub_date'] = datetime.datetime.now()
        if 'pub_date' in article_kwargs and type(article_kwargs['pub_date']) == time.struct_time:
            article_kwargs['pub_date'] = datetime.datetime.fromtimestamp(time.mktime(article.published_parsed))
        article_kwargs['pub_date'] = settings.TIME_ZONE_OBJ.localize(article_kwargs['pub_date'])


        # check if artcile already exists
        search_article = Article.objects.filter(hash=article_kwargs['hash'])
        prev_article = None

        # if article exists but changed
        if len(search_article) > 0 and search_article[0].title is not None and 'title' in article_kwargs and search_article[0].title != article_kwargs['title']:
            old_artcile = search_article[0]
            new_article = True
            hash_obj.update(str(old_artcile.title).encode())
            hash_str = hash_obj.hexdigest()
            setattr(old_artcile, 'hash', f'{feed.publisher.pk}_{hash_str}')
            old_artcile.save()
            prev_article = old_artcile.pk

        # if article exists
        elif len(search_article) > 0:
            article_obj = search_article[0]
            new_article = False

        # article does not exist
        else:
            new_article = True

        # article does not exist yet
        if new_article:
            # get full text if settings say yes
            if feed.full_text_fetch == 'Y':
                request_url = f'{settings.FULL_TEXT_URL}extract.php?url={urllib.parse.quote(article_kwargs["link"], safe="")}'
                response = requests.get(request_url)
                if response.status_code == 200:
                    full_text_data = response.json()
                    for kwarg_X, kwarg_Y in {'summary': 'excerpt', 'author': 'author', 'image_url': 'og_image', 'full_text': 'content', 'language': 'language'}.items():
                        if (kwarg_X not in article_kwargs or len(article_kwargs[kwarg_X]) < 6) and kwarg_Y in full_text_data and full_text_data[kwarg_Y] is not None and full_text_data[kwarg_Y] != '':
                            if kwarg_X in ['title', 'summary', 'author', 'language']:
                                article_kwargs[kwarg_X] = html.unescape(full_text_data[kwarg_Y])
                            else:
                                article_kwargs[kwarg_X] = full_text_data[kwarg_Y]

                    # if no image try scraping it differently
                    if 'image_url' not in article_kwargs or article_kwargs['image_url'] is None or len(
                            article_kwargs['image_url']) < 10:
                        image_url = scarpe_img(url=article_kwargs['link'])
                        if image_url is not None:
                            article_kwargs['image_url'] = image_url
                            print(f"Successfully scrape image for article {feed.publisher.name}: {article_kwargs['title']}")
                        else:
                            print(f"Couldn't scrape image for article {feed.publisher.name}: {article_kwargs['title']}")

                else:
                    print(f'Full-Text fetch error response {response.status_code}')

            # clean up data
            if 'full_text' in article_kwargs:
                soup = BeautifulSoup(article_kwargs['full_text'], "html.parser")
                for img in soup.find_all('img'):
                    img['style'] = 'max-width: 100%; max-height: 80vh;'
                    if img['src'] == 'src':
                        img['src'] = img['data-url'].replace('${formatId}', '906')
                for a in soup.find_all('a'):
                    a['target'] = '_blank'
                for link in soup.find_all('link'):
                    if link is not None:
                        link.decompose()
                for meta in soup.find_all('meta'):
                    if meta is not None:
                        meta.decompose()
                for noscript in soup.find_all('noscript'):
                    if noscript is not None:
                        noscript.name = 'div'
                for div_type, id in [('div', 'barrierContent'), ('div', 'nousermsg'),
                                 ('div', 'trial_print_message'), ('div', 'print_blocked_message'),
                                 ('div', 'copy_blocked_message'), ('button', 'toolbar-item-parent-share-2909'),
                                 ('ul', 'toolbar-item-dropdown-share-2909')]:
                    div = soup.find(div_type, id=id)
                    if div is not None:
                        div.decompose()
                article_kwargs['full_text'] = soup.prettify()

                if prev_article is not None:
                    article_kwargs['full_text'] = f'<a class="btn btn-outline-secondary my-2 ms-2" style="float: right;" href="/?article={prev_article}">Go to previous article version</a>\n' + article_kwargs['full_text']


            # add additional properties
            if 'full_text' not in article_kwargs or len(article_kwargs['full_text']) < 200:
                article_kwargs['has_full_text'] = False
            else:
                article_kwargs['has_full_text'] = True


            if ('title' in article_kwargs and ('breaking news' in article_kwargs['title'].lower() or 'live news' in article_kwargs['title'].lower())) or ('full_text' in article_kwargs and article_kwargs['full_text'] is not None and ('developing story' in article_kwargs['full_text'].lower())):
                article_kwargs['type'] = 'breaking'
            else:
                article_kwargs['type'] = 'normal'


            # add article
            article_obj = Article(**article_kwargs)
            article_obj.save()
            added_articles += 1

            if prev_article is not None:
                full_text = '' if old_artcile.full_text is None else old_artcile.full_text
                setattr(old_artcile, 'full_text', f'<a class="btn btn-outline-danger cust-text-danger my-2 ms-2" style="float: right;" href="/?article={article_obj.pk}">Go to updated article version</a>\n' + full_text)
                old_artcile.save()


        # Update article metrics
        article_kwargs['max_importance'], article_kwargs['min_article_relevance'] = calcualte_relevance(publisher=feed.publisher, feed=feed, feed_position=article__feed_position, hash=article_kwargs['hash'], pub_date=article_kwargs['pub_date'])
        for k, v in article_kwargs.items():
            value = getattr(article_obj, k)
            if value is None and v is not None:
                setattr(article_obj, k, v)
            elif 'min' in k and v < value:
                setattr(article_obj, k, v)
            elif 'max' in k and v > value:
                setattr(article_obj, k, v)
        article_obj.save()

        # Add feed position linking
        feed_position = FeedPosition(
            feed=feed,
            position=article__feed_position,
            importance=article_kwargs['max_importance'],
            relevance=article_kwargs['min_article_relevance'],
            genre=article_obj.main_genre if feed.genre is None else feed.genre
        )
        feed_position.save()

        article_obj.feed_position.add(feed_position)

    print(f'Refreshed {feed.name} with {added_articles} new articles out of {len(fetched_feed.entries)}')
    return added_articles


