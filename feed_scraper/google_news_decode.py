# -*- coding: utf-8 -*-
"""Decode encoded Google News entry URLs."""
import base64
import functools
import re

# Ref: https://stackoverflow.com/a/59023463/

_ENCODED_URL_PREFIX = "https://news.google.com/rss/articles/"
_ENCODED_URL_RE = re.compile(
    rf"^{re.escape(_ENCODED_URL_PREFIX)}(?P<encoded_url>[^?]+)"
)
_DECODED_URL_RE = re.compile(rb'^\x08\x13".+?(?P<primary_url>http[^\xd2]+)\xd2\x01')


@functools.lru_cache(2048)
def _decode_google_news_url(url: str) -> str:
    """Actually decodes Google News url"""
    match = _ENCODED_URL_RE.match(url)
    encoded_text = match.groupdict()["encoded_url"]  # type: ignore
    encoded_text += (  # Fix incorrect padding. Ref: https://stackoverflow.com/a/49459036/
        "==="
    )
    decoded_text = base64.urlsafe_b64decode(encoded_text)

    match = _DECODED_URL_RE.match(decoded_text)  # type: ignore
    primary_url = match.groupdict()["primary_url"]  # type: ignore
    primary_url = primary_url.decode()  # type: ignore
    return primary_url


def decode_google_news_url(
    url: str,
) -> str:  # Not cached because not all Google News URLs are encoded.
    """Return Google News entry URLs after decoding their encoding as applicable."""
    return _decode_google_news_url(url) if url.startswith(_ENCODED_URL_PREFIX) else url
