import requests
from .models import DataSource, DataEntry
from django.core.cache import cache
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from django.db.models import F, Q, Max


def __get_quote_table(ticker, headers={'User-agent': 'Mozilla/5.0'}):
    """Scrape Market Data from Yahoo Finance"""

    site = "https://finance.yahoo.com/quote/" + ticker + "?p=" + ticker

    reponse = requests.get(site, headers=headers).text

    tables = pd.read_html(reponse)
    one_table = np.concatenate(tables, axis=0)
    data = {x: y for x,y in one_table}

    soup = BeautifulSoup(reponse, "lxml")
    items = soup.find(id="quote-market-notice").find_parent().find_all("fin-streamer")
    for i in items:
        if hasattr(i, 'data-field') and hasattr(i, 'value'):
            data[i['data-field']] = i['value']

    converted_data = {}
    for k, v in data.items():
        if type(v) is str:
            if v != '':
                d = v.split(' - ')
                for i, j in enumerate(d):
                    if j.replace(',','').replace('-','', 1).replace('.','', 1).isdigit():
                        d[i] = float(j.replace(',', ''))
                converted_data[k] = d[0] if len(d) == 1 else d
        else:
            converted_data[k] = v

    return converted_data



def scrape_market_data():
    """Get all data sources, scrape the data from the web, and update cached market data."""
    all_scources = DataSource.objects.all()
    latest_data = []

    for data_src in all_scources:
        summary_box = __get_quote_table(data_src.yfin_tck)
        obj = DataEntry(
            source=data_src,
            price=summary_box['regularMarketPrice'],
            change_today=summary_box['regularMarketChangePercent']*100,
            )
        obj.save()
        latest_data.append(obj.pk)

    latest_data = DataEntry.objects.filter(pk__in=latest_data).order_by('source__group__position', '-source__pinned', 'change_today')
    final_data = {}
    for i in latest_data:
        if i.source.group not in final_data:
            final_data[i.source.group] = []
        final_data[i.source.group].append(i)

    cache.set("latestMarketData", final_data, 60 * 60 * 12)

