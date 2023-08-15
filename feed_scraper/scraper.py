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


def getDuration(then, now=datetime.datetime.now(), interval="default"):
    # Returns a duration as specified by variable interval
    # Functions, except totalDuration, returns [quotient, remainder]

    duration = now - then  # For build-in functions
    duration_in_s = duration.total_seconds()

    def years():
        return divmod(duration_in_s, 31536000)  # Seconds in a year=31536000.

    def days(seconds=None):
        return divmod(seconds if seconds != None else duration_in_s, 86400)  # Seconds in a day = 86400

    def hours(seconds=None):
        return divmod(seconds if seconds != None else duration_in_s, 3600)  # Seconds in an hour = 3600

    def minutes(seconds=None):
        return divmod(seconds if seconds != None else duration_in_s, 60)  # Seconds in a minute = 60

    def seconds(seconds=None):
        if seconds != None:
            return divmod(seconds, 1)
        return duration_in_s

    def totalDuration():
        y = years()
        d = days(y[1])  # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])

        return "Time between dates: {} years, {} days, {} hours, {} minutes and {} seconds".format(int(y[0]), int(d[0]),
                                                                                                   int(h[0]), int(m[0]),
                                                                                                   int(s[0]))

    def shortDuration():
        y = years()
        d = days(y[1])  # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])

        if y[0] > 0:
            return '{} years, {} days'.format(int(y[0]), int(d[0]))
        elif d[0] > 0:
            return '{} days, {} hours'.format(int(d[0]), int(h[0]))
        elif h[0] > 0:
            return '{}h {}min'.format(int(h[0]), int(m[0]))
        elif m[0] > 0:
            return '{}min {}s'.format(int(m[0]), int(s[0]))
        else:
            return '{}s'.format(int(s[0]))

    return {
        'years': int(years()[0]),
        'days': int(days()[0]),
        'hours': int(hours()[0]),
        'minutes': int(minutes()[0]),
        'seconds': int(seconds()),
        'default': totalDuration(),
        'short': shortDuration()
    }[interval]



def article_get_full_text(image_website_scraped, **kwargs):
    request_url = f'{settings.FULL_TEXT_URL}extract.php?url={urllib.parse.quote(kwargs["link"], safe="")}'
    response = requests.get(request_url)
    if response.status_code == 200:
        data = response.json()
        if 'summary' not in kwargs or len(kwargs['summary']) < 20:
            kwargs['summary'] = data['excerpt']
        if 'author' not in kwargs or len(kwargs['author']) < 4:
            kwargs['author'] = data['author']
        if 'image_url' not in kwargs or len(kwargs['image_url']) < 4 or image_website_scraped:
            kwargs['image_url'] = data['og_image']
        if 'full_text' not in kwargs or len(kwargs['full_text']) < 20:
            full_text = data['content']
            soup = BeautifulSoup(full_text, "html.parser")
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
            for type, id in [('div', 'barrierContent'), ('div', 'nousermsg'), ('div', 'trial_print_message'), ('div', 'print_blocked_message'), ('div', 'copy_blocked_message'), ('button', 'toolbar-item-parent-share-2909'), ('ul', 'toolbar-item-dropdown-share-2909')]:
                div = soup.find(type, id=id)
                if div is not None:
                    div.decompose()
            kwargs['full_text'] = soup.prettify()
        if 'language' not in kwargs or len(kwargs['language']) < 20:
            kwargs['language'] = data['language']
    else:
        print(f'Full Text Fetch Error response {response.status_code}')
    return kwargs


