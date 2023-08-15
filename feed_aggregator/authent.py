from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import redirect
from articles.models import Article
import urllib

class ExampleView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        try:
            requested_article = Article.objects.get(pk=pk)
            article = requested_article.__dict__
            article['publisher__name'] = requested_article.publisher.name
            article.pop('_state')
            SHARE_EMAIL_SUBJECT = f"{article['publisher__name']}: {article['title']}"
            SHARE_EMAIL_BODY = f"""Hi,\n\nHave you seen this article:\n\n{SHARE_EMAIL_SUBJECT}\n{article['link']}\n\nBest wishes,\n\n"""
            SHARE_TEAMS_LINK = f"""{SHARE_EMAIL_SUBJECT}\n{article['link']}"""
            article[f'email__link'] = 'mailto:?subject=' + urllib.parse.quote(SHARE_EMAIL_SUBJECT) + '&body=' + urllib.parse.quote(SHARE_EMAIL_BODY)
            article[f'teams__link'] = 'https://teams.microsoft.com/l/chat/0/0?message=' + urllib.parse.quote(SHARE_TEAMS_LINK)
            article['error'] = False
        except:
            article = {'error': True}

        return Response(article)