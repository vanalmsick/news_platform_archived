from django.contrib import admin

from .models import Article


# Register your models here.
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "publisher",
        "pub_date",
        "added_date",
        "min_article_relevance",
        "categories",
    ]
    readonly_fields = (
        "added_date",
        "last_updated_date",
    )
