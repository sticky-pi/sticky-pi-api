```
rsync -a ../../src/ src && 
        docker-compose  down --remove-orphans  -v  && 
        docker-compose up --remove-orphans --build --force-recreate -d 
```

## Connect to db

```
docker exec -it  spi_db sh
mysql -u $MYSQL_USER -p  $MYSQL_DATABASE
```

# debugging 
```python
import pymysql
connection = pymysql.connect(host='db',
                             user='sticky-pi',
                             password='ei3yqiudhbnw78rfgh',
                             db='sticky-pi') 
with connection.cursor() as cursor:
    # Create a new record
    sql = "CREATE TABLE tmp ( id INT );"
    cursor.execute(sql)
connection.commit()

with connection.cursor() as cursor:
    # Create a new record
    sql = "SHOW TABLES;"
    cursor.execute(sql)
connection.commit()
cursor.fetchall()
```

```python
import sqlalchemy
from sticky_pi_api.configuration import RemoteAPIConf
c = RemoteAPIConf()

#mysql+pymysql://<username>:<password>@<host>/<dbname>[?<options>]
engine_url = "mysql+pymysql://%s:%s@%s/%s?charset=utf8mb4" % (c.MYSQL_USER,
                                                                  c.MYSQL_PASSWORD,
                                                               c.MYSQL_HOST,
                                                                c.MYSQL_DATABASE
                                                                  )
e = sqlalchemy.create_engine(engine_url)
e.begin()

```

to read: https://www.freecodecamp.org/news/end-to-end-api-testing-with-docker/

# run prototype:
```
rsync -a ../src/ api/src &&  docker-compose  down --remove-orphans  -v &&  export EXTRA_ENV=.devel.env && docker-compose up --remove-orphans --build --force-recreate -d
```
