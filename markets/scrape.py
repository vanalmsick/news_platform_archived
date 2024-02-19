"""Data scraping for Market Data i.e. Stock/FX/Comm prices"""
import datetime
from io import StringIO

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache

from .models import DataEntry, DataSource


def __get_bonds(tickers, headers={"User-agent": "Mozilla/5.0"}):
    """Function to scrape rates market data form tradingeconomics.com"""
    site = "https://tradingeconomics.com/bonds"
    reponse = requests.get(site, headers=headers).text
    soup = BeautifulSoup(reponse, "lxml")

    span = soup.find("span", {"class": "market-negative-image"})
    while span is not None:
        new_tag = soup.new_tag("span")
        new_tag.string = "-"
        span.replace_with(new_tag)
        span = soup.find("span", {"class": "market-negative-image"})

    tables = pd.read_html(StringIO(str(soup)))
    data = tables[0].iloc[:, 1:].set_index("Major10Y").to_dict(orient="index")

    latest_data = []
    if len(tickers) > 0:
        for ticker in tickers:
            if ticker.ticker in data:
                data_yield = (
                    float(
                        "".join(
                            [
                                i
                                for i in data[ticker.ticker]["Yield"]
                                if i.isdigit() or i == "-" or i == "."
                            ]
                        )
                    )
                    if type(data[ticker.ticker]["Yield"]) is str
                    else data[ticker.ticker]["Yield"]
                )
                data_day = (
                    float(
                        "".join(
                            [
                                i
                                for i in data[ticker.ticker]["Day"]
                                if i.isdigit() or i == "-" or i == "."
                            ]
                        )
                    )
                    if type(data[ticker.ticker]["Day"]) is str
                    else data[ticker.ticker]["Day"]
                )
                obj = DataEntry(
                    source=ticker,
                    price=data_yield,
                    change_today=data_day * 100,
                )
                obj.save()
                latest_data.append(obj.pk)

    return latest_data


def __get_quote_table(ticker, headers={"User-agent": "Mozilla/5.0"}):
    """Scrape Market Data from Yahoo Finance"""

    site = "https://finance.yahoo.com/quote/" + ticker + "?p=" + ticker

    reponse = requests.get(site, headers=headers).text

    tables = pd.read_html(StringIO(reponse))
    one_table = np.concatenate(tables, axis=0)
    data = {x: y for x, y in one_table}

    soup = BeautifulSoup(reponse, "lxml")
    data["quote-market-notice"] = soup.find(id="quote-market-notice").text
    items = soup.find(id="quote-market-notice").find_parent().find_all("fin-streamer")
    for i in items:
        if hasattr(i, "data-field") and hasattr(i, "value"):
            data[i["data-field"]] = i["value"]

    converted_data = {}
    for k, v in data.items():
        if type(v) is str:
            if v != "":
                d = v.split(" - ")
                for i, j in enumerate(d):
                    if (
                        j.replace(",", "")
                        .replace("-", "", 1)
                        .replace(".", "", 1)
                        .isdigit()
                    ):
                        d[i] = float(j.replace(",", ""))
                converted_data[k] = d[0] if len(d) == 1 else d
        else:
            converted_data[k] = v

    return converted_data


def scrape_market_data():
    """Get all data sources, scrape the data from the web, and update cached market data."""

    print("Refreshing Market Data...")

    all_scources = DataSource.objects.exclude(data_source="yfin")
    latest_data = __get_bonds(all_scources)

    all_scources = DataSource.objects.filter(data_source="yfin")
    for data_src in all_scources:
        summary_box = __get_quote_table(data_src.ticker)
        obj = DataEntry(
            source=data_src,
            price=summary_box["regularMarketPrice"],
            change_today=summary_box["regularMarketChangePercent"] * 100,
            market_closed=(
                True if "close" in summary_box["quote-market-notice"].lower() else False
            ),
        )
        obj.save()
        latest_data.append(obj.pk)

    latest_data = DataEntry.objects.filter(pk__in=latest_data).order_by(
        "source__group__position", "-source__pinned", "change_today"
    )
    final_data = {}
    for i in latest_data:
        if i.source.group not in final_data:
            final_data[i.source.group] = []
        final_data[i.source.group].append(i)

    # delete market data older than 45 days
    DataEntry.objects.filter(
        ref_date_time__lte=settings.TIME_ZONE_OBJ.localize(
            datetime.datetime.now() - datetime.timedelta(days=45)
        )
    ).delete()

    print("Market Data was successfully refreshed.")

    cache.set("latestMarketData", final_data, 60 * 60 * 12)
