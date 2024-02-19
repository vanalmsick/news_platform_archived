from django.db import models


# Create your models here.
class DataGroup(models.Model):
    name = models.CharField(max_length=200)
    position = models.IntegerField()

    def __str__(self):
        """print-out representation of individual model entry"""
        return f"{self.name}"


class DataSource(models.Model):
    """Django Model Class for each single article or video"""

    group = models.ForeignKey(DataGroup, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    pinned = models.BooleanField(default=False)

    DATA_SRC = [
        ("yfin", "Yahoo Finance"),
        ("te", "Trading Economics"),
    ]
    data_source = models.CharField(max_length=4, choices=DATA_SRC, default="yfin")
    ticker = models.CharField(max_length=20)

    def __str__(self):
        """print-out representation of individual model entry"""
        return f"{self.name} ({self.ticker} / {self.group})"


class DataEntry(models.Model):
    """Django Model Class for each single article or video"""

    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    ref_date_time = models.DateTimeField(auto_now_add=True)
    fetched = models.DateTimeField(auto_now_add=True)

    price = models.DecimalField(decimal_places=4, max_digits=12)
    change_today = models.DecimalField(decimal_places=6, max_digits=12)

    def __str__(self):
        """print-out representation of individual model entry"""
        return f"{self.source} - {self.ref_date_time} - {self.price}"
