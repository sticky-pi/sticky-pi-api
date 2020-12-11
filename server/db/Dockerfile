FROM mysql/mysql-server:8.0

COPY scripts/* /docker-entrypoint-initdb.d/

# Install server
RUN yum install -y iproute \
  && yum clean all \
  && rm -rf /var/lib/{cache,log} /var/log/lastlog \
  && find /var/log -type f -delete

VOLUME /var/lib/mysql

EXPOSE 3306

CMD ["mysqld"]