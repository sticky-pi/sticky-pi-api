#!/bin/bash

set -e

if [ $# -eq 0 ]
  then
    echo "No arguments supplied. Expect a env file"
    exit 1
fi

# fixme rm this line
rsync -a ../src/ api/src


docker-compose  down --remove-orphans  -v

case "$1" in
        test)
            docker-compose  -f docker-compose.yml  -f docker-compose.devel.yml up --remove-orphans --build --force-recreate   spi_api_tests
            ;;
        devel)
            docker-compose  -f docker-compose.yml  -f docker-compose.devel.yml up --remove-orphans --build --force-recreate   -d
            ;;
       prod)
            docker-compose  -f docker-compose.yml  -f docker-compose.prod.yml up --remove-orphans --build --force-recreate -d
            ;;
       prod-init)
           export $(grep -v '^#' .env | xargs)
           export $(grep -v '^#' .secret.env | xargs)
           bash .init-letsencrypt.sh
           echo 'Certificates initialised. now run "deploy.sh prod"'
           ;;
        *)
            echo "Wrong action: $1"
            exit 1
esac

