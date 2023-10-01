"""Get artcile data for all views"""
import urllib

from django.core.cache import cache
from django.utils.safestring import mark_safe
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from articles.models import Article, FeedPosition


def get_article_data(pk, debug=False):
    """Get artcile data for one specific article via primary key (pk)"""
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
        SHARE_EMAIL_BODY = (
            "Hi,\n\nHave you seen this"
            f" article:\n\n{SHARE_EMAIL_SUBJECT}\n{article['link']}\n\nBest wishes,\n\n"
        )
        SHARE_TEAMS_LINK = f"""{SHARE_EMAIL_SUBJECT}\n{article['link']}"""
        article["email__link"] = (
            "mailto:?subject="
            + urllib.parse.quote(SHARE_EMAIL_SUBJECT)
            + "&body="
            + urllib.parse.quote(SHARE_EMAIL_BODY)
        )
        article["teams__link"] = (
            "https://teams.microsoft.com/l/chat/0/0?users=sven.van.almsick@morganstanley.com&message="
            + urllib.parse.quote(SHARE_TEAMS_LINK)
        )
        if debug:
            feed_positions = FeedPosition.objects.filter(article=requested_article)
            article["feed_position"] = []
            if len(feed_positions) > 0:
                for pos in feed_positions:
                    content_type = "art" if pos.feed.feed_type == "rss" else "vid"
                    publisher_article_count = cache.get(
                        f"publisher_{content_type}_cnt_{pos.feed.publisher.pk}"
                    )
                    article["feed_position"].append(
                        dict(
                            feed__name=pos.feed.name,
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


class ExampleView(APIView):
    """View for url request to article/<int:pk>/"""

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        article = get_article_data(pk)

        return Response(article)
