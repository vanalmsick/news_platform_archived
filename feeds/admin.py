from django.contrib import admin
from .models import Feed, Publisher

# Register your models here.
@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ['publisher', 'name', 'active', 'importance', 'last_fetched']

@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ['name', 'link', 'renowned']