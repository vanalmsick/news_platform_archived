# -*- coding: utf-8 -*-
"""Get artcile data for all views"""

import datetime
import functools
import operator

from django.conf import settings
from django.core.cache import cache
from django.db.models import F, Q
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from articles.models import Article
from feeds.models import Publisher
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


def get_articles(max_length=72, force_recache=False, **kwargs):
    """Gets artcile request by user either from database or from cache"""
    kwargs_hash, kwargs = url_parm_encode(**kwargs)
    page_num = max(int(kwargs.pop("page", ["1"])[0]), 1) - 1

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
        articles = Article.objects.prefetch_related("publisher").filter(conditions)
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
        if max_length is not None:
            lower_bound = page_num * max_length
            upper_bound = min((page_num + 1) * max_length, len(articles))
            articles = articles[lower_bound:upper_bound]
        cache.set(kwargs_hash, articles, 60 * 60 * 48 if page_num == 0 else 10 * 60)
        print(f"Got {kwargs_hash} from database and cached it")
    return kwargs_hash, articles, page_num + 1


class RestArticleAPIView(APIView):
    """RestAPI view to get article data via /api/article/<int:pk>/"""

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        """get method for Django"""
        try:
            return Response(model_to_dict(Article.objects.get(pk=pk)))
        except Exception as e:
            return Response(
                data=dict(error=e.__str__()), status=status.HTTP_400_BAD_REQUEST
            )


class RestPublisherAPIView(APIView):
    """RestAPI view to get publisher data via /api/publisher/<int:pk>/"""

    authentication_classes = []  # type: ignore
    permission_classes = []  # type: ignore

    def get(self, request, pk, format=None):
        """get method for Django"""
        try:
            return Response(model_to_dict(Publisher.objects.get(pk=pk)))
        except Exception as e:
            return Response(
                data=dict(error=e.__str__()), status=status.HTTP_400_BAD_REQUEST
            )


class RestLastRefeshAPIView(APIView):
    """RestAPI view to check when articles were last refeshed"""

    authentication_classes = []  # type: ignore
    permission_classes = []  # type: ignore

    def get(self, request, format=None):
        """get method for Django"""
        return Response(
            dict(
                lastRefreshed=cache.get("lastRefreshed"),
                currentlyRefreshing=cache.get("currentlyRefreshing"),
                videoRefreshCycleCount=cache.get("videoRefreshCycleCount"),
            )
        )


def ReadLaterView(request, action, pk):
    try:
        requested_article = Article.objects.get(pk=pk)
        setattr(requested_article, "read_later", action == "add")
        requested_article.save()

        cached_views_lst = cache.get("cached_views_lst")
        for kwargs_hash, kwargs in (
            [].items() if cached_views_lst is None else cached_views_lst.items()
        ):
            if "read_later" in kwargs_hash:
                _, _, _ = get_articles(force_recache=True, **kwargs)

        return redirect("/")

    except Exception:
        return HttpResponse(
            "Error! Maybe the article was not found or other unknonw error.",
            content_type="text/plain",
        )


def ArchiveView(request, action, pk):
    try:
        requested_article = Article.objects.get(pk=pk)
        setattr(requested_article, "archive", action == "add")
        if requested_article.read_later and action == "add":
            setattr(requested_article, "read_later", False)
        requested_article.save()

        cached_views_lst = cache.get("cached_views_lst")
        for kwargs_hash, kwargs in (
            [].items() if cached_views_lst is None else cached_views_lst.items()
        ):
            if "archive" in kwargs_hash or "read_later" in kwargs_hash:
                _, _, _ = get_articles(force_recache=True, **kwargs)

        return redirect("/")

    except Exception:
        return HttpResponse(
            "Error! Maybe the article was not found or other unknonw error.",
            content_type="text/plain",
        )
