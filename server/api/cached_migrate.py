"""
A draft script to make performe migration even.
To be adapted

"""
import logging
from sticky_pi_api.configuration import RemoteAPIConf
import sqlalchemy
from sqlalchemy import Column
from sqlalchemy import Integer, DateTime, String, BLOB, Boolean


log_lev = logging.INFO
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=log_lev)
conf = RemoteAPIConf()

engine_url = "mysql+pymysql://%s:%s@%s/%s?charset=utf8mb4" % (conf.MYSQL_USER,
                                                              conf.MYSQL_PASSWORD,
                                                              conf.MYSQL_HOST,
                                                              conf.MYSQL_DATABASE
                                                              )
engine = sqlalchemy.create_engine(engine_url)

engine.execute('DELETE FROM  tiled_tuboids')
engine.execute('DELETE FROM  tuboid_series')


def add_column(engine, table_name):
    col = Column('cached_repr', BLOB(16000000), nullable=True)  # mediumtext
    c_name = col.compile(dialect=engine.dialect)
    c_type = col.type.compile(engine.dialect)
    engine.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table_name, c_name, c_type))
    col = Column('cached_expire_datetime', DateTime, nullable=True)  # mediumtext
    c_name = col.compile(dialect=engine.dialect)
    c_type = col.type.compile(engine.dialect)
    engine.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table_name, c_name, c_type))


engine_url = "mysql+pymysql://%s:%s@%s/%s?charset=utf8mb4" % (conf.MYSQL_USER,
                                                              conf.MYSQL_PASSWORD,
                                                              conf.MYSQL_HOST,
                                                              conf.MYSQL_DATABASE
                                                              )
engine = sqlalchemy.create_engine(engine_url)

q=engine.execute("ALTER TABLE images ADD INDEX `image_id` (`device`,`datetime`)")

# col = Column('can_write', Boolean, nullable=False, default=True)  # mediumtext
# c_name = col.compile(dialect=engine.dialect)
# c_type = col.type.compile(engine.dialect)
engine.execute('DELETE FROM  tiled_tuboids')
engine.execute('DELETE FROM  tuboid_series')

#
for tb in ['images', 'itc_labels', 'tiled_tuboids', 'tuboid_series', 'uid_annotations', 'users']:
    try:
        engine.execute('ALTER TABLE %s DROP COLUMN cached_repr' % tb)
        engine.execute('ALTER TABLE %s DROP COLUMN cached_expire_datetime' % tb)
    except sqlalchemy.exc.OperationalError as e:
        print(e)
        print("Error skipped")


