FROM python:3.7-alpine

WORKDIR /code

# this is really ugly it's here because we need gcc etc to install uwsgi :-(
RUN set -e; \
	apk add --no-cache --virtual .build-deps \
		gcc \
		libc-dev \
		git \
		musl-dev linux-headers  build-base libjpeg-turbo-dev  libpng-dev openblas-dev tiff-dev \
		linux-headers;


# add to a new line, so we can cache previouss command (does not rerun if requierements change)
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Set the current directory to /app 
WORKDIR /app

# Copy the current directory contents into the container at /app 
COPY . /app

CMD ["uwsgi", "--ini", "uwsgi.ini"]
#
#ENTRYPOINT ["flask", "run", "--with-threads"]