FROM nginx

# Remove the default nginx.conf-template
RUN rm /etc/nginx/conf.d/default.conf

# Replace with our own nginx.conf-template
COPY nginx.conf-template /tmp/

ARG API_PORT
ARG ROOT_DOMAIN_NAME
ENV API_PORT=$API_PORT
ENV ROOT_DOMAIN_NAME=$ROOT_DOMAIN_NAME

# production
RUN export API_PORT; envsubst '\$API_PORT \$ROOT_DOMAIN_NAME' < /tmp/nginx.conf-template > /etc/nginx/conf.d/nginx.conf
RUN rm /tmp/nginx.conf-template

