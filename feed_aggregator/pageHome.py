"""Responaible for home view at base url / """
import datetime

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from django.shortcuts import render
from django.template.defaulttags import register

from articles.models import Article
from feed_scraper.feed_scraper import update_feeds
from feed_scraper.video_scraper import update_videos
from preferences.models import get_pages

from .celery import app
from .pageAPI import get_article_data, get_articles
from .pageLogin import LoginView


@register.filter(name="split")
def split(value, key):
    """Django filter 'split'"""
    value.split("key")
    return value.split(key)[:-1]


def getDuration(then, now=datetime.datetime.now(), interval="default"):
    """Get duration between two datetimes"""
    # Returns a duration as specified by variable interval
    # Functions, except totalDuration, returns [quotient, remainder]

    duration = now - then  # For build-in functions
    duration_in_s = duration.total_seconds()

    def years():
        """Seconds in a year=31536000."""
        return divmod(duration_in_s, 31536000)

    def days(seconds=None):
        """Seconds in a day = 86400."""
        return divmod(seconds if seconds is not None else duration_in_s, 86400)

    def hours(seconds=None):
        """Seconds in an hour = 3600."""
        return divmod(seconds if seconds is not None else duration_in_s, 3600)

    def minutes(seconds=None):
        """Seconds in a minute = 60."""
        return divmod(seconds if seconds is not None else duration_in_s, 60)

    def seconds(seconds=None):
        """One secoind in one second."""
        if seconds is not None:
            return divmod(seconds, 1)
        return duration_in_s

    def totalDuration():
        """Duration as extensive string"""
        y = years()
        d = days(y[1])  # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])

        return (
            "Time between dates: {} years, {} days, {} hours, {} minutes and {} seconds"
            .format(int(y[0]), int(d[0]), int(h[0]), int(m[0]), int(s[0]))
        )

    def shortDuration():
        """Duration as short string"""
        y = years()
        d = days(y[1])  # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])

        if y[0] > 0:
            return "{} years, {} days".format(int(y[0]), int(d[0]))
        elif d[0] > 0:
            return "{} days, {} hours".format(int(d[0]), int(h[0]))
        elif h[0] > 0:
            return "{}h {}min".format(int(h[0]), int(m[0]))
        elif m[0] > 0:
            return "{}min {}s".format(int(m[0]), int(s[0]))
        else:
            return "{}s".format(int(s[0]))

    return {
        "years": int(years()[0]),
        "days": int(days()[0]),
        "hours": int(hours()[0]),
        "minutes": int(minutes()[0]),
        "seconds": int(seconds()),
        "default": totalDuration(),
        "short": shortDuration(),
    }[interval]


def get_stats():
    """Get stats about number of artciles/videos per publisher for relevance ranking"""
    added_date__lte_2d = settings.TIME_ZONE_OBJ.localize(
        datetime.datetime.now() - datetime.timedelta(days=2)
    )
    added_date__lte_30d = settings.TIME_ZONE_OBJ.localize(
        datetime.datetime.now() - datetime.timedelta(days=30)
    )

    all_articles = Article.objects.exclude(content_type="video").filter(
        pub_date__gte=added_date__lte_2d
    )
    all_videos = Article.objects.filter(content_type="video").filter(
        pub_date__gte=added_date__lte_30d
    )

    for content_type, query in [("art", all_articles), ("vid", all_videos)]:
        summary = (
            query.exclude(feed_position=None)
            .values("feed_position__feed__publisher__pk")
            .annotate(count=Count("pk"))
        )
        for i in summary:
            cache.set(
                f'feed_publisher_{content_type}_cnt_{i["feed_position__feed__publisher__pk"]}',
                i["count"],
                60 * 60 * 24,
            )


