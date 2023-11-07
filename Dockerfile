# syntax=docker/dockerfile:1

# Section 1- Base Image
FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpcre3 mime-support nano lsb-release curl gpg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list \
    && apt-get update \
    && apt-get install -y redis

COPY requirements.txt /feed_aggregator/requirements.txt
RUN pip3 install --no-cache-dir -r /feed_aggregator/requirements.txt \
    && useradd -U app_user \
    && install -d -m 0755 -o app_user -g app_user /feed_aggregator

USER app_user:app_user

COPY --chown=app_user:app_user / /feed_aggregator/

WORKDIR /feed_aggregator

RUN chown -R app_user:app_user /feed_aggregator
RUN chmod 755 /feed_aggregator

LABEL org.opencontainers.image.title="News Plattform"
LABEL org.opencontainers.image.description="News Aggregator - Aggregates news articles from several RSS feeds, fetches full-text if possible, sorts them by relevance (based on user settings), and display on distraction-free homepage."
LABEL org.opencontainers.image.authors="https://github.com/vanalmsick"
LABEL org.opencontainers.image.url="https://github.com/vanalmsick/news_platform"
LABEL org.opencontainers.image.documentation="https://vanalmsick.github.io/news_platform/"
LABEL org.opencontainers.image.source="https://hub.docker.com/r/vanalmsick/news_platform"
LABEL org.opencontainers.image.licenses="MIT"

EXPOSE 80
VOLUME /feed_aggregator/data
HEALTHCHECK --interval=20m --timeout=60s --retries=3 \
    CMD echo Successful Docker Container Healthcheck && curl --max-time 30 --connect-timeout 30 --silent --output /dev/null --show-error --fail http://localhost:80/ || exit 1

CMD ["supervisord", "-c", "./supervisord.conf"]
