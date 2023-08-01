# syntax=docker/dockerfile:1

# Section 1- Base Image
FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl libpcre3 mime-support nano \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /feed_aggregator/requirements.txt
RUN pip3 install --no-cache-dir -r /feed_aggregator/requirements.txt \
  && useradd -U app_user \
  && install -d -m 0755 -o app_user -g app_user /feed_aggregator

WORKDIR /feed_aggregator
USER app_user:app_user

COPY --chown=app_user:app_user / /feed_aggregator/
#RUN chmod +x /src/*.sh

LABEL org.opencontainers.image.title="vA News Plattform"
LABEL version="0.0.1"

EXPOSE 80
VOLUME /data
HEALTHCHECK --interval=20m --timeout=60s --retries=3 \
  CMD echo Successful Docker Container Healthcheck && curl --max-time 30 --connect-timeout 30 --silent --output /dev/null --show-error --fail http://localhost:80/ || exit 1

CMD [ "python3", "manage.py", "runserver", "0.0.0.0:80"]
#, "--cert-file", "data/cert.pem", "--key-file", "data/key.pem"