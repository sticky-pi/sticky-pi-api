FROM python:3.7-alpine

WORKDIR /code

# this is really ugly it's here because we need gcc etc to install uwsgi :-(
RUN set -e; \
	apk add --no-cache --virtual .build-deps \
		gcc \
		libc-dev \
		git \
		musl-dev linux-headers  build-base libjpeg-turbo-dev  libpng-dev openblas-dev tiff-dev \
		linux-headers \
		gettext libintl;


RUN pip install git+https://github.com/sticky-pi/sticky-pi-ml@develop#egg=sticky_pi_ml&subdirectory=src

# Set the current directory to /app
WORKDIR /app
# Copy the current directory contents into the container at /app
COPY . /app

CMD ["universal_insect_detector.py", "predict", "-v"]
