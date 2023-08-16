from django.shortcuts import render
from django.core.cache import cache
from feed_scraper.scraper import update_feeds
from articles.models import Article
from django.db.models import Q
import datetime
from .login import LoginForm
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



def homeView(request):

    upToDate = cache.get('upToDate')
    currentlyRefresing = cache.get('currentlyRefresing')

    if currentlyRefresing:
        print('Article refreshing in progress thus get latest cached')

        articles = cache.get('homepage')
        lastRefreshed = cache.get('lastRefreshed')

    else:

        articles = cache.get('homepage')
        lastRefreshed = cache.get('lastRefreshed')

        if articles is None or len(articles) == 0:
            print('Get articles not from cache but database')

            articles = Article.objects.all().exclude(main_genre='sport').exclude(min_article_relevance__isnull=True).order_by('min_article_relevance')[:64]
            cache.set('homepage', articles, 60 * 60 * 48)

        if upToDate is not True:

            print('News are being refreshed now')
            update_feeds()

    form = LoginForm()
    message = ''
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username='user',
                password=form.cleaned_data['password'],
            )
            if user is not None:
                message = 'Login successful!'
                login(request, user)
            else:
                message = 'Login failed!'



    return render(request, 'home.html', {
        'articles': articles,
        'lastRefreshed': 'Never' if lastRefreshed is None else getDuration(lastRefreshed, datetime.datetime.now(), 'short'),
        'loaading': currentlyRefresing,
        'form': form, 'message': message
        })