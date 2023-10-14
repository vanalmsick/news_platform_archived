"""Responaible for home view at base url / """
import datetime
import functools
import operator

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q
from django.shortcuts import render
from django.template.defaulttags import register

from articles.models import Article
from feed_scraper.feed_scraper import postpone, update_feeds
from feed_scraper.video_scraper import update_videos

from .pageAPI import get_article_data
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
            .values("publisher__pk")
            .annotate(count=Count("publisher__name"))
        )
        for i in summary:
            cache.set(
                f'publisher_{content_type}_cnt_{i["publisher__pk"]}',
                i["count"],
                60 * 60 * 24,
            )


@postpone
def refresh_feeds():
    """Main function to refresh all articles and videos"""
    currentlyRefreshing = cache.get("currentlyRefreshing")
    videoRefreshCycleCount = cache.get("videoRefreshCycleCount")

    get_stats()

    # Caching artciles before updaing
    for kwargs in [
        dict(categories="frontpage"),
        {"special": ["free-only"]},
        {"language": ["de"]},
        {"categories": ["fund"]},
        {"categories": ["tech"]},
        {"publisher__name": ["financial times"]},
        {"publisher__name": ["bloomberg"]},
        {"content_type": ["video"]},
    ]:
        _ = get_articles(**kwargs)

    if currentlyRefreshing is not True:
        cache.set("currentlyRefreshing", True, 60 * 60)
        update_feeds()
        if videoRefreshCycleCount is None or videoRefreshCycleCount == 0:
            update_videos()
            cache.set("videoRefreshCycleCount", 8, 60 * 60 * 24)
        else:
            print(f"Refeshing videos in {videoRefreshCycleCount - 1} cycles")
            cache.set(
                "videoRefreshCycleCount", videoRefreshCycleCount - 1, 60 * 60 * 24
            )


def get_articles(max_length=72, force_recache=False, **kwargs):
    """Gets artcile request by user either from database or from cache"""
    kwargs = {k: [v] if type(v) is str else v for k, v in kwargs.items()}
    kwargs_hash = "articles_" + str(
        {k.lower(): [i.lower() for i in sorted(v)] for k, v in kwargs.items()}
    )
    kwargs_hash = "".join([i if i.isalnum() else "_" for i in kwargs_hash])
    articles = cache.get(kwargs_hash)
    currentlyRefreshing = cache.get("currentlyRefreshing")

    if (articles is None or force_recache) and currentlyRefreshing is not True:
        conditions = Q()
        special_filters = kwargs["special"] if "special" in kwargs else None
        exclude_sidebar = True
        has_language_filters = False
        for field, condition_lst in kwargs.items():
            sub_conditions = Q()
            for condition in condition_lst:
                if field.lower() == "special":
                    if condition.lower() == "free-only":
                        sub_conditions &= Q(
                            Q(Q(has_full_text=True) | Q(publisher__paywall="N"))
                            & Q(categories__icontains="frontpage")
                        )
                    elif condition.lower() == "sidebar":
                        sub_conditions &= Q(categories__icontains="SIDEBAR")
                        exclude_sidebar = False
                else:
                    sub_conditions |= Q(**{f"{field}__icontains": condition})
                    exclude_sidebar = False
            if field == "language":
                has_language_filters = True
            try:
                test_condition = Article.objects.filter(sub_conditions)
            except Exception:
                test_condition = []
            if len(test_condition) > 0:
                conditions &= sub_conditions
        articles = (
            Article.objects.filter(conditions)
            .exclude(min_article_relevance__isnull=True)
            .order_by("min_article_relevance")
        )
        if exclude_sidebar:
            articles = articles.exclude(categories__icontains="SIDEBAR")
        if special_filters is not None and "sidebar" in special_filters:
            articles = articles.order_by(
                "-added_date", "-pub_date", "min_article_relevance"
            ).exclude(
                pub_date__lte=settings.TIME_ZONE_OBJ.localize(
                    datetime.datetime.now() - datetime.timedelta(days=5)
                )
            )
        if has_language_filters is False:
            articles = articles.filter(
                functools.reduce(
                    operator.or_,
                    (
                        Q(language__icontains=x)
                        for x in settings.ALLOWED_LANGUAGES.split(",")
                    ),
                )
            )
        if max_length is not None and len(articles) > max_length:
            articles = articles[:max_length]
        cache.set(kwargs_hash, articles, 60 * 60 * 48)
        print(f"Got {kwargs_hash} from database and cached it")
    return articles


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
            if article["error"]:
                meta = "<title>vA News Platform</title>"
            else:
                meta = (
                    f"<title>{article['title']} - {article['publisher__name']}</title>"
                )

        # if user is not autheticated
        if request.user.is_authenticated is False:
            return LoginView(request, meta)
        return render(
            request,
            "fallbackArticle.html",
            {"article": article, "meta": meta, "debug": debug},
        )

    # Get Homepage
    selected_page = "frontpage" if len(request.GET) == 0 else "unknown"
    upToDate = cache.get("upToDate")
    articles = (
        get_articles(categories="frontpage")
        if selected_page == "frontpage"
        else get_articles(**request.GET)
    )
    sidebar = get_articles(special="sidebar", max_length=100)
    lastRefreshed = cache.get("lastRefreshed")
    currentlyRefreshing = cache.get("currentlyRefreshing")

    if "publisher__name" in request.GET:
        if "financial times" in request.GET["publisher__name"]:
            selected_page = "financial times"
        elif "bloomberg" in request.GET["publisher__name"]:
            selected_page = "bloomberg"
        elif "medium" in request.GET["publisher__name"]:
            selected_page = "medium"
    elif "categories" in request.GET:
        if "fund" in request.GET["categories"]:
            selected_page = "funds"
        elif "tech" in request.GET["categories"]:
            selected_page = "tech"
    elif "special" in request.GET:
        if "free-only" in request.GET["special"]:
            selected_page = "free-only"
        elif "sidebar" in request.GET["special"]:
            selected_page = "sidebar"
    elif "language" in request.GET:
        if "de" in request.GET["language"]:
            selected_page = "german"
    elif "content_type" in request.GET:
        if "video" in request.GET["content_type"]:
            selected_page = "video"

    if not upToDate and not currentlyRefreshing:
        now = datetime.datetime.now()
        if now.hour >= 0 and now.hour < 5:
            print(
                "Don't update articles between 0:00-4:59am to avoid forceful shutdown"
                " of container during server updates."
            )
        else:
            print("News are being refreshed now")
            refresh_feeds()

    return render(
        request,
        "home.html",
        {
            "articles": articles,
            "sidebar": sidebar,
            "lastRefreshed": (
                "Never"
                if lastRefreshed is None
                else getDuration(lastRefreshed, datetime.datetime.now(), "short")
            ),
            "page": selected_page,
            "meta": "<title>vA News Platform</title>",
        },
    )
