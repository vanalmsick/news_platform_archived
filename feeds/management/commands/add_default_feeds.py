from django.core.management import BaseCommand
from feeds.models import Feed, Publisher

class Command(BaseCommand):
    # Show this when the user types help
    help = "Adds StartUp default feeds"

    def handle(self, *args, **options):
        initial_publishers = [
            {'name': 'Financial Times',
             'link': 'https://www.ft.com',
             'renowned': 3,
             'img_scrape_urls': 'https://www.ft.com\nhttps://www.ft.com/news-feed'},
            {'name': 'The Economist',
             'link': 'http://www.economist.com',
             'renowned': 3,
             'img_scrape_urls': 'http://www.economist.com'},
            {'name': 'Al Jazeera',
             'link': 'https://www.aljazeera.com',
             'renowned': 1,
             'img_scrape_urls': 'https://www.aljazeera.com'},
            {'name': 'Reuters',
             'link': 'https://www.reuters.com',
             'renowned': 1,
             'img_scrape_urls': 'https://www.reuters.com'},
            {'name': 'Detsche Welle',
             'link': 'https://www.dw.com\nhttps://www.dw.com/en/headlines/headlines-en',
             'renowned': 1,
             'img_scrape_urls': 'https://www.dw.com'}
        ]

        for publisher in initial_publishers:
            Publisher(**publisher).save()


        initial_feeds = [
            {'name': 'Financial Times - International',
             'publisher': Publisher.objects.get(name='Financial Times'),
             'url': 'https://www.ft.com/rss/home/international',
             'active': True,
             'paywall': 'Y',
             'feed_ordering': 'r',
             'full_text_fetch': 'N',
             'importance': 2},
            {'name': 'Financial Times - Markets',
             'publisher': Publisher.objects.get(name='Financial Times'),
             'url': 'https://www.ft.com/markets?format=rss',
             'active': True,
             'paywall': 'Y',
             'feed_ordering': 'r',
             'full_text_fetch': 'N',
             'importance': 0,
             'genre': 'finance'},
            {'name': 'The Economist',
             'publisher': Publisher.objects.get(name='The Economist'),
             'url': 'http://www.economist.com/feeds/print-sections/79/finance-and-economics.xml',
             'active': True,
             'paywall': 'Y',
             'feed_ordering': 'r',
             'full_text_fetch': 'N',
             'importance': 0,
             'genre': 'finance'},
            {'name': 'Al Jazeera',
             'publisher': Publisher.objects.get(name='Al Jazeera'),
             'url': 'https://www.aljazeera.com/xml/rss/all.xml',
             'active': True,
             'paywall': 'N',
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'importance': 2},
            {'name': 'Detsche Welle - Top',
             'publisher': Publisher.objects.get(name='Detsche Welle'),
             'url': 'http://rss.dw.com/rdf/rss-en-all',
             'active': True,
             'paywall': 'N',
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'importance': 2,
             'genre': 'world'}
        ]


        for feed in initial_feeds:
            Feed(**feed).save()