def postpone(function):
    def decorator(*args, **kwargs):
        t = threading.Thread(target = function, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
    return decorator

@postpone
def update_feeds():

    cache.set('currentlyRefresing', True, 60*60)

    old_articles = Article.objects.filter(min_article_relevance__isnull=True, pub_date__lte=settings.TIME_ZONE_OBJ.localize(datetime.datetime.now() - datetime.timedelta(days=3)))
    if len(old_articles) > 0:
        print(f'Delete {len(old_articles)} old articles')
        old_articles.delete()
    else:
        print(f'No old articles to delete')

    feeds = Feed.objects.filter(active=True)
    added_articles = 0
    for feed in feeds:
        added_articles += fetch_feed(feed)
    print(f'Added {added_articles} articles')

    if added_articles > 10:
        fetched_pictures = 0
        publishers = Publisher.objects.all()
        for publisher in publishers:
            fetched_pictures += fetch_pictures(publisher)
        print(f'Scraped websites for {fetched_pictures} additional images')

    cache.set('currentlyRefresing', False, 60 * 60)

    articles = Article.objects.all().exclude(main_genre='sport').exclude(min_article_relevance__isnull=True).order_by('min_article_relevance')[:64]
    cache.set('homepage', articles, 60 * 60 * 48)
    lastRefreshed = datetime.datetime.now()
    cache.set('lastRefreshed', lastRefreshed, 60 * 60 * 48)
    now = datetime.datetime.now()
    now_h = now.hour
    if now_h >= 6 and now_h < 19:
        refresh_time = 60 * 15
    else:
        refresh_time = 60 * 30
    cache.set('upToDate', True, refresh_time)

    connection.close()




def delete_feed_positions(feed):
    all_articles = Article.objects.filter(feed_position__feed=feed)
    all_articles.update(min_feed_position=None)
    all_articles.update(max_importance=None)
    all_articles.update(min_article_relevance=None)
    all_feedpositions = feed.feedposition_set.all()
    all_feedpositions.delete()


def fetch_feed(feed):
    hash_obj = hashlib.new('sha256')

    feed_url = feed.url
    if 'http://FEED-CREATOR.local' in feed_url:
        feed_url = feed_url.replace('http://FEED-CREATOR.local', settings.FEED_CREATOR_URL)
    if 'http://FULL-TEXT.local' in feed_url:
        feed_url = feed_url.replace('http://FULL-TEXT.local', settings.FULL_TEXT)

    fetched_feed = feedparser.parse(feed_url)
    added_articles = 0

    news_categories = {
        i: j.upper().split(' / ') for i, j in NEWS_GENRES
    }

    if len(fetched_feed.entries) > 0:
        delete_feed_positions(feed)

    for i, article in enumerate(fetched_feed.entries):
        article_kwargs = {}

        feed_position = i + 1
        article_kwargs['min_feed_position'] = feed_position
        importance = feed.importance
        if feed.feed_ordering == 'r':
            if feed_position <= 3:
                importance += 2
            elif feed_position <= 7:
                importance += 1
            importance = min(4, importance)
        article_kwargs['max_importance'] = importance
        article_kwargs['publisher'] = feed.publisher

        if hasattr(article, 'title'):
            article_kwargs['title'] = article.title
            if 'live news' in str(article_kwargs['title']).lower() or 'breaking' in str(article_kwargs['title']).lower():
                article_kwargs['max_importance'] = importance = 4
        if hasattr(article, 'summary'):
            article_kwargs['summary'] = html.unescape(article.summary)
        if hasattr(article, 'link'):
            article_kwargs['link'] = article.link
        if hasattr(article, 'id') and 'http' not in article.id and 'www' not in article.id:
            article_kwargs['guid'] = article.id
        else:
            hash_obj.update(str(article.link).encode())
            hash_str = hash_obj.hexdigest()
            article_kwargs['guid'] = f'{hash_str}'
        article_kwargs['hash'] = f'{feed.publisher.id}_' + article_kwargs['guid']
        if hasattr(article, 'published_parsed'):
            article_kwargs['pub_date'] = datetime.datetime.fromtimestamp(time.mktime(article.published_parsed))
        elif hasattr(fetched_feed, 'feed') and hasattr(fetched_feed.feed, 'updated_parsed'):
            article_kwargs['pub_date'] = datetime.datetime.fromtimestamp(time.mktime(fetched_feed.feed.updated_parsed))
        else:
            article_kwargs['pub_date'] = datetime.datetime.now()
        if hasattr(article, 'tags'):
            article_kwargs['categories'] = ', '.join([i['term'] for i in article.tags])
        if hasattr(article, 'author'):
            article_kwargs['author'] = article.author
        if feed.genre is None and 'categories' in article_kwargs:
            matching_tags = [k for k, v in news_categories.items() for i in article_kwargs['categories'].upper().split(', ') if any([z in i for z in v])]
            if len(matching_tags) > 0:
                article_kwargs['main_genre'] = matching_tags[0]
        elif feed.genre is not None:
            article_kwargs['main_genre'] = feed.genre

        image_website_scraped = False
        if hasattr(article, 'image'):
            article_kwargs['image_url'] = 'included'
        else:
            if feed.full_text_fetch == 'Y':
                resp = requests.get(article.link)
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
                    if len(i_src) > 3 and any([j in i_src for j in ['.avif', '.gif', '.jpg', '.jpeg', '.jfif', '.pjpeg', '.pjp', '.png', '.svg', '.webp']]) and 'logo' not in i_class  and 'logo' not in i_alt and 'author' not in i_class  and 'author' not in i_alt:
                        new_images.append(i)
                if len(new_images) > 0:
                    images = new_images
                    image = images[0]['src']
                    if 'www.' not in image and 'http' not in image:
                        url_parts = urlparse(article.link)
                        image = url_parts.scheme + '://' + url_parts.hostname + image
                    article_kwargs['image_url'] = image
                    image_website_scraped = True

        random.seed(article_kwargs['guid'])

        article_age = getDuration(article_kwargs['pub_date'], interval='hours')
        if article_age > 48:
            article_age_discount = 2
        elif article_age > 24:
            article_age_discount = 1
        else:
            article_age_discount = 0

        article_relevance = round(feed_position *
                             {3: 3 / 6, 2: 5 / 6, 1: 1, 0: 1, -1: 8 / 6, -2: 10 / 6, -3: 12 / 6}[article_kwargs['publisher'].renowned] *
                             {4: 1 / 6, 3: 2 / 6, 2: 4 / 6, 1: 1, 0: 8 / 6}[max((importance - article_age_discount), 0)] -
                             ((article_kwargs['publisher'].renowned + random.randrange(0,9)) / 10000),
                             6)

        article_kwargs['min_article_relevance'] = article_relevance

        check_articles = Article.objects.filter(hash=article_kwargs['hash'])
        article_kwargs['pub_date'] = settings.TIME_ZONE_OBJ.localize(article_kwargs['pub_date'])

        if len(check_articles) == 0:

            if settings.FULL_TEXT_URL is not None:
                article_kwargs = article_get_full_text(**article_kwargs, image_website_scraped=image_website_scraped)


            added_article = Article(**article_kwargs)
            added_article.save()
            added_articles += 1

        else:
            added_article = check_articles[0]

            for k, v in article_kwargs.items():
                value = getattr(added_article, k)
                if value is None and v is not None:
                    check_articles.update(**{f'{k}': v})
                elif 'min' in k and v < value:
                    check_articles.update(**{f'{k}': v})
                elif 'max' in k and v > value:
                    check_articles.update(**{f'{k}': v})



        added_feed_position = FeedPosition(
            feed = feed,
            position = feed_position,
            importance = importance,
            relevance = article_relevance,
            genre = added_article.main_genre if feed.genre is None else feed.genre
        )
        added_feed_position.save()

        added_article.feed_position.add(added_feed_position)

    print(f'{feed.name} contains {len(fetched_feed.entries)} articles of which {added_articles} are new')
    return added_articles


def fetch_pictures(publisher):
    fetched_pictures = 0
    validate = URLValidator()

    for link in publisher.img_scrape_urls.replace('%0d', '\r').replace('\r', '\n').replace('%0a', '\n').split('\n'):
        try:
            validate(link)
            resp = requests.get(link)
            soup = BeautifulSoup(resp.content, 'html5lib')
            body = soup.find('body')
            images = body.find_all('img')
            for image in images:
                article_found = False
                item = image
                i = 0
                while article_found is False and i < 5 and item is not None:
                    item = item.parent
                    i += 1
                    matched_article = None
                    try:
                        href_value = item['href']
                        article_found = True
                        matched_article = publisher.article_set.filter(link__contains=href_value)
                    except:
                        pass
                    if matched_article is not None:
                        for article in matched_article:
                            if article.image_url is None:
                                url_img = None
                                try:
                                    url_img = image['src']
                                except:
                                    pass
                                if url_img is None:
                                    try:
                                        url_img = image['data-src']
                                    except:
                                        pass
                                try:
                                    if 'logo' in str(image['alt']).lower() or 'author' in str(image['alt']).lower() or 'logo' in str(image['class']).lower() or 'author' in str(image['class']).lower():
                                        url_img = None
                                except:
                                    pass
                                if url_img is not None and any([i in str(url_img).lower() for i in ['.avif', '.gif', '.jpg', '.jpeg', '.jfif', '.pjpeg', '.pjp', '.png', '.svg', '.webp']]):
                                    url_parts = urlparse(link)
                                    if 'www.' not in url_img and 'http' not in url_img:
                                        url_img = url_parts.scheme + '://' + url_parts.hostname + url_img
                                    article.image_url = url_img
                                    article.save()
                                    fetched_pictures += 1
        except ValidationError as e:
            print(f'Invalid image scraping url: "{link}"')
    return fetched_pictures


