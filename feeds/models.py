from django.db import models

NEWS_IMPORTANCE = [
        (4, 'Lead Articles News'),
        (3, 'Breaking & Top News'),
        (2, 'Frontpage News'),
        (1, 'Latest News'),
        (0, 'Normal')
    ]

NEWS_GENRES = [
        ('world', 'World'),
        ('europe', 'Europe / EU / UK'),
        ('us', 'US'),
        ('other_cntrys', 'Asia / Pacific / Middle East / Africa / Americas'),
        ('finance', 'Economics / Finance / Markets / Business'),
        ('tech', 'Technology'),
        ('science', 'Science'),
        ('lifestyle', 'Culture / Lifestyle / Health'),
        ('sport', 'Sport'),
        ('unknown', 'Unknown')
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
    renowned = models.SmallIntegerField(choices=RENOWNED_LEVES, default=0)
    img_scrape_urls = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.name}'


class Feed(models.Model):
    name = models.CharField(max_length=30)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    url = models.URLField()
    active = models.BooleanField(default=True)
    last_fetched = models.DateTimeField(null=True, blank=True)
    importance = models.SmallIntegerField(choices=NEWS_IMPORTANCE)
    genre = models.CharField(choices=NEWS_GENRES, max_length=15, null=True, blank=True)
    paywall = models.CharField(max_length=1, choices=YES_NO, default='N')
    FEED_ORDER = [
        ('r', 'Relavance'),
        ('d', 'Date')
    ]
    feed_ordering = models.CharField(max_length=1, choices=FEED_ORDER)
    full_text_fetch = models.CharField(max_length=1, choices=YES_NO, default='Y')
    clicked_articles = models.SmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.name}'