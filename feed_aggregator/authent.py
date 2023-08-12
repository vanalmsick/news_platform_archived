from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import redirect
from articles.models import Article

class ExampleView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        try:
            requested_article = Article.objects.get(pk=pk)
            article = requested_article.__dict__
            article['publisher__name'] = requested_article.publisher.name
            article.pop('_state')
            article['error'] = False
        except:
            article = {'error': True}

        return Response(article)