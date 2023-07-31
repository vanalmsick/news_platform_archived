import feedparser, datetime, time, hashlib
from articles.models import Article, FeedPosition
from feeds.models import Feed, Publisher, NEWS_GENRES
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

def update_feeds():
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
        print(f'Sccraped websites for {fetched_pictures} additional images')




def delete_feed_positions(feed):
    all_articles = Article.objects.filter(feed_position__feed=feed)
    all_articles.update(min_feed_position=None)
    all_articles.update(max_importance=None)
    all_feedpositions = feed.feedposition_set.all()
    all_feedpositions.delete()
    print(f'Updating current artcile sorting for feed {feed.name}')


def fetch_feed(feed):
    hash_obj = hashlib.new('sha256')
    fetched_feed = feedparser.parse(feed.url)
    added_articles = 0

    news_categories = {
        i: j.upper().split(' / ') for i, j in NEWS_GENRES
    }

    if len(fetched_feed) > 0:
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
        if hasattr(article, 'summary'):
            article_kwargs['summary'] = article.summary
        if hasattr(article, 'link'):
            article_kwargs['link'] = article.link
        if hasattr(article, 'id') and 'http' not in article.id and 'www' not in article.id:
            article_kwargs['guid'] = article.id
        else:
            hash_obj.update(str(article.link).encode())
            hash_str = hash_obj.hexdigest()
            article_kwargs['guid'] = f'{hash_str}'
        article_kwargs['hash'] = f'{feed.id}_' + article_kwargs['guid']
        if hasattr(article, 'published_parsed'):
            article_kwargs['pub_date'] = datetime.datetime.fromtimestamp(time.mktime(article.published_parsed))
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

        if hasattr(article, 'image'):
            article_kwargs['image_html'] = 'included'
        else:
            if feed.full_text_fetch == 'Y':
                resp = requests.get(article.link)
                soup = BeautifulSoup(resp.content, 'html5lib')
                body = soup.find('body')
                images = body.find_all('img')
                if len(images) > 0:
                    url_parts = urlparse(article.link)
                    image = images[0]['src']
                    if len(image) > 3:
                        if 'www.' not in image and 'http' not in image:
                            image = url_parts.scheme + '://' + url_parts.hostname + image
                        article_kwargs['image_html'] = image

        check_articles = Article.objects.filter(hash=article_kwargs['hash'])

        if len(check_articles) == 0:

            added_article = Article(**article_kwargs)
            added_article.save()
            added_articles += 1

        else:
            added_article = check_articles[0]

            for k, v in article_kwargs.items():
                value = getattr(added_article, k)
                if value is None and v is not None:
                    check_articles.update(**{f'{k}': v})


        added_feed_position = FeedPosition(
            feed = feed,
            position = feed_position,
            importance = importance,
            genre = added_article.main_genre if feed.genre is None else feed.genre
        )
        added_feed_position.save()

        added_article.feed_position.add(added_feed_position)
    return added_articles


def fetch_pictures(publisher):
    fetched_pictures = 0
    for link in publisher.img_scrape_urls.split('\n'):
        resp = requests.get(link)
        soup = BeautifulSoup(resp.content, 'html5lib')
        body = soup.find('body')
        images = body.find_all('img')
        for image in images:
            article_found = False
            item = image
            i = 0
            while article_found is False and i < 6 and item is not None:
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
                        if article.image_html is None:
                            if 'src' not in image:
                                print('d')
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
                            if url_img is not None:
                                url_parts = urlparse(link)
                                if 'www.' not in url_img and 'http' not in url_img:
                                    url_img = url_parts.scheme + '://' + url_parts.hostname + url_img
                                article.image_html = url_img
                                article.save()
                                fetched_pictures += 1
    return fetched_pictures

