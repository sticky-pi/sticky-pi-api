#!/bin/bash

set -e

if [ $# -eq 0 ]
  then
    echo "No arguments supplied. Expect a env file"
    exit 1
fi

# fixme rm this line
rsync -a ../src/ api/src
rsync -a ../src/ ml/src_api

# this line should also go when packages are installed from github
#rsync -a ../../sticky-pi-ml-git/src/ ml/src


case "$1" in
       s3test)
            docker-compose down --remove-orphans -v
            docker-compose -f docker-compose.yml  -f docker-compose.devel.yml up --remove-orphans --build --force-recreate   spi_s3_tests
            ;;
       test)
            docker-compose  down --remove-orphans  -v
            docker-compose  -f docker-compose.yml  -f docker-compose.devel.yml up --remove-orphans --build --force-recreate   spi_api_tests
            ;;
       devel)
            docker-compose  down --remove-orphans  -v
            docker-compose  -f docker-compose.yml  -f docker-compose.devel.yml up --remove-orphans --build --force-recreate   -d
            ;;
       prod)
            docker-compose  down --remove-orphans  -v
            docker-compose  -f docker-compose.yml  -f docker-compose.prod.yml pull
            docker-compose  -f docker-compose.yml  -f docker-compose.prod.yml up --remove-orphans  --force-recreate -d
            ;;
       prod-init)
           docker-compose  down --remove-orphans  -v
           docker-compose  -f docker-compose.yml  -f docker-compose.prod.yml pull
           export $(grep -v '^#' .env | xargs)
           export $(grep -v '^#' .secret.env | xargs)
           bash .init-letsencrypt.sh
           echo 'Certificates initialised. now run "deploy.sh prod"'
           ;;
      mysql-prompt)
          source ./.env
          source ./.secret.env
          docker exec -it spi_db mysql --password=$MYSQL_PASSWORD -u $MYSQL_USER $MYSQL_DATABASE
          ;;
      mysql-backup)
          source ./.env
          source ./.secret.env
          OUTPUT_BACKUP_FILE=spi_db.dump.$(date +%F).sql.gz
          echo "Making a database backup: $OUTPUT_BACKUP_FILE. This could take a while..."
          docker exec -it spi_db mysqldump --password=$MYSQL_PASSWORD -u $MYSQL_USER $MYSQL_DATABASE --single-transaction | gzip -c > $OUTPUT_BACKUP_FILE &&\
          echo "Success! Now COPY this file to a safe location"
          ;;
       *)
          echo "Wrong action: $1"
          exit 1
esac

