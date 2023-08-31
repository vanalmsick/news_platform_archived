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
             'paywall': 'Y',
             'unique_article_id': 'guid',
             'language': 'en'},
            {'name': 'Tagesschau',
             'link': 'https://www.tagesschau.de',
             'renowned': 3,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'de'},
            {'name': 'ZDF Heute',
             'link': 'https://www.heute.de',
             'renowned': 3,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'de'},
            {'name': 'The Economist',
             'link': 'http://www.economist.com',
             'renowned': 3,
             'paywall': 'Y',
             'unique_article_id': 'url',
             'language': 'en'},
            {'name': 'Al Jazeera',
             'link': 'https://www.aljazeera.com',
             'renowned': 1,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'en'},
            {'name': 'CNBC',
             'link': 'https://www.cnbc.com',
             'renowned': 1,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'en'},
            {'name': 'Risk.net',
             'link': 'https://www.risk.net',
             'renowned': 1,
             'paywall': 'Y',
             'unique_article_id': 'url',
             'language': 'en'},
            {'name': 'Reuters',
             'link': 'https://www.reuters.com',
             'renowned': 1,
             'paywall': 'N',
             'unique_article_id': 'url',
             'language': 'en'},
            {'name': 'Deutsche Welle',
             'link': 'https://www.dw.com',
             'renowned': 1,
             'paywall': 'N',
             'unique_article_id': 'title',
             'language': 'en'},
            {'name': 'n-tv.de',
             'link': 'https://www.n-tv.de',
             'renowned': 1,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'de'},
            {'name': 'Bloomberg',
             'link': 'https://www.bloomberg.com',
             'renowned': 2,
             'paywall': 'Y',
             'unique_article_id': 'url',
             'language': 'en'},
            {'name': 'The Trade',
             'link': 'http://www.thetradenews.com',
             'renowned': 0,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'en'},
            {'name': '9to5mac.com',
             'link': 'http://www.9to5mac.com',
             'renowned': 1,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'en'},
            {'name': 'TechCrunch',
             'link': 'https://techcrunch.com',
             'renowned': 1,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'en'},
            {'name': 'The Verge',
             'link': 'http://www.theverge.com',
             'renowned': 1,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'en'},
            {'name': 'Google News',
             'link': 'https://news.google.com',
             'renowned': 0,
             'paywall': 'N',
             'unique_article_id': 'guid',
             'language': 'en'}
        ]

        for publisher in initial_publishers:
            Publisher(**publisher).save()

        initial_feeds = [
            {'name': 'Home International',
             'publisher': Publisher.objects.get(name='Financial Times'),
             'url': 'https://www.ft.com/rss/home/international',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage',
             'importance': 4},
            {'name': 'Markets',
             'publisher': Publisher.objects.get(name='Financial Times'),
             'url': 'https://www.ft.com/markets?format=rss',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;markets',
             'importance': 0},
            {'name': 'Country US',
             'publisher': Publisher.objects.get(name='Financial Times'),
             'url': 'https://www.ft.com/us?format=rss',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;usa',
             'importance': 0},
            {'name': 'Country UK',
             'publisher': Publisher.objects.get(name='Financial Times'),
             'url': 'https://www.ft.com/world-uk?format=rss',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;uk',
             'importance': 0},
            {'name': 'Region Europe',
             'publisher': Publisher.objects.get(name='Financial Times'),
             'url': 'https://www.ft.com/europe?format=rss',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;europe',
             'importance': 0},
            {'name': 'Top News',
             'publisher': Publisher.objects.get(name='CNBC'),
             'url': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage',
             'importance': 1},
            {'name': 'Markets',
             'publisher': Publisher.objects.get(name='CNBC'),
             'url': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258',
             'active': False,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;markets',
             'importance': 1},
            {'name': 'Next Opinions',
             'publisher': Publisher.objects.get(name='Reuters'),
             'url': 'http://FEED-CREATOR.local/extract.php?url=https%3A%2F%2Fwww.reuters.com%2Fworld%2Freuters-next%2F&in_id_or_class=content-layout__item__SC_GG&max=10&order=document&guid=0&strip=.label__label__f9Hew%2C.events__data__18XBG&keep_qs_params=',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;opinion',
             'importance': 1},
            {'name': 'Markets',
             'publisher': Publisher.objects.get(name='Reuters'),
             'url': 'http://FEED-CREATOR.local/extract.php?url=https%3A%2F%2Fwww.reuters.com%2Fmarkets%2F&in_id_or_class=content-layout__item__SC_GG&max=19&order=document&guid=0&strip_if_url%5B0%5D=author&strip=.label__label__f9Hew%2C.events__data__18XBG%2C.media-story-card__placement-container__1R55-%2C.topic__header__3T_p2&keep_qs_params=',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;markets',
             'importance': 1},
            {'name': 'All News',
             'publisher': Publisher.objects.get(name='Risk.net'),
             'url': 'http://www.risk.net/feeds/rss/',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage',
             'importance': 1},
            {'name': 'All News',
             'publisher': Publisher.objects.get(name='Al Jazeera'),
             'url': 'https://www.aljazeera.com/xml/rss/all.xml',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage',
             'importance': 2},
            {'name': 'All News',
             'publisher': Publisher.objects.get(name='Deutsche Welle'),
             'url': 'http://rss.dw.com/rdf/rss-en-all',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage',
             'importance': 2},
            {'name': 'Markets',
             'publisher': Publisher.objects.get(name='Bloomberg'),
             'url': 'https://feeds.bloomberg.com/markets/news.rss',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'N',
             'source_categories': 'frontpage;markets',
             'importance': 2},
            {'name': 'Politics',
             'publisher': Publisher.objects.get(name='Bloomberg'),
             'url': 'https://feeds.bloomberg.com/politics/news.rss',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'N',
             'source_categories': 'frontpage;politics',
             'importance': 2},
            {'name': 'Top News',
             'publisher': Publisher.objects.get(name='The Economist'),
             'url': 'http://FEED-CREATOR.local/mergefeeds.php?url%5B0%5D=https%3A%2F%2Fwww.economist.com%2Fbriefing%2Frss.xml&url%5B1%5D=https%3A%2F%2Fwww.economist.com%2Ffinance-and-economics%2Frss.xml&max=5&order=date',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;magazine',
             'importance': 0},
            {'name': 'Countries',
             'publisher': Publisher.objects.get(name='The Economist'),
             'url': 'http://FEED-CREATOR.local/mergefeeds.php?url%5B0%5D=https%3A%2F%2Fwww.economist.com%2Feurope%2Frss.xml&url%5B1%5D=https%3A%2F%2Fwww.economist.com%2Finternational%2Frss.xml&url%5B2%5D=https%3A%2F%2Fwww.economist.com%2Funited-states%2Frss.xml&url%5B3%5D=https%3A%2F%2Fwww.economist.com%2Fthe-americas%2Frss.xml&url%5B4%5D=https%3A%2F%2Fwww.economist.com%2Fmiddle-east-and-africa%2Frss.xml&url%5B5%5D=https%3A%2F%2Fwww.economist.com%2Fasia%2Frss.xml&url%5B6%5D=https%3A%2F%2Fwww.economist.com%2Fchina%2Frss.xml&url%5B7%5D=https%3A%2F%2Fwww.economist.com%2Fbritain%2Frss.xml&max=12&order=date',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;magazine;world',
             'importance': 0},
            {'name': 'All News',
             'publisher': Publisher.objects.get(name='The Trade'),
             'url': 'https://www.thetradenews.com/feed/',
             'active': True,
             'feed_ordering': 'd',
             'full_text_fetch': 'Y',
             'source_categories': 'frontpage;funds;sidebar',
             'importance': 2},
            {'name': 'Search "Hedge Funds"',
             'publisher': Publisher.objects.get(name='Google News'),
             'url': 'https://news.google.com/rss/search?q=hedge+fund',
             'active': True,
             'feed_ordering': 'd',
             'full_text_fetch': 'Y',
             'source_categories': 'google news;hedge funds;funds;sidebar',
             'importance': 0},
            {'name': 'Startseite',
             'publisher': Publisher.objects.get(name='Tagesschau'),
             'url': 'https://www.tagesschau.de/index~rss2.xml',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': '',
             'importance': 2},
            {'name': 'Startseite',
             'publisher': Publisher.objects.get(name='ZDF Heute'),
             'url': 'https://www.zdf.de/rss/zdf/nachrichten',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': '',
             'importance': 2},
            {'name': 'Wirtschaft',
             'publisher': Publisher.objects.get(name='n-tv.de'),
             'url': 'https://www.n-tv.de/wirtschaft/rss',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': '',
             'importance': 1},
            {'name': 'Politik',
             'publisher': Publisher.objects.get(name='n-tv.de'),
             'url': 'https://www.n-tv.de/politik/rss',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': '',
             'importance': 1},
            {'name': 'Technology',
             'publisher': Publisher.objects.get(name='Bloomberg'),
             'url': 'https://feeds.bloomberg.com/technology/news.rss',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'N',
             'source_categories': 'tech',
             'importance': 1},
            {'name': 'Home',
             'publisher': Publisher.objects.get(name='9to5mac.com'),
             'url': 'http://9to5mac.com/feed/',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'tech',
             'importance': 1},
            {'name': 'Home',
             'publisher': Publisher.objects.get(name='TechCrunch'),
             'url': 'http://feeds.feedburner.com/Techcrunch',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'tech',
             'importance': 1},
            {'name': 'Home',
             'publisher': Publisher.objects.get(name='The Verge'),
             'url': 'http://www.theverge.com/rss/full.xml',
             'active': True,
             'feed_ordering': 'r',
             'full_text_fetch': 'Y',
             'source_categories': 'tech',
             'importance': 1}
        ]

        for feed in initial_feeds:
            Feed(**feed).save()
