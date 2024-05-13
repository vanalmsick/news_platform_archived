# -*- coding: utf-8 -*-
import os

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render

from articles.models import Article


def articleView(request, article=None):
    """Return django view of home page"""
    debug = (
        True
        if "debug" in request.GET and request.GET["debug"].lower() == "true"
        else False
    )

    # if user is not autheticated
    if request.user.is_authenticated is False:
        return HttpResponseRedirect(f"/login/?article={article}")

    article = Article.objects.get(pk=article)

    meta = f"""
        <title>{article.title} - {article.publisher.name}</title>
        <meta name="description" property="og:description" content="{article.extract}">
        <meta name="image" property="og:image" content="{article.image_url}">
        <meta name="site_name" property="og:site_name" content="{article.publisher.name}">
        <meta name="author" property="og:author" content="{article.publisher.name}">
        <meta name="title" property="og:title" content="{article.title} - {article.publisher.name}">
        <meta name="type" property="og:type" content="article">
        <meta name="url" property="og:url" content="{article.link}">
        """

    return render(
        request,
        "article.html",
        {
            "article": article,
            "meta": meta,
            "sentry_sdk": ""
            if os.environ.get("SENTRY_URL", None) is None
            else (
                '<script src="https://browser.sentry-cdn.com/8.0.0/bundle.tracing.replay.min.js" '
                'integrity="sha384-DIp1noZ8K3g+Eyo/7tMTZQNCQrsBen2/q9RIV2OhfLLfZ8yDxAtG5zvXK+PFbQCI" '
                'crossorigin="anonymous"></script>'
            ),
            "debug": debug,
            "platform_name": settings.CUSTOM_PLATFORM_NAME,
        },
    )
