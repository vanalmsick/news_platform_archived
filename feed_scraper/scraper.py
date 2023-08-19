from django.db.models import Q

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
    articles = Article.objects.all().exclude(main_genre='sport').exclude(min_article_relevance__isnull=True).order_by('min_article_relevance')[:64]
    cache.set('homepage', articles, 60 * 60 * 48)
    cache.set('lastRefreshed', now, 60 * 60 * 48)
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
    elif article_age_h > 24:
        article_age_discount = 1
    else:
        article_age_discount = 0

    article_relevance = round(feed_position *
                              {3: 3 / 6, 2: 5 / 6, 1: 1, 0: 1, -1: 8 / 6, -2: 10 / 6, -3: 12 / 6}[
                                  publisher.renowned] *
                              {4: 1 / 6, 3: 2 / 6, 2: 4 / 6, 1: 1, 0: 8 / 6}[
                                  max((importance - article_age_discount), 0)] -
                              ((publisher.renowned + random.randrange(0, 9)) / 10000),
                              6)

    return importance, article_relevance



def delete_feed_positions(feed):
    all_articles = Article.objects.filter(feed_position__feed=feed)
    all_articles.update(min_feed_position=None)
    all_articles.update(max_importance=None)
    all_articles.update(min_article_relevance=None)
    all_feedpositions = feed.feedposition_set.all()
    all_feedpositions.delete()


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
    hash_obj = hashlib.new('sha256')
    added_articles = 0

    feed_url = feed.url
    if 'http://FEED-CREATOR.local' in feed_url:
        feed_url = feed_url.replace('http://FEED-CREATOR.local', settings.FEED_CREATOR_URL)
    if 'http://FULL-TEXT.local' in feed_url:
        feed_url = feed_url.replace('http://FULL-TEXT.local', settings.FULL_TEXT)

    fetched_feed = feedparser.parse(feed_url)

    if len(fetched_feed.entries) > 0:
        delete_feed_positions(feed)

    for i, scraped_article in enumerate(fetched_feed.entries):
        article__feed_position = i + 1
        article_kwargs = dict(min_feed_position=article__feed_position, publisher=feed.publisher)
        for kwarg_X, kwarg_Y in {'title': 'title', 'summary': 'summary', 'link': 'link', 'guid': 'id', 'pub_date': 'published_parsed'}.items():
            if hasattr(scraped_article, kwarg_Y):
                article_kwargs[kwarg_X] = scraped_article[kwarg_Y]

        # add unique id/hash
        if feed.publisher.unique_article_id == 'guid' and 'guid' in article_kwargs:
            article_kwargs['hash'] = f'{feed.pk}_{article_kwargs["guid"]}'
        elif feed.publisher.unique_article_id == 'title':
            hash_obj.update(str(article_kwargs["title"]).encode())
            hash_str = hash_obj.hexdigest()
            article_kwargs['hash'] = f'{feed.pk}_{hash_str}'
        else:
            hash_obj.update(str(article_kwargs["link"]).encode())
            hash_str = hash_obj.hexdigest()
            article_kwargs['hash'] = f'{feed.pk}_{hash_str}'


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

        # if artcle exists
        if len(search_article) > 0:
            article_obj = search_article[0]

        # article does not exist yet
        else:
            # get full text if settings say yes
            if feed.full_text_fetch == 'Y':
                request_url = f'{settings.FULL_TEXT_URL}extract.php?url={urllib.parse.quote(article_kwargs["link"], safe="")}'
                response = requests.get(request_url)
                if response.status_code == 200:
                    full_text_data = response.json()
                    for kwarg_X, kwarg_Y in {'summary': 'excerpt', 'author': 'author', 'image_url': 'og_image', 'full_text': 'content', 'language': 'language'}.items():
                        if (kwarg_X not in article_kwargs or len(article_kwargs[kwarg_X]) < 6) and kwarg_Y in full_text_data:
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


            # add additional properties
            if 'full_text' not in article_kwargs or len(article_kwargs['full_text']) < 200:
                article_kwargs['has_full_text'] = False
            else:
                article_kwargs['has_full_text'] = True


            if 'breaking news' in article_kwargs['title'].lower() or 'live:' in article_kwargs['title'].lower():
                article_kwargs['type'] = 'breaking'
            else:
                article_kwargs['type'] = 'normal'


            # add article
            article_obj = Article(**article_kwargs)
            article_obj.save()
            added_articles += 1


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


