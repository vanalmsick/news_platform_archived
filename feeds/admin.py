# -*- coding: utf-8 -*-
"""Definition of Publisher and Feed Views in Django Admin Space"""

from django.contrib import admin
from django.contrib.auth.models import Group, User
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Feed, Publisher

# Register your models here.


class FeedsInline(admin.TabularInline):
    """Table of feeds to be shown in single-Publisher view"""

    model = Feed
    fk_name = "publisher"
    extra = 0
    exclude = ["last_fetched"]


class FeedImportExport(resources.ModelResource):
    """Data class for import/export functionality of Feeds"""

    class Meta:
        model = Feed


class PublisherImportExport(resources.ModelResource):
    """Data class for import/export functionality of Publishers"""

    class Meta:
        model = Publisher


@admin.register(Feed)
class FeedAdmin(ImportExportModelAdmin):
    """Main Admin Feed View"""

    list_display = [
        "publisher",
        "name",
        "active",
        "importance",
        "feed_type",
        "source_categories",
    ]
    ordering = ("feed_type", "-importance", "-active", "name")
    resource_classes = [FeedImportExport]


@admin.register(Publisher)
class PublisherAdmin(ImportExportModelAdmin):
    """Main Admin Publisher View"""

    list_display = ["name", "link", "renowned", "paywall", "language"]
    inlines = [
        FeedsInline,
    ]
    ordering = (
        "-renowned",
        "-language",
        "name",
    )
    resource_classes = [PublisherImportExport]


admin.site.unregister(User)
admin.site.unregister(Group)
