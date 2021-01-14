import logging
from sticky_pi_api.configuration import RemoteAPIConf
import sqlalchemy
from sqlalchemy import Column
from sqlalchemy import Integer, DateTime, String, Text


log_lev = logging.INFO
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=log_lev)


conf = RemoteAPIConf()


def add_column(engine, table_name):
    col = Column('cached_json_repr', Text(16000000), nullable=True)  # mediumtext
    c_name = col.compile(dialect=engine.dialect)
    c_type = col.type.compile(engine.dialect)
    engine.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table_name, c_name, c_type))
    col = Column('cached_json_expire_datetime', DateTime, nullable=True)  # mediumtext
    c_name = col.compile(dialect=engine.dialect)
    c_type = col.type.compile(engine.dialect)
    engine.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table_name, c_name, c_type))


engine_url = "mysql+pymysql://%s:%s@%s/%s?charset=utf8mb4" % (conf.MYSQL_USER,
                                                              conf.MYSQL_PASSWORD,
                                                              conf.MYSQL_HOST,
                                                              conf.MYSQL_DATABASE
                                                              )
eng = sqlalchemy.create_engine(engine_url)

for tb in ['images', 'itc_labels', 'tiled_tuboids', 'tuboid_series', 'uid_annotations', 'users']:
    try:
        add_column(eng, tb)
    except sqlalchemy.exc.OperationalError as e:
        print(e)
        print("Error skipped")

