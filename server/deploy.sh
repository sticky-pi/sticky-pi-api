#!/bin/bash

set -e

if [ $# -eq 0 ]
  then
    echo "No arguments supplied. Expect a env file"
    exit 1
fi

# fixme rm this line
rsync -a ../src/ api/src

case "$1" in
        devel)
            export EXTRA_ENV=.devel.env
            ;;
       prod)
             export EXTRA_ENV=.prod.env
            ;;
       prod-init)
           export EXTRA_ENV=.prod.env
           export $(grep -v '^#' .env | xargs)
           export $(grep -v '^#' .prod.env | xargs)
           bash .init-letsencrypt.sh
           echo 'Certificates initialised. now run "deploy.sh prod"'
           exit 0
           ;;
        *)
            echo "Wrong action: $1"
            exit 1
esac

export $(grep -v '^#' ${EXTRA_ENV} | xargs)
docker-compose  down --remove-orphans  -v
# docker-compose config
docker-compose up --remove-orphans --build --force-recreate -d
