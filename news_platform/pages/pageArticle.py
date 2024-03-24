from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect
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
        return HttpResponseRedirect(f'/login/?article={article}')

    article = Article.objects.get(pk=article)

    meta = f"""
    <title>{article.title} - {article.publisher.name}</title>
    <meta name="description" content="{article.extract}">
    <meta property="og:description" content="{article.extract}">
    <meta property="og:image" content="{article.image_url}">
    <meta property="og:site_name" content="{article.publisher.name}">
    <meta property="og:title" content="{article.title}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{article.link}">
    """

    return render(
        request,
        "article.html",
        {
            "article": article,
            "meta": meta,
            "debug": debug,
            "platform_name": settings.CUSTOM_PLATFORM_NAME,
        },
    )