# @postpone
@app.task
def refresh_feeds():
    """Main function to refresh all articles and videos"""
    print("refreshing started")

    currentlyRefreshing = cache.get("currentlyRefreshing")
    if currentlyRefreshing:
        print("Already other task that is refreshing articles")
        return "ALREADY RUNNING"

    try:
        cache.set("currentlyRefreshing", True, 60 * 60 * 48)
        videoRefreshCycleCount = cache.get("videoRefreshCycleCount")

        get_stats()

        # Caching artciles before updaing
        views_to_cache = [
            dict(categories="frontpage"),
            {"special": ["free-only"]},
            {"language": ["de"]},
            {"categories": ["fund"]},
            {"categories": ["tech"]},
            {"publisher__name": ["financial times"]},
            {"publisher__name": ["bloomberg"]},
            {"content_type": ["video"]},
        ]
        for kwargs in views_to_cache:
            _, _ = get_articles(**kwargs)

        update_feeds()
        if videoRefreshCycleCount is None or videoRefreshCycleCount == 0:
            update_videos()
            cache.set("videoRefreshCycleCount", 8, 60 * 60 * 24)
        else:
            print(f"Refeshing videos in {videoRefreshCycleCount - 1} cycles")
            cache.set(
                "videoRefreshCycleCount", videoRefreshCycleCount - 1, 60 * 60 * 24
            )

        cached_views_lst = cache.get("cached_views_lst")
        if cached_views_lst is None:
            cached_views_lst = {i: j for i, j in enumerate(views_to_cache)}
        for kwargs_hash, kwargs in cached_views_lst.items():
            _, _ = get_articles(force_recache=True, **kwargs)

        now = datetime.datetime.now()
        cache.set("lastRefreshed", now, 60 * 60 * 48)

        print("refreshing finished")

    except Exception as e:
        raise Exception(e)

    finally:
        cache.set("currentlyRefreshing", False, 60 * 60 * 48)


# @cache_page(60 * 1)
# @vary_on_cookie
def homeView(request):
    """Return django view of home page"""
    debug = (
        True
        if "debug" in request.GET and request.GET["debug"].lower() == "true"
        else False
    )
    # If fallback articcle view is needed
    if "article" in request.GET:
        article = get_article_data(int(request.GET["article"]), debug=debug)
        if article["error"] is False:
            meta = f"""
            <title>{article['title']} - {article['publisher__name']}</title>
            <meta name="description" content="{article['summary']}">
            <meta property="og:description" content="{article['summary']}">
            <meta property="og:image" content="{article['image_url']}">
            <meta property="og:site_name" content="{article['publisher__name']}">
            <meta property="og:title" content="{article['title']}">
            <meta property="og:type" content="article">
            <meta property="og:url" content="{article['link']}">
            """
        else:
            meta = f"<title>{settings.CUSTOM_PLATFORM_NAME}</title>"

        # if user is not autheticated
        if request.user.is_authenticated is False:
            return LoginView(request, meta)
        return render(
            request,
            "fallbackArticle.html",
            {
                "article": article,
                "meta": meta,
                "debug": debug,
                "platform_name": settings.CUSTOM_PLATFORM_NAME,
            },
        )

    # Get Homepage
    kwargs_hash, articles = (
        get_articles(categories="frontpage")
        if len(request.GET) == 0
        else get_articles(**request.GET)
    )
    _, sidebar = get_articles(special="sidebar", max_length=100)
    lastRefreshed = cache.get("lastRefreshed")
    html_nav_bar = get_pages(recache=False)

    return render(
        request,
        "home.html",
        {
            "articles": articles,
            "sidebar": sidebar,
            "platform_name": settings.CUSTOM_PLATFORM_NAME,
            "lastRefreshed": (
                "Never"
                if lastRefreshed is None
                else getDuration(lastRefreshed, datetime.datetime.now(), "short")
            ),
            "navbar_html": html_nav_bar,
            "selected_page": kwargs_hash,
            "sidebar_title": settings.SIDEBAR_TITLE,
            "meta": (
                f"<title>{settings.CUSTOM_PLATFORM_NAME}</title><meta"
                ' name="description" content="Personal news platform aggregating news'
                " articles from several RSS feeds and videos from different YouTube"
                ' channels.">'
            ),
        },
    )
