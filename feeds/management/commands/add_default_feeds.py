"""mange.py command add_defaullt_feeds to add default data to database"""
from django.core.management import BaseCommand

from feeds.models import Feed, Publisher
from preferences.models import Page


class Command(BaseCommand):
    """command for manage.py"""

    # Show this when the user types help
    help = "Adds StartUp default feeds"

    def handle(self, *args, **options):
        """adds default data to database"""
        initial_publishers = [
            {
                "name": "Financial Times",
                "link": "https://www.ft.com",
                "renowned": 3,
                "paywall": "Y",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "Tagesschau",
                "link": "https://www.tagesschau.de",
                "renowned": 3,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "de",
            },
            {
                "name": "ZDF Heute",
                "link": "https://www.heute.de",
                "renowned": 3,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "de",
            },
            {
                "name": "Redations Netzwerk Deutschland",
                "link": "https://www.rnd.de",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "de",
            },
            {
                "name": "FAZ",
                "link": "https://www.faz.net",
                "renowned": 3,
                "paywall": "Y",
                "unique_article_id": "guid",
                "language": "de",
            },
            {
                "name": "The Economist",
                "link": "http://www.economist.com",
                "renowned": 3,
                "paywall": "Y",
                "unique_article_id": "url",
                "language": "en",
            },
            {
                "name": "Harvard Business Review",
                "link": "https://hbr.org",
                "renowned": 2,
                "paywall": "Y",
                "unique_article_id": "url",
                "language": "en",
            },
            {
                "name": "Wall Street Journal",
                "link": "https://www.wsj.com/",
                "renowned": 2,
                "paywall": "Y",
                "unique_article_id": "url",
                "language": "en",
            },
            {
                "name": "Al Jazeera",
                "link": "https://www.aljazeera.com",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "CNBC",
                "link": "https://www.cnbc.com",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "Risk.net",
                "link": "https://www.risk.net",
                "renowned": 1,
                "paywall": "Y",
                "unique_article_id": "url",
                "language": "en",
            },
            {
                "name": "Hedge Week",
                "link": "https://www.hedgeweek.com",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "url",
                "language": "en",
            },
            {
                "name": "Reuters",
                "link": "https://www.reuters.com",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "url",
                "language": "en",
            },
            {
                "name": "Deutsche Welle",
                "link": "https://www.dw.com",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "title",
                "language": "en",
            },
            {
                "name": "n-tv.de",
                "link": "https://www.n-tv.de",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "de",
            },
            {
                "name": "Bloomberg",
                "link": "https://www.bloomberg.com",
                "renowned": 2,
                "paywall": "Y",
                "unique_article_id": "url",
                "language": "en",
            },
            {
                "name": "BBC",
                "link": "https://www.bbc.com",
                "renowned": 2,
                "paywall": "N",
                "unique_article_id": "url",
                "language": "en",
            },
            {
                "name": "The Trade",
                "link": "http://www.thetradenews.com",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "9to5mac.com",
                "link": "http://www.9to5mac.com",
                "renowned": 2,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "TechCrunch",
                "link": "https://techcrunch.com",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "The Verge",
                "link": "http://www.theverge.com",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "Medium",
                "link": "http://www.medium.com",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "Google News",
                "link": "https://news.google.com",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "Stuff Made Here",
                "link": "https://www.youtube.com/@StuffMadeHere",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "Teulu Tribe",
                "link": "https://www.youtube.com/@TeuluTribe",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "BigThink",
                "link": "https://www.youtube.com/@bigthink",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "EconomicsExplained",
                "link": "https://www.youtube.com/@EconomicsExplained",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "Wendover Productions",
                "link": "https://www.youtube.com/@Wendoverproductions",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "RealEngineering",
                "link": "https://www.youtube.com/@RealEngineering",
                "renowned": 0,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "TED",
                "link": "https://www.ted.com/",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "Vox",
                "link": "https://www.vox.com/",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
            {
                "name": "TheNextWeb",
                "link": "https://www.thenextweb.com/",
                "renowned": 1,
                "paywall": "N",
                "unique_article_id": "guid",
                "language": "en",
            },
        ]

        for publisher in initial_publishers:
            Publisher(**publisher).save()

        initial_feeds = [
            ########################### English News ###########################
            {
                "name": "Home International",
                "publisher": Publisher.objects.get(name="Financial Times"),
                "url": "https://www.ft.com/rss/home/international",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage",
                "importance": 4,
            },
            {
                "name": "Markets",
                "publisher": Publisher.objects.get(name="Financial Times"),
                "url": "https://www.ft.com/markets?format=rss",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;markets",
                "importance": 1,
            },
            {
                "name": "News In Depth",
                "publisher": Publisher.objects.get(name="Financial Times"),
                "url": "https://www.ft.com/news-in-depth?format=rss",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;News In Depth",
                "importance": 2,
            },
            {
                "name": "The Big Read",
                "publisher": Publisher.objects.get(name="Financial Times"),
                "url": "https://www.ft.com/the-big-read?format=rss",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;The Big Read",
                "importance": 2,
            },
            {
                "name": "Country US",
                "publisher": Publisher.objects.get(name="Financial Times"),
                "url": "https://www.ft.com/us?format=rss",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;usa",
                "importance": 0,
            },
            {
                "name": "Country UK",
                "publisher": Publisher.objects.get(name="Financial Times"),
                "url": "https://www.ft.com/world-uk?format=rss",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;uk",
                "importance": 0,
            },
            {
                "name": "Region Europe",
                "publisher": Publisher.objects.get(name="Financial Times"),
                "url": "https://www.ft.com/europe?format=rss",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;europe",
                "importance": 0,
            },
            {
                "name": "Top News",
                "publisher": Publisher.objects.get(name="CNBC"),
                "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage",
                "importance": 1,
            },
            {
                "name": "Markets",
                "publisher": Publisher.objects.get(name="CNBC"),
                "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;markets",
                "importance": 1,
            },
            {
                "name": "Markets",
                "publisher": Publisher.objects.get(name="Reuters"),
                "url": (
                    "http://FEED-CREATOR.local/extract.php?url=https%3A%2F%2Fwww.reuters.com%2Fmarkets%2F&"
                    "in_id_or_class=content-layout__item__SC_GG&max=19&order=document&guid=0&strip_if_url%5B0%5D="
                    "author&strip=.label__label__f9Hew%2C.events__data__18XBG%2C.media-story-card__placement-"
                    "container__1R55-%2C.topic__header__3T_p2&keep_qs_params="
                ),
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;markets",
                "importance": 0,
            },
            {
                "name": "All News",
                "publisher": Publisher.objects.get(name="Risk.net"),
                "url": "http://www.risk.net/feeds/rss/",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage",
                "importance": 0,
            },
            {
                "name": "All News",
                "publisher": Publisher.objects.get(name="Al Jazeera"),
                "url": "https://www.aljazeera.com/xml/rss/all.xml",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage",
                "importance": 2,
            },
            {
                "name": "All News",
                "publisher": Publisher.objects.get(name="Deutsche Welle"),
                "url": "http://rss.dw.com/rdf/rss-en-all",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "source_categories": "frontpage",
                "importance": 1,
            },
            {
                "name": "Markets",
                "publisher": Publisher.objects.get(name="Bloomberg"),
                "url": "https://feeds.bloomberg.com/markets/news.rss",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "N",
                "source_categories": "frontpage;markets",
                "importance": 3,
            },
            {
                "name": "Politics",
                "publisher": Publisher.objects.get(name="Bloomberg"),
                "url": "https://feeds.bloomberg.com/politics/news.rss",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "N",
                "source_categories": "frontpage;politics",
                "importance": 1,
            },
            {
                "name": "Top News",
                "publisher": Publisher.objects.get(name="The Economist"),
                "url": (
                    "http://FEED-CREATOR.local/mergefeeds.php?url%5B0%5D=https%3A%2F%2Fwww.economist.com%2F"
                    "briefing%2Frss.xml&url%5B1%5D=https%3A%2F%2Fwww.economist.com%2Ffinance-and-economics%2F"
                    "rss.xml&max=5&order=date"
                ),
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;magazine",
                "importance": 1,
            },
            {
                "name": "Countries",
                "publisher": Publisher.objects.get(name="The Economist"),
                "url": (
                    "http://FEED-CREATOR.local/mergefeeds.php?url%5B0%5D=https%3A%2F%2Fwww.economist.com%2F"
                    "europe%2Frss.xml&url%5B1%5D=https%3A%2F%2Fwww.economist.com%2Finternational%2Frss.xml&"
                    "url%5B2%5D=https%3A%2F%2Fwww.economist.com%2Funited-states%2Frss.xml&url%5B3%5D="
                    "https%3A%2F%2Fwww.economist.com%2Fthe-americas%2Frss.xml&url%5B4%5D=https%3A%2F%2F"
                    "www.economist.com%2Fmiddle-east-and-africa%2Frss.xml&url%5B5%5D=https%3A%2F%2F"
                    "www.economist.com%2Fasia%2Frss.xml&url%5B6%5D=https%3A%2F%2F"
                    "www.economist.com%2Fchina%2Frss.xml&url%5B7%5D=https%3A%2F%2F"
                    "www.economist.com%2Fbritain%2Frss.xml&max=12&order=date"
                ),
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;magazine;world",
                "importance": 0,
            },
            ########################### Fund News ###########################
            {
                "name": "All News",
                "publisher": Publisher.objects.get(name="The Trade"),
                "url": "https://www.thetradenews.com/feed/",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "source_categories": "frontpage;funds;sidebar",
                "importance": 1,
            },
            {
                "name": "Latest",
                "publisher": Publisher.objects.get(name="Hedge Week"),
                "url": "https://www.hedgeweek.com/feed/",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "source_categories": "hedge funds;funds;sidebar",
                "importance": 3,
            },
            {
                "name": 'Search "Hedge Funds"',
                "publisher": Publisher.objects.get(name="Google News"),
                "url": "https://news.google.com/rss/search?q=hedge+fund",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "source_categories": "google news;hedge funds;funds;sidebar",
                "importance": 0,
            },
            ########################### German News ###########################
            {
                "name": "Startseite",
                "publisher": Publisher.objects.get(name="Tagesschau"),
                "url": "https://www.tagesschau.de/index~rss2.xml",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "startseite",
                "importance": 2,
            },
            {
                "name": "Startseite",
                "publisher": Publisher.objects.get(name="FAZ"),
                "url": "https://www.faz.net/rss/aktuell/",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "startseite",
                "importance": 1,
            },
            {
                "name": "Startseite",
                "publisher": Publisher.objects.get(name="ZDF Heute"),
                "url": "https://www.zdf.de/rss/zdf/nachrichten",
                "active": False,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "startseite",
                "importance": 2,
            },
            {
                "name": "Wirtschaft",
                "publisher": Publisher.objects.get(name="n-tv.de"),
                "url": "https://www.n-tv.de/wirtschaft/rss",
                "active": False,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "wirtschaft",
                "importance": 1,
            },
            {
                "name": "Politik",
                "publisher": Publisher.objects.get(name="n-tv.de"),
                "url": "https://www.n-tv.de/politik/rss",
                "active": False,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "politik",
                "importance": 1,
            },
            {
                "name": "Politik",
                "publisher": Publisher.objects.get(
                    name="Redations Netzwerk Deutschland"
                ),
                "url": "https://www.rnd.de/arc/outboundfeeds/rss/category/politik/",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "wirtschaft",
                "importance": 1,
            },
            {
                "name": "Wirtschaft",
                "publisher": Publisher.objects.get(
                    name="Redations Netzwerk Deutschland"
                ),
                "url": "https://www.rnd.de/arc/outboundfeeds/rss/category/wirtschaft/",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "politik",
                "importance": 1,
            },
            ########################### Tech News ###########################
            {
                "name": "Technology",
                "publisher": Publisher.objects.get(name="Bloomberg"),
                "url": "https://feeds.bloomberg.com/technology/news.rss",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "N",
                "source_categories": "tech",
                "importance": 0,
            },
            {
                "name": "Home",
                "publisher": Publisher.objects.get(name="9to5mac.com"),
                "url": "http://9to5mac.com/feed/",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "source_categories": "tech",
                "importance": 2,
            },
            {
                "name": "Home",
                "publisher": Publisher.objects.get(name="TechCrunch"),
                "url": "http://feeds.feedburner.com/Techcrunch",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "tech",
                "importance": 2,
            },
            {
                "name": "Home",
                "publisher": Publisher.objects.get(name="The Verge"),
                "url": "http://www.theverge.com/rss/full.xml",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "tech",
                "importance": 2,
            },
            {
                "name": "Home",
                "publisher": Publisher.objects.get(name="TheNextWeb"),
                "url": "https://thenextweb.com/feed",
                "active": True,
                "feed_ordering": "r",
                "full_text_fetch": "Y",
                "source_categories": "tech",
                "importance": 2,
            },
            {
                "name": "#Python",
                "publisher": Publisher.objects.get(name="Medium"),
                "url": "https://medium.com/feed/tag/python",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "N",
                "source_categories": "tech",
                "importance": 0,
            },
            ########################### YouTube Channels ###########################
            {
                "name": "Originals - YouTube Channel",
                "publisher": Publisher.objects.get(name="Bloomberg"),
                "url": "https://www.youtube.com/Bloomberg",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 1,
            },
            {
                "name": "Quicktake - YouTube Channel",
                "publisher": Publisher.objects.get(name="Bloomberg"),
                "url": "https://www.youtube.com/@BloombergQuicktake",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 2,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="Financial Times"),
                "url": "https://www.youtube.com/@FinancialTimes",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 1,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="The Economist"),
                "url": "https://www.youtube.com/@TheEconomist",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 1,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="Harvard Business Review"),
                "url": "https://www.youtube.com/@harvardbusinessreview",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 2,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="Wall Street Journal"),
                "url": "https://www.youtube.com/@wsj",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 2,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="Stuff Made Here"),
                "url": "https://www.youtube.com/@StuffMadeHere",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 0,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="Teulu Tribe"),
                "url": "https://www.youtube.com/@TeuluTribe",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 1,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="Deutsche Welle"),
                "url": "https://www.youtube.com/@DWDocumentary",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 2,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="CNBC"),
                "url": "https://www.youtube.com/@CNBC",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 2,
            },
            {
                "name": "TED - YouTube Channel",
                "publisher": Publisher.objects.get(name="TED"),
                "url": "https://www.youtube.com/@TED",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 2,
            },
            {
                "name": "TEDed - YouTube Channel",
                "publisher": Publisher.objects.get(name="TED"),
                "url": "https://www.youtube.com/@TEDEd",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 1,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="Vox"),
                "url": "https://www.youtube.com/@Vox",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 1,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="Wendover Productions"),
                "url": "https://www.youtube.com/@Wendoverproductions",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 1,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="BigThink"),
                "url": "https://www.youtube.com/@bigthink",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 1,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="EconomicsExplained"),
                "url": "https://www.youtube.com/@EconomicsExplained",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 2,
            },
            {
                "name": "YouTube Channel",
                "publisher": Publisher.objects.get(name="RealEngineering"),
                "url": "https://www.youtube.com/@RealEngineering",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-channel",
                "importance": 1,
            },
            {
                "name": "World Services - YouTube Playlist",
                "publisher": Publisher.objects.get(name="BBC"),
                "url": "https://www.youtube.com/playlist?list=PLz_B0PFGIn4fADt3h_U2SOWErIq-xtXPD",
                "active": True,
                "feed_ordering": "d",
                "full_text_fetch": "Y",
                "feed_type": "y-playlist",
                "importance": 1,
            },
        ]

        for feed in initial_feeds:
            Feed(**feed).save()

        initial_pages = [
            {
                "position_index": 1,
                "html_icon": "",
                "name": "Frontpage",
                "url_parameters": "categories=frontpage",
            },
            {
                "position_index": 2,
                "html_icon": (
                    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"'
                    ' fill="currentColor" class="bi bi-translate" viewBox="0 0 16'
                    ' 16"><path d="M4.545 6.714 4.11 8H3l1.862-5h1.284L8'
                    " 8H6.833l-.435-1.286H4.545zm1.634-.736L5.5 3.956h-.049l-.679"
                    ' 2.022H6.18z"/><path d="M0 2a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v3h3a2 2'
                    " 0 0 1 2 2v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-3H2a2 2 0 0"
                    " 1-2-2V2zm2-1a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V2a1 1"
                    " 0 0 0-1-1H2zm7.138 9.995c.193.301.402.583.63.846-.748.575-1.673"
                    " 1.001-2.768 1.292.178.217.451.635.555.867 1.125-.359 2.08-.844"
                    " 2.886-1.494.777.665 1.739 1.165 2.93"
                    " 1.472.133-.254.414-.673.629-.89-1.125-.253-2.057-.694-2.82-1.284.681-.747"
                    " 1.222-1.651 1.621-2.757H14V8h-3v1.047h.765c-.318.844-.74"
                    " 1.546-1.272 2.13a6.066 6.066 0 0 1-.415-.492 1.988 1.988 0 0"
                    ' 1-.94.31z"/></svg>'
                ),
                "name": "German",
                "url_parameters": "language=de",
            },
            {
                "position_index": 3,
                "html_icon": "#",
                "name": "Tech",
                "url_parameters": "categories=tech",
            },
            {
                "position_index": 4,
                "html_icon": (
                    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"'
                    ' fill="currentColor" class="bi bi-clock" viewBox="0 0 16 16"><path'
                    ' d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0'
                    ' .496-.868L8 8.71V3.5z"/><path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0'
                    ' 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z"/></svg>'
                ),
                "name": "Latest: Funds",
                "url_parameters": "special=sidebar",
            },
            {
                "position_index": 5,
                "html_icon": "@",
                "name": "FT & BBG",
                "url_parameters": (
                    "publisher__name=financial+times,bloomberg&content_type=article"
                ),
            },
            {
                "position_index": 6,
                "html_icon": (
                    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"'
                    ' fill="currentColor" class="bi bi-play-btn" viewBox="0 0 16'
                    ' 16"><path d="M6.79 5.093A.5.5 0 0 0 6 5.5v5a.5.5 0 0 0'
                    ' .79.407l3.5-2.5a.5.5 0 0 0 0-.814l-3.5-2.5z"/><path d="M0 4a2 2 0'
                    " 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm15"
                    " 0a1 1 0 0 0-1-1H2a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h12a1 1 0 0 0"
                    ' 1-1V4z"/></svg>'
                ),
                "name": "Videos",
                "url_parameters": "content_type=video",
            },
            {
                "position_index": 7,
                "html_icon": (
                    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"'
                    ' fill="currentColor" class="bi bi-bookmark" viewBox="0 0 16 16"> '
                    ' <path d="M2 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v13.5a.5.5 0 0'
                    " 1-.777.416L8 13.101l-5.223 2.815A.5.5 0 0 1 2 15.5zm2-1a1 1 0 0"
                    " 0-1 1v12.566l4.723-2.482a.5.5 0 0 1 .554 0L13 14.566V2a1 1 0 0"
                    ' 0-1-1z"/></svg>'
                ),
                "name": "Read Later",
                "url_parameters": "read_later=true",
            },
        ]

        for page in initial_pages:
            Page(**page).save()
