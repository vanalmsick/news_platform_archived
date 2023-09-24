"""Definition of Article View in Django Admin Space"""

from django.contrib import admin

from .models import Article


# Register your models here.
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Main Admin Article View"""

    list_display = [
        "title",
        "publisher",
        "content_type",
        "has_full_text",
        "added_date",
        "min_article_relevance",
        "categories",
        "language",
    ]
    readonly_fields = (
        "added_date",
        "last_updated_date",
    )
    ordering = ("-added_date",)
