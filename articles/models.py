# -*- coding: utf-8 -*-
"""Containing all Django models related to an indiviual artcile/video"""

import urllib

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from feeds.models import NEWS_IMPORTANCE, Feed, Publisher


# Create your models here.
class ArticleGroup(models.Model):
    """Django Model Class for grouping single articles/video about the same topic"""

    title = models.CharField(max_length=30)
    summary = models.CharField(max_length=250, null=True)
    full_text = models.TextField(null=True)
    author = models.CharField(max_length=50, null=True)
    link = models.URLField(null=True)
    pub_date = models.DateTimeField(null=True)
    guid = models.CharField(max_length=75, null=True)
    image_url = models.TextField(null=True)
    min_feed_position = models.SmallIntegerField()
    min_article_relevance = models.DecimalField(
        null=True, decimal_places=6, max_digits=12
    )
    max_importance = models.SmallIntegerField(choices=NEWS_IMPORTANCE)
    categories = models.CharField(max_length=250, null=True)
    language = models.CharField(max_length=6, null=True)
    hash = models.CharField(max_length=80)

    def __str__(self):
        """print-out name of individual entry"""
        return f"{self.title}"


class Article(models.Model):
    """Django Model Class for each single article or video"""

    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    article_group = models.ForeignKey(
        ArticleGroup, on_delete=models.SET_NULL, null=True, blank=True
    )

    title = models.CharField(max_length=200, null=True)

    author = models.CharField(max_length=90, null=True, blank=True)
    link = models.URLField()
    image_url = models.URLField(max_length=300, null=True, blank=True)

    IMPORTANCE_TYPES = [
        ("breaking", "Breaking/Live News"),
        ("headline", "Headline/Top Articles"),
        ("normal", "Normal Article"),
    ]
    importance_type = models.CharField(
        choices=IMPORTANCE_TYPES, max_length=8, default="normal"
    )
    CONTENT_TYPES = [
        ("article", "Article"),
        ("ticker", "Live News/Ticker"),
        ("briefing", "Briefing/Newsletter"),
        ("video", "Video"),
    ]
    content_type = models.CharField(
        max_length=10, choices=CONTENT_TYPES, default="article"
    )

    extract = models.CharField(max_length=500, null=True, blank=True)
    has_extract = models.BooleanField(default=True)

    ai_summary = models.TextField(max_length=750, null=True, blank=True)

    full_text_html = models.TextField(null=True, blank=True)
    full_text_text = models.TextField(null=True, blank=True)
    has_full_text = models.BooleanField(default=True)

    pub_date = models.DateTimeField(null=True, blank=True)
    added_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)

    read_later = models.BooleanField(default=False)
    archive = models.BooleanField(default=False)

    categories = models.CharField(max_length=250, null=True, blank=True)
    language = models.CharField(max_length=6, null=True, blank=True)

    guid = models.CharField(max_length=95, null=True, blank=True)
    hash = models.CharField(max_length=100)

    publisher_article_position = models.SmallIntegerField(null=True)
    min_feed_position = models.SmallIntegerField(null=True)
    min_article_relevance = models.DecimalField(
        decimal_places=6, max_digits=12, null=True
    )
    max_importance = models.SmallIntegerField(choices=NEWS_IMPORTANCE, null=True)

    mailto_link = models.CharField(max_length=300, null=True)

    def __calc_mailto_link(self):
        """Create the caluclated field that stores the mailto link to share an artcile via email"""
        SHARE_EMAIL_SUBJECT = f"{self.publisher.name}: {self.title}"
        SHARE_EMAIL_BODY = (
            "Hi,\n\nHave you seen this article:\n\n"
            f"{SHARE_EMAIL_SUBJECT}\n"
            f"{self.link}\n\n"
            "Best wishes,\n\n"
        )
        return (
            "mailto:?subject="
            + urllib.parse.quote(SHARE_EMAIL_SUBJECT)
            + "&body="
            + urllib.parse.quote(SHARE_EMAIL_BODY)
        )

    def __init__(self, *args, **kwargs):
        args = [
            None if i in ["", " "] else i for i in args
        ]  # ensure blanks '' or ' ' are replaced with None/Null
        super(Article, self).__init__(*args, **kwargs)
        # self.__original = self._dict

    # @property
    # def _dict(self):
    #    return model_to_dict(self, fields=[field.name for field in self._meta.fields])

    def save(self, *args, **kwargs):
        """Make sure the min and max fields are refreshed on every update"""
        self.mailto_link = self.__calc_mailto_link()
        super(Article, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.publisher.name} - {self.title}"


@receiver(pre_save, sender=Article)
def truncate_long_fields(sender, instance, **kwargs):
    """Make sure fields with a max_length attr are truncated if too long"""
    # Define a list of fields you want to check and truncate
    fields_to_check = [
        "title",
        "author",
        "image_url",
        "extract",
        "ai_summary",
        "categories",
        "guid",
        "hash",
        "mailto_link",
    ]  # Add more fields as needed

    for field_name in fields_to_check:
        field = getattr(instance, field_name)
        max_length = instance._meta.get_field(field_name).max_length
        if field is not None and len(field) > max_length:
            setattr(instance, field_name, field[:max_length])


class FeedPosition(models.Model):
    """Django Model Class linking a single article/video with a specific feed and containing the relavent
    position in that feed"""

    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)

    position = models.SmallIntegerField()
    importance = models.SmallIntegerField(choices=NEWS_IMPORTANCE)
    relevance = models.DecimalField(null=True, decimal_places=6, max_digits=12)

    def __str__(self):
        return f"{self.feed} - {self.position}"

    def __calc_min__max__(self):
        if self.article is not None:
            was_updated = False
            for article_key, position_key in dict(
                max_importance="importance",
                min_feed_position="position",
                min_article_relevance="relevance",
            ).items():
                if getattr(self.article, article_key) is None:
                    setattr(self.article, article_key, getattr(self, position_key))
                    was_updated = True
                elif "max" in article_key and getattr(
                    self.article, article_key
                ) < getattr(self, position_key):
                    setattr(self.article, article_key, getattr(self, position_key))
                    was_updated = True
                elif "min" in article_key and getattr(
                    self.article, article_key
                ) > getattr(self, position_key):
                    setattr(self.article, article_key, getattr(self, position_key))
                    was_updated = True
            if was_updated:
                self.article.save()

    def save(self, *args, **kwargs):
        """Make sure the min and max fields are refreshed on every update"""
        self.__calc_min__max__()
        super(FeedPosition, self).save(*args, **kwargs)
