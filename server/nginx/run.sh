#!/bin/bash

if [ ${TESTING} = "TRUE" ]
then
  TEMPLATE_FILE='nginx_testing.conf-template'
else
  TEMPLATE_FILE='nginx.conf-template'
fi

export API_PORT;
export WEBAPP_PORT;
export S3_PORT;

envsubst '\$API_PORT \$WEBAPP_PORT \$S3_PORT \$ROOT_DOMAIN_NAME' < ${TEMPLATE_FILE} > /etc/nginx/conf.d/nginx.conf ;
echo $(echo "NGINX IN TESTING MODE");
nginx -g "daemon off;"

#exec /docker-entrypoint.sh $@