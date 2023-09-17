import scrapetube, time, datetime

from django.conf import settings
from django.core.cache import cache
from articles.models import Article, FeedPosition
from feeds.models import Feed, Publisher

from .feed_scraper import postpone, calcualte_relevance


def __extract_number_from_datestr(full_str, identifier):
    first_part = full_str.split(' ' + identifier)[0]
    reversed_int_str = ''
    for i in reversed(first_part):
        if i.isnumeric():
            reversed_int_str += i
        else:
            break
    return int(''.join(reversed(reversed_int_str)))

@postpone
def update_videos():

    start_time = time.time()

    feeds = Feed.objects.all().exclude(feed_type='rss')

    all_videos = Article.objects.filter(feed_position__feed__in=feeds)
    all_videos.update(min_feed_position=None)
    all_videos.update(max_importance=None)
    all_videos.update(min_article_relevance=None)

    added_videos = 0
    for feed in feeds:
        added_videos += fetch_feed(feed)

    # Updating cached artciles
    cached_views = [i[3:] for i in list(cache._cache.keys()) if 'article' in i and 'video' in i]
    for cached_view in cached_views:
        cache.set(cached_view, None, 10)
        print(f'Delete cached {cached_view}')

    end_time = time.time()
    print(f'Refreshed videos and added {added_videos} videos in {int(end_time - start_time)} seconds')


def fetch_feed(feed):
    added_vids = 0

    if feed.feed_type == 'y-channel':
        videos = scrapetube.get_channel(channel_url=feed.url)
    elif feed.feed_type == 'y-playlist':
        videos = scrapetube.get_playlist(feed.url)
    else:
        videos = []

    for i, video in enumerate(videos):
        no_new_video = 0
        if i > 500:
            print(f'{feed} has more than 500 videos thus stop fetching more.')
            break
        if no_new_video > 50:
            print(f'{feed} no new video found for the last {no_new_video} videos at video {i+1} thus stop checking more.')
        article_kwargs = {}
        article__feed_position = i + 1
        article_kwargs['min_feed_position'] =  article__feed_position
        article_kwargs['publisher'] = feed.publisher
        article_kwargs['content_type'] = 'video'
        article_kwargs['categories'] = ';'.join([str(i).upper() for i in ['VIDEO'] + ([] if feed.source_categories is None else feed.source_categories.split(';')) + ['']])
        article_kwargs['title'] = video['title']['runs'][0]['text'] if 'title' in video else None
        article_kwargs['summary'] = video['descriptionSnippet']['runs'][0]['text'] if 'descriptionSnippet' in video else ''
        if 'lengthText' in video:
            article_kwargs['summary'] = video['lengthText']['simpleText'] + (' h' if len(video['lengthText']['simpleText']) > 5 else ' min') + '  |  ' + video['viewCountText']['simpleText'] + '<br>\n' + article_kwargs['summary']
        article_kwargs['image_url'] = video['thumbnail']['thumbnails'][-1]['url'] if 'thumbnail' in video else None
        article_kwargs['guid'] = video['videoId']
        publishedTimeText = video['publishedTimeText']['simpleText']
        article_kwargs['pub_date'] = datetime.datetime.now()
        if 'min' in publishedTimeText:
            article_kwargs['pub_date'] -= datetime.timedelta(minutes=__extract_number_from_datestr(publishedTimeText, 'min'))
        elif 'hour' in publishedTimeText:
            article_kwargs['pub_date'] -= datetime.timedelta(hours=__extract_number_from_datestr(publishedTimeText, 'hour'))
        elif 'day' in publishedTimeText:
            article_kwargs['pub_date'] -= datetime.timedelta(days=__extract_number_from_datestr(publishedTimeText, 'day'))
        elif 'week' in publishedTimeText:
            article_kwargs['pub_date'] -= datetime.timedelta(days=__extract_number_from_datestr(publishedTimeText, 'week') * 7)
        elif 'month' in publishedTimeText:
            article_kwargs['pub_date'] -= datetime.timedelta(days=__extract_number_from_datestr(publishedTimeText, 'month') * 30)
        elif 'year' in publishedTimeText:
            article_kwargs['pub_date'] -= datetime.timedelta(days=__extract_number_from_datestr(publishedTimeText, 'year') * 365)
        else:
            print(f'Unknown date string "{publishedTimeText}"')
        article_kwargs['pub_date'] = settings.TIME_ZONE_OBJ.localize(article_kwargs['pub_date'])
        article_kwargs['hash'] = f"youtube_{video['videoId']}"
        article_kwargs['language'] = feed.publisher.language
        article_kwargs['link'] = f"https://www.youtube.com/watch?v={video['videoId']}"
        article_kwargs['full_text'] = f"""
        <iframe style="width: 100%; height: auto; min-height: 30vw; max-height:400px; aspect-ratio: 16 / 9;" 
        src="https://www.youtube-nocookie.com/embed/{video['videoId']}?rel=0&autoplay=1"
        frameborder="0" allow="autoplay; encrypted-media" tabindex="0" allowfullscreen></iframe>
        """
        article_kwargs['has_full_text'] = True

        search_article = Article.objects.filter(hash=article_kwargs['hash'])

        if len(search_article) == 0:
            article_obj = Article(**article_kwargs)
            article_obj.save()
            added_vids += 1
            no_new_video = 0

        else:
            article_obj = search_article[0]
            no_new_video += 1


        article_kwargs['max_importance'], article_kwargs['min_article_relevance'] = calcualte_relevance(publisher=feed.publisher, feed=feed, feed_position=article__feed_position, hash=article_kwargs['hash'], pub_date=article_kwargs['pub_date'])
        for k, v in article_kwargs.items():
            value = getattr(article_obj, k)
            if value is None and v is not None:
                setattr(article_obj, k, v)
            elif 'min' in k and v < value:
                setattr(article_obj, k, v)
            elif 'max' in k and v > value:
                setattr(article_obj, k, v)
            elif k == 'categories' and article_kwargs['categories'] is not None:
                for category in article_kwargs['categories'].split(';'):
                    if category.upper() not in v:
                        v += category.upper() + ';'
                setattr(article_obj, k, v)
        article_obj.save()


        # Add feed position linking
        feed_position = FeedPosition(
            feed=feed,
            position=article__feed_position,
            importance=article_kwargs['max_importance'],
            relevance=article_kwargs['min_article_relevance']
        )
        feed_position.save()

        article_obj.feed_position.add(feed_position)

    print(f'Refreshed {feed} with {added_vids} new videos out of {article__feed_position}')
    return added_vids
