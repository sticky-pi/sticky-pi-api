FROM python:3.7-alpine

WORKDIR /code

COPY requirements.txt requirements.txt
# this is really ugly it's here because we need gcc etc to install uwsgi :-(
RUN set -e; \
	apk add --no-cache --virtual .build-deps \
		gcc \
		libc-dev \
		linux-headers \
	; \
	pip install -r requirements.txt; \
	apk del .build-deps;

# Set the current directory to /app 
WORKDIR /app

# Copy the current directory contents into the container at /app 
COPY . /app

CMD ["uwsgi", "--ini", "uwsgi.ini"]