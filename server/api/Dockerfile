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


# fixme remove (debug)
# these ca explicit dependencies of `sticky_pi_api[remote_api]`
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install  ipython


#fixme  for now,  use local package instead of dl from github everytime
# a src is a local snapshot of the package
# e,g, rsync -a ../../src/ src
COPY src /tmp/sticky_pi_api
RUN pip uninstall sticky_pi_api -y
RUN pip install -e /tmp/sticky_pi_api[remote_api,test]

# when stable:
#RUN pip install git+https://github.com/sticky-pi/sticky-pi-api@main#egg=sticky_pi_api&subdirectory=src

# Set the current directory to /app 
WORKDIR /app
# Copy the current directory contents into the container at /app
COPY . /app

# debug:
#ENV FLASK_APP app.py
#ENV FLASK_RUN_HOST 0.0.0.0
#ENV FLASK_ENV development
#ENTRYPOINT ["flask", "run"]

# production
CMD ["uwsgi", "--ini", "uwsgi.ini"]
