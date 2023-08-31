from django.db import models

NEWS_IMPORTANCE = [
        (4, 'Lead Articles News'),
        (3, 'Breaking & Top News'),
        (2, 'Frontpage News'),
        (1, 'Latest News'),
        (0, 'Normal')
    ]

YES_NO = [
        ('Y', 'Yes'),
        ('N', 'No')
    ]


# Create your models here.
class Publisher(models.Model):
    name = models.CharField(max_length=30)
    link = models.URLField()
    RENOWNED_LEVES = [
        (3, 'Top Publisher'),
        (2, 'Higly Renowned Publisher'),
        (1, 'Renowned Publisher'),
        (0, 'Regular Publisher'),
        (-1, 'Lesser-known Publisher'),
        (-2, 'Unknown Publisher'),
        (-3, 'Inaccurate Publisher')
    ]
    paywall = models.CharField(max_length=1, choices=YES_NO, default='N')
    renowned = models.SmallIntegerField(choices=RENOWNED_LEVES, default=0)
    UNIQUE_ARTICLE_ID = [
        ('guid', 'GUID'),
        ('url', 'URL'),
        ('title', 'Title')
    ]
    unique_article_id = models.CharField(choices=UNIQUE_ARTICLE_ID, default='guid', max_length=5)
    language = models.CharField(max_length=5, default='en')

    def __str__(self):
        return f'{self.name}'


class Feed(models.Model):
    name = models.CharField(max_length=40)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    url = models.URLField(max_length=600)
    active = models.BooleanField(default=True)
    last_fetched = models.DateTimeField(null=True, blank=True)
    importance = models.SmallIntegerField(choices=NEWS_IMPORTANCE)
    DISPLAY_SECTION = [
        ('main', 'Main Page'),
        ('side', 'Side Widget')
    ]
    source_categories = models.CharField(max_length=250, null=True, blank=True)
    FEED_ORDER = [
        ('r', 'Relavance'),
        ('d', 'Date')
    ]
    feed_ordering = models.CharField(max_length=1, choices=FEED_ORDER)
    full_text_fetch = models.CharField(max_length=1, choices=YES_NO, default='Y')

    def __str__(self):
        return f'{self.publisher.name} - {self.name}'