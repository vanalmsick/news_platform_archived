from django.shortcuts import render
from django.core.cache import cache
from feed_scraper.scraper import update_feeds
from articles.models import Article
from django.db.models import Q, F
import datetime
from .pageLogin import LoginForm, LoginView
from django.utils.safestring import mark_safe
from .pageAPI import get_article_data
from django.contrib.auth import login, authenticate

def getDuration(then, now=datetime.datetime.now(), interval="default"):
    # Returns a duration as specified by variable interval
    # Functions, except totalDuration, returns [quotient, remainder]

    duration = now - then  # For build-in functions
    duration_in_s = duration.total_seconds()

    def years():
        return divmod(duration_in_s, 31536000)  # Seconds in a year=31536000.

    def days(seconds=None):
        return divmod(seconds if seconds != None else duration_in_s, 86400)  # Seconds in a day = 86400

    def hours(seconds=None):
        return divmod(seconds if seconds != None else duration_in_s, 3600)  # Seconds in an hour = 3600

    def minutes(seconds=None):
        return divmod(seconds if seconds != None else duration_in_s, 60)  # Seconds in a minute = 60

    def seconds(seconds=None):
        if seconds != None:
            return divmod(seconds, 1)
        return duration_in_s

    def totalDuration():
        y = years()
        d = days(y[1])  # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])

        return "Time between dates: {} years, {} days, {} hours, {} minutes and {} seconds".format(int(y[0]), int(d[0]),
                                                                                                   int(h[0]), int(m[0]),
                                                                                                   int(s[0]))

    def shortDuration():
        y = years()
        d = days(y[1])  # Use remainder to calculate next variable
        h = hours(d[1])
        m = minutes(h[1])
        s = seconds(m[1])

        if y[0] > 0:
            return '{} years, {} days'.format(int(y[0]), int(d[0]))
        elif d[0] > 0:
            return '{} days, {} hours'.format(int(d[0]), int(h[0]))
        elif h[0] > 0:
            return '{}h {}min'.format(int(h[0]), int(m[0]))
        elif m[0] > 0:
            return '{}min {}s'.format(int(m[0]), int(s[0]))
        else:
            return '{}s'.format(int(s[0]))

    return {
        'years': int(years()[0]),
        'days': int(days()[0]),
        'hours': int(hours()[0]),
        'minutes': int(minutes()[0]),
        'seconds': int(seconds()),
        'default': totalDuration(),
        'short': shortDuration()
    }[interval]


def get_articles(max_length=72, **kwargs):
    kwargs = {k: [v] if type(v) is str else v for k, v in kwargs.items()}
    kwargs_hash = 'articles_' + str({k.lower(): [i.lower() for i in sorted(v)] for k, v in kwargs.items()})
    kwargs_hash = ''.join([i if i.isalnum() else '_' for i in kwargs_hash])
    articles = cache.get(kwargs_hash)

    if articles is None:
        conditions = Q()
        special_filters = kwargs['special'] if 'special' in kwargs else None
        exclude_sidebar = True
        for field, condition_lst in kwargs.items():
            sub_conditions = Q()
            for condition in condition_lst:
                if field.lower() == "special":
                    if condition.lower() == 'free-only':
                        sub_conditions &= Q(Q(has_full_text=True) | Q(publisher__paywall='N'))
                    elif condition.lower() == "sidebar":
                        sub_conditions &= Q(categories__icontains='SIDEBAR')
                        exclude_sidebar = False
                else:
                    sub_conditions |= Q(**{f'{field}__icontains': condition})
                    exclude_sidebar = False
            try:
                test_condition = Article.objects.filter(sub_conditions)
            except:
                test_condition = []
            if len(test_condition) > 0:
                conditions &= sub_conditions
        articles = Article.objects.filter(conditions).order_by('min_article_relevance')
        if exclude_sidebar:
            articles = articles.exclude(categories__icontains="SIDEBAR")
        if max_length is not None and len(articles) > max_length:
            articles = articles[:max_length]
        cache.set(kwargs_hash, articles, 60 * 60 * 48)
        print(f'Got {kwargs_hash} from database and cached it')
    return articles



def homeView(request):

    # If fallback articcle view is needed
    if 'article' in request.GET:
        # if user is not autheticated
        if request.user.is_authenticated is False:
            return LoginView(request)
        return render(request, 'fallbackArticle.html', {'article': get_article_data(int(request.GET['article']))})


    # Get Homepage
    upToDate = cache.get('upToDate')
    articles = get_articles(**request.GET)
    sidebar = get_articles(special='sidebar')
    lastRefreshed = cache.get('lastRefreshed')

    selected_page = 'frontpage'
    if 'publisher__name' in request.GET:
        if 'financial times' in request.GET['publisher__name']:
            selected_page = 'financial times'
        elif 'bloomberg' in request.GET['publisher__name']:
            selected_page = 'bloomberg'
    elif 'categories' in request.GET:
        if 'fund' in request.GET['categories']:
            selected_page = 'funds'
    elif 'special' in request.GET:
        if 'free-only' in request.GET['special']:
            selected_page = 'free-only'


    if upToDate is not True:

        now = datetime.datetime.now()
        if now.hour >= 0 and now.hour < 5:
            print("Don't update articles between 0:00-4:59am to avoid forceful shutdown of container during server updates.")
        else:
            print('News are being refreshed now')
            update_feeds()


    return render(request, 'home.html', {
        'articles': articles,
        'sidebar': sidebar,
        'lastRefreshed': 'Never' if lastRefreshed is None else getDuration(lastRefreshed, datetime.datetime.now(), 'short'),
        'page': selected_page
        })