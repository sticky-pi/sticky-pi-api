FROM nginx

# Remove the default nginx.conf-template

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf-template .
COPY nginx_testing.conf-template .
COPY run.sh .
# testing
# NOTE: S3_PORT added to this
#RUN if [ ${TESTING} = "TRUE" ] ; then export API_PORT; export WEBAPP_PORT; export S3_PORT; envsubst '\$API_PORT \$WEBAPP_PORT \$S3_PORT \$ROOT_DOMAIN_NAME' < /tmp/nginx_testing.conf-template > /etc/nginx/conf.d/nginx.conf ; echo $(echo "NGINX IN TESTING MODE"); fi
# production
#RUN export API_PORT; envsubst '\$API_PORT \$ROOT_DOMAIN_NAME' < /tmp/nginx.conf-template > /etc/nginx/conf.d/nginx.conf
#RUN if [ ${TESTING} != "TRUE" ] ; then export API_PORT; export WEBAPP_PORT; envsubst '\$API_PORT \$WEBAPP_PORT \$ROOT_DOMAIN_NAME' < /tmp/nginx.conf-template > /etc/nginx/conf.d/nginx.conf ; echo $(echo "NGINX IN PRODUCTION MODE"); fi


#RUN rm /tmp/nginx.conf-template
ENTRYPOINT ["bash", "run.sh"]
#CMD ["nginx", "-g", "daemon off;"]