
define the `EXTRA_ENV` variable. It must be one of the local environment files:

* `.prod.env` -- for deployment
* `.devel.env` -- for local development
* `.testing.env` -- to run tests

e.g. deploy:

```
bash deploy.sh .devel.env
```