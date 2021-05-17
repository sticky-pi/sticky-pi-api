#!/bin/bash

export API_PORT; envsubst '\$API_PORT' < uwsgi.ini-template > uwsgi.ini
uwsgi --ini uwsgi.ini
