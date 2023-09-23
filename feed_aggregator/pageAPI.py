import urllib

from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from articles.models import Article


def get_article_data(pk):
    try:
        requested_article = Article.objects.get(pk=pk)
        article = requested_article.__dict__
        article["full_text"] = mark_safe(article["full_text"])
        article["ai_summary"] = mark_safe(article["ai_summary"])
        article["publisher__name"] = requested_article.publisher.name
        article["publisher__paywall"] = requested_article.publisher.paywall
        if "<img " in article["full_text"][: min(250, len(article["full_text"]))]:
            article["image_url"] = ""
        if (
            len(article["summary"]) > 30
            and article["summary"][:30] in article["full_text"]
        ):
            article["summary"] = ""
        article.pop("_state")
        SHARE_EMAIL_SUBJECT = f"{article['publisher__name']}: {article['title']}"
        SHARE_EMAIL_BODY = f"""Hi,\n\nHave you seen this article:\n\n{SHARE_EMAIL_SUBJECT}\n{article['link']}\n\nBest wishes,\n\n"""
        SHARE_TEAMS_LINK = f"""{SHARE_EMAIL_SUBJECT}\n{article['link']}"""
        article[f"email__link"] = (
            "mailto:?subject="
            + urllib.parse.quote(SHARE_EMAIL_SUBJECT)
            + "&body="
            + urllib.parse.quote(SHARE_EMAIL_BODY)
        )
        article[f"teams__link"] = (
            "https://teams.microsoft.com/l/chat/0/0?users=sven.van.almsick@morganstanley.com&message="
            + urllib.parse.quote(SHARE_TEAMS_LINK)
        )
        article["error"] = False
    except:
        article = {"error": True}

    return article


class ExampleView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        article = get_article_data(pk)

        return Response(article)
