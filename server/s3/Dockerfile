FROM localstack/localstack
COPY run.sh /run.sh
# RUN mkdir /docker-entrypoint-initaws.d
# COPY create_buckets.sh /docker-entrypoint-initaws.d
ENTRYPOINT ["sh", "/run.sh"]
