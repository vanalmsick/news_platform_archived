"""Containing all Django models related to an indiviual artcile/video"""

from django.db import models

from feeds.models import NEWS_IMPORTANCE, Feed, Publisher


# Create your models here.
class FeedPosition(models.Model):
    """Django Model Class linking a single article/video with a specific feed and containing the relavent
    position in that feed"""

    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    position = models.SmallIntegerField()
    importance = models.SmallIntegerField(choices=NEWS_IMPORTANCE)
    relevance = models.DecimalField(null=True, decimal_places=6, max_digits=12)

    def __str__(self):
        return f"{self.feed} - {self.position}"


class Article(models.Model):
    """Django Model Class for each single article or video"""

    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    feed_position = models.ManyToManyField(FeedPosition)

    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=500, null=True)
    ai_summary = models.TextField(max_length=750, null=True)
    ARTICLE_TYPE = [("breaking", "Breaking/Live News"), ("normal", "Normal Article")]
    type = models.CharField(choices=ARTICLE_TYPE, max_length=8, default="normal")
    CONTENT_TYPES = [
        ("article", "Article"),
        ("ticker", "Live News/Ticker"),
        ("video", "Video"),
    ]
    content_type = models.CharField(
        max_length=10, choices=CONTENT_TYPES, default="article"
    )
    full_text = models.TextField(null=True)
    has_full_text = models.BooleanField(default=True)
    author = models.CharField(max_length=90, null=True)
    link = models.URLField(null=True)
    pub_date = models.DateTimeField(null=True)
    guid = models.CharField(max_length=95, null=True)
    image_url = models.URLField(max_length=300, null=True)

    read_later = models.BooleanField(default=False, null=True)

    added_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)

    min_feed_position = models.SmallIntegerField(null=True)
    min_article_relevance = models.DecimalField(
        null=True, decimal_places=6, max_digits=12
    )
    max_importance = models.SmallIntegerField(choices=NEWS_IMPORTANCE, null=True)

    categories = models.CharField(max_length=250, null=True, blank=True)
    language = models.CharField(max_length=6, null=True, blank=True)

    hash = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.publisher.name} - {self.title}"


class ArticleGroup(models.Model):
    """Django Model Class for grouping single articles/video about the same topic"""

    feeds = models.ManyToManyField(Feed)
    articles = models.ManyToManyField(Article)
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
