"""feed_aggregator URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from .pageAPI import ReadLaterView, RestArticleView
from .pageHome import homeView
from .pageLogin import LoginURLView, LoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", LoginView, name="login"),
    path("login-url/<str:password>/", LoginURLView, name="login-url"),
    path("article/<int:pk>/", RestArticleView.as_view(), name="article"),
    path("read-later/<str:action>/<int:pk>/", ReadLaterView, name="read-later"),
    path("view/<int:article>/", homeView, name="view_article"),
    path("", homeView, name="home"),
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("webpush/", include("webpush.urls")),
    path("", include("pwa.urls")),
    # path('restapi/v1/accounts/', transactions.api_views.AccountList.as_view()),
    # path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico')))
]
