# The API for the [Sticky Pi project](https://sticky-pi.github.io)


* `client` a Python package (`sticky-pi`) to interact with the API. Complete doumentation [here](https://sticky-pi.github.io/client).

* `server` a docker-based server, deployed using `docker-compose`. Complete doumentation [here](https://sticky-pi.github.io/server). Contains the following services:
  * `db` the database (MySQL)
  * `api` a flask server that handles client requests
  * `rshiny` a webtool to visualise the data
  * `s3` an (optional) s3 server to store and serve resources such as images (can set a remote S3 server instead)
  * `nginx` an server to route trafic, set subdomains, etc


