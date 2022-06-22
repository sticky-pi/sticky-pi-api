FROM python:3.8-alpine

WORKDIR /code


RUN echo "https://dl-3.alpinelinux.org/alpine/v3.12/main" >> /etc/apk/repositories
RUN echo "https://dl-3.alpinelinux.org/alpine/v3.12/community" >> /etc/apk/repositories

# this is really ugly it's here because we need gcc etc to install uwsgi :-(
RUN set -e; \
	apk add --no-cache --virtual .build-deps \
		gcc \
		libc-dev \
		git \
		musl-dev linux-headers  build-base libjpeg-turbo-dev  libpng-dev openblas-dev tiff-dev \
		linux-headers \
		gettext libintl \
		python3 py3-pip gcompat libgcc \
		python3-dev  mariadb-dev \
        g++  rust cargo

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install  ipython


# fixme remove (debug)
# these ca explicit dependencies of `sticky_pi_api[remote_api]`
RUN pip install pandas requests python-dotenv pillow psutil tqdm joblib \
            sqlalchemy imread typeguard passlib itsdangerous decorate_all_methods \
            boto3 pymysql  PyMySQL  Flask-HTTPAuth  retry nose  pytest  pytest-cov  codecov  coverage \
            mysqlclient orjson

# RUN apk update \
#     && apk add --virtual build-deps gcc python3-dev musl-dev \
#     && apk add --no-cache mariadb-dev
# RUN pip install
#
# RUN apk del build-deps

# RUN apk add --no-cache gcc g++ musl-dev rust cargo



#fixme  for now,  use local package instead of dl from github everytime
# a src is a local snapshot of the package
# e,g, rsync -a ../../src/ src
COPY src /tmp/sticky_pi_api
RUN pip uninstall sticky_pi_api -y
RUN pip install -e /tmp/sticky_pi_api[remote_api,test]

# when stable:
#RUN pip install git+https://github.com/sticky-pi/sticky-pi-api@main#egg=sticky_pi_api&subdirectory=src[remote_api,test]

# Set the current directory to /app 
WORKDIR /app
# Copy the current directory contents into the container at /app
COPY . /app

CMD ["sh", "/app/run.sh"]

#ARG API_PORT
#ENV API_PORT=$API_PORT
#
## production
#RUN export API_PORT; envsubst '\$API_PORT' < uwsgi.ini-template > uwsgi.ini
#CMD ["uwsgi", "--ini", "uwsgi.ini"]
