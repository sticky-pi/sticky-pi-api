# The API for the [Sticky Pi project](https://sticky-pi.github.io)

`main` branch:
[![readthedocs](https://readthedocs.org/projects/sticky_pi_api/badge/?version=latest)](https://sticky-pi-api.readthedocs.io/en/main/)
[![Travis](https://travis-ci.org/sticky-pi/sticky-pi-api.svg?branch=main)](https://travis-ci.org/sticky-pi/sticky-pi-ap)
[![codecov](https://codecov.io/gh/sticky-pi/sticky-pi-api/branch/main/graph/badge.svg)](https://codecov.io/gh/sticky-pi/sticky-pi-api/branch/main)

`develop` branch:
[![readthedocs](https://readthedocs.org/projects/sticky_pi_api/badge/?version=develop)](https://sticky-pi-api.readthedocs.io/en/develop/)
[![Travis](https://travis-ci.org/sticky-pi/sticky-pi-api.svg?branch=develop)](https://travis-ci.org/sticky-pi/sticky-pi-ap)
[![codecov](https://codecov.io/gh/sticky-pi/sticky-pi-api/branch/develop/graph/badge.svg)](https://codecov.io/gh/sticky-pi/sticky-pi-api/branch/develop)


--------------------------------
## Project organisation:

* `src` a Python package (`sticky_pi_api`) that defines the API and its client. 
Complete documentation of the [client](https://sticky-pi.github.io/client) and 
the [api](https://sticky-pi.github.io/api) is available on our website.


* `server` a docker-based server, deployed using `docker-compose`. Complete documentation [here](https://sticky-pi.github.io/server). Contains the following services:
  * `db` the database (MySQL)
  * `api` a flask server that instantiates our API and routes entry points
  * `rshiny` a webtool to visualise the data
  * `s3` an (optional) s3 server to store and serve resources such as images (can set a remote S3 server instead)
  * `nginx` an server to route trafic, set subdomains, etc


