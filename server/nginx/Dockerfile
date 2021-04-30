FROM nginx

# Remove the default nginx.conf-template
RUN rm /etc/nginx/conf.d/default.conf



ARG API_PORT
ARG WEBAPP_PORT
ARG ROOT_DOMAIN_NAME
# TODO adapt this
ENV API_PORT=$API_PORT
ENV WEBAPP_PORT=$WEBAPP_PORT
ENV ROOT_DOMAIN_NAME=$ROOT_DOMAIN_NAME

ARG TESTING
ENV TESTING=$TESTING

# Replace with our own nginx.conf-template
ENV CONFIG_FILE=nginx.conf-template
ENV TEST_CONFIG_FILE=nginx_testing.conf-template


COPY ${CONFIG_FILE} /tmp/nginx.conf-template
COPY ${TEST_CONFIG_FILE} /tmp/nginx_testing.conf-template

# testing
# NOTE: S3_PORT added to this
RUN if [ ${TESTING} = "TRUE" ] ; then export API_PORT; export WEBAPP_PORT; export S3_PORT; envsubst '\$API_PORT \$WEBAPP_PORT \$S3_PORT \$ROOT_DOMAIN_NAME' < /tmp/nginx_testing.conf-template > /etc/nginx/conf.d/nginx.conf ; echo $(echo "NGINX IN TESTING MODE"); fi
# production
#RUN export API_PORT; envsubst '\$API_PORT \$ROOT_DOMAIN_NAME' < /tmp/nginx.conf-template > /etc/nginx/conf.d/nginx.conf
RUN if [ ${TESTING} != "TRUE" ] ; then export API_PORT; export WEBAPP_PORT; envsubst '\$API_PORT \$WEBAPP_PORT \$ROOT_DOMAIN_NAME' < /tmp/nginx.conf-template > /etc/nginx/conf.d/nginx.conf ; echo $(echo "NGINX IN PRODUCTION MODE"); fi

RUN  echo $(cat  /etc/nginx/conf.d/nginx.conf)

RUN rm /tmp/nginx.conf-template

