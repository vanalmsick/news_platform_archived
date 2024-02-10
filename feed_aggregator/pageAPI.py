"""Get artcile data for all views"""

import datetime
import functools
import operator
import urllib

from django.conf import settings
from django.core.cache import cache
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from articles.models import Article, FeedPosition
from preferences.models import url_parm_encode


def __convert_type(n):
    """convert string to float, int, or bool if possible"""
    try:
        return int(n)
    except ValueError:
        try:
            return float(n)
        except ValueError:
            if n.lower() == "true":
                return True
            elif n.lower() == "false":
                return False
            elif n.lower() == "none" or n.lower() == "null":
                return None
            else:
                return n


def get_article_data(pk, debug=False):
    """Get artcile data for one specific article via primary key (pk)"""
    try:
        requested_article = Article.objects.get(pk=pk)
        article = requested_article.__dict__
        article["full_text"] = mark_safe(article["full_text"])
        article["ai_summary"] = mark_safe(article["ai_summary"])
        article["publisher__name"] = requested_article.publisher.name
        article["publisher__paywall"] = requested_article.publisher.paywall
        if (
            len(article["summary"]) > 30
            and article["summary"][:30] in article["full_text"]
        ):
            article["summary"] = ""
        article.pop("_state")
        SHARE_EMAIL_SUBJECT = f"{article['publisher__name']}: {article['title']}"
        SHARE_EMAIL_BODY = (
            "Hi,\n\nHave you seen this article:\n\n"
            f"{SHARE_EMAIL_SUBJECT}\n"
            f"{article['link']}\n\n"
            "Best wishes,\n\n"
        )
        article["email__link"] = (
            "mailto:?subject="
            + urllib.parse.quote(SHARE_EMAIL_SUBJECT)
            + "&body="
            + urllib.parse.quote(SHARE_EMAIL_BODY)
        )
        article["save__link"] = (
            f"/read-later/remove/{pk}"
            if requested_article.read_later
            else f"/read-later/add/{pk}"
        )
        if debug:
            feed_positions = FeedPosition.objects.filter(article=requested_article)
            article["feed_position"] = []
            if len(feed_positions) > 0:
                for pos in feed_positions:
                    content_type = "art" if pos.feed.feed_type == "rss" else "vid"
                    publisher_article_count = cache.get(
                        f"feed_publisher_{content_type}_cnt_{pos.feed.publisher.pk}"
                    )
                    article["feed_position"].append(
                        dict(
                            feed__name=pos.feed.name,
                            feed__pk=pos.feed.pk,
                            feed__importance=pos.feed.importance,
                            feed__source_categories=pos.feed.source_categories,
                            feed__feed_ordering=pos.feed.feed_ordering,
                            feed__publisher__name=pos.feed.publisher.name,
                            feed__publisher__renowned=pos.feed.publisher.renowned,
                            feed__publisher__language=pos.feed.publisher.language,
                            importance=pos.importance,
                            position=pos.position,
                            relevance=pos.relevance,
                            publisher__article_cnt=publisher_article_count,
                        )
                    )
        article["error"] = False
    except Exception as e:
        print("Error", e)
        article = {"error": True}

    return article


def get_articles(max_length=72, force_recache=False, **kwargs):
    """Gets artcile request by user either from database or from cache"""
    kwargs_hash, kwargs = url_parm_encode(**kwargs)

    articles = cache.get(kwargs_hash)

    cached_views_lst = cache.get("cached_views_lst")
    if cached_views_lst is None:
        cache.set("cached_views_lst", {kwargs_hash: kwargs}, 60 * 60 * 48)
    elif kwargs_hash not in cached_views_lst:
        cache.set(
            "cached_views_lst",
            {**cached_views_lst, **{kwargs_hash: kwargs}},
            60 * 60 * 48,
        )

    if articles is None or force_recache:
        conditions = Q()
        special_filters = kwargs["special"] if "special" in kwargs else None
        exclude_sidebar = True
        has_language_filters = False
        has_read_later = False
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
                    condition = __convert_type(condition)
                    if type(condition) is str:
                        sub_conditions |= Q(**{f"{field}__icontains": condition})
                    else:
                        sub_conditions |= Q(**{f"{field}": condition})
                    exclude_sidebar = False
            if field == "language":
                has_language_filters = True
            if field == "read_later":
                has_read_later = True
            try:
                test_condition = Article.objects.filter(sub_conditions)
            except Exception:
                test_condition = []
            if len(test_condition) > 0:
                conditions &= sub_conditions
        articles = Article.objects.filter(conditions)
        articles = articles.order_by(
            F("min_article_relevance").asc(nulls_last=True),
            "-pub_date__date",
            "-max_importance",
            "-last_updated_date",
        )
        if has_read_later:
            articles = articles.order_by("-last_updated_date")
            has_language_filters = True
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
        if has_language_filters is False and "*" not in settings.ALLOWED_LANGUAGES:
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
    return kwargs_hash, articles


class RestArticleView(APIView):
    """View for url request to article/<int:pk>/"""

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        """get method for Django"""
        article = get_article_data(pk)

        return Response(article)


def ReadLaterView(request, action, pk):
    try:
        requested_article = Article.objects.get(pk=pk)
        if action == "add":
            setattr(requested_article, "read_later", True)
        else:
            setattr(requested_article, "read_later", False)
        requested_article.save()

        cached_views_lst = cache.get("cached_views_lst")
        for kwargs_hash, kwargs in (
            [].items() if cached_views_lst is None else cached_views_lst.items()
        ):
            if "read_later" in kwargs_hash:
                _, _ = get_articles(force_recache=True, **kwargs)

        return redirect("/")

    except Exception:
        return HttpResponse(
            "Error! Maybe the article was not found or other unknonw error.",
            content_type="text/plain",
        )
