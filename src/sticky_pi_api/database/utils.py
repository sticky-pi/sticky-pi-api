from sticky_pi_api._version import __version__
import datetime
import pickle
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sticky_pi_api.utils import datetime_to_string, json_io_converter, json_out_parser
from sqlalchemy import Integer, DateTime, String, Text, BLOB

Base = declarative_base()

class DescribedColumn(Column):
    def __init__(self,  col_type, description="", *args, **kwargs):
        super().__init__(col_type, *args, **kwargs)
        self._description = description

# A base class to add our own customisation to Base, using mixin
class BaseCustomisations(Base):
    # __table__ = None
    __abstract__ = True

    _cache_expiration = datetime.timedelta(hours=6)

    datetime_created = Column(DateTime, nullable=False)

    api_version = Column(String(8), default="1.0.0", nullable=True)
    api_user = Column(String(32), nullable=True)


    def __init__(self, api_user=None, **kwargs):
        kwargs['datetime_created'] = datetime.datetime.now()
        kwargs['api_user'] = api_user
        kwargs['api_version'] = __version__
        # self._column_names = [column.name for column in self.__table__.columns]
        super().__init__(**kwargs)

    def to_dict(self):
        out = {}
        for c in self.__table__.columns:
            out[c.name] = getattr(self, c.name)
        return out

    @classmethod
    def column_names(cls):
        return cls.__table__.columns.keys()



