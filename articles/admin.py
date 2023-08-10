from django.contrib import admin
from .models import Article

# Register your models here.
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'publisher', 'pub_date', 'min_article_relevance', 'main_genre', 'categories']