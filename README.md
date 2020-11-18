# The API for the [Sticky Pi project](https://sticky-pi.github.io)

|build-status| |docs| |coverage|

.. |build-status| image:: https://circleci.com/gh/readthedocs/readthedocs.org.svg?style=svg
    :alt: build status
    :target: https://circleci.com/gh/readthedocs/readthedocs.org

.. |docs| image:: https://readthedocs.org/projects/sticky_pi_api/badge/?version=latest
    :alt: Documentation Status
    :scale: 100%
    :target: https://sticky_pi_api.readthedocs.io/en/latest/?badge=latest

.. |coverage| image:: https://codecov.io/gh/readthedocs/readthedocs.org/branch/master/graph/badge.svg
    :alt: Test coverage
    :scale: 100%
    :target: https://codecov.io/gh/readthedocs/readthedocs.org


* `src` a Python package (`sticky_pi_api`) that defines the API and its client. 
Complete documentation of the [client](https://sticky-pi.github.io/client) and 
the [api][client](https://sticky-pi.github.io/api) is available on our website.


* `server` a docker-based server, deployed using `docker-compose`. Complete doumentation [here](https://sticky-pi.github.io/server). Contains the following services:
  * `db` the database (MySQL)
  * `api` a flask server that instantiates our API and routes entry points
  * `rshiny` a webtool to visualise the data
  * `s3` an (optional) s3 server to store and serve resources such as images (can set a remote S3 server instead)
  * `nginx` an server to route trafic, set subdomains, etc


