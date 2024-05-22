# syntax=docker/dockerfile:1

# Section 1- Base Image
FROM python:3.11.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpcre3 mime-support nano lsb-release curl gpg python3-dev libpq-dev postgresql-dev gcc \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list \
    && apt-get update \
    && apt-get install -y redis

COPY requirements.txt /news_platform/requirements.txt
RUN pip3 install --no-cache-dir -r /news_platform/requirements.txt \
    && useradd -U app_user \
    && install -d -m 0755 -o app_user -g app_user /news_platform

USER app_user:app_user

COPY --chown=app_user:app_user / /news_platform/

WORKDIR /news_platform

RUN chown -R app_user:app_user /news_platform
RUN chmod 755 /news_platform

LABEL org.opencontainers.image.title="News Plattform"
LABEL org.opencontainers.image.description="News Aggregator - Aggregates news articles from several RSS feeds, fetches full-text if possible, sorts them by relevance (based on user settings), and display on distraction-free homepage."
LABEL org.opencontainers.image.authors="https://github.com/vanalmsick"
LABEL org.opencontainers.image.url="https://github.com/vanalmsick/news_platform"
LABEL org.opencontainers.image.documentation="https://vanalmsick.github.io/news_platform/"
LABEL org.opencontainers.image.source="https://hub.docker.com/r/vanalmsick/news_platform"
LABEL org.opencontainers.image.licenses="MIT"

# Main website
EXPOSE 80
# Celery Flower - for dev
EXPOSE 5555
# Supervisord - for dev
EXPOSE 9001
# Permanent storage for databse and config files
VOLUME /news_platform/data

HEALTHCHECK --interval=20m --timeout=60s --retries=3 \
    CMD echo Successful Docker Container Healthcheck && curl --max-time 30 --connect-timeout 30 --silent --output /dev/null --show-error --fail http://localhost:80/ || exit 1

CMD ["supervisord", "-c", "./supervisord.conf"]
