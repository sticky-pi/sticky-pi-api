from sticky_pi_api._version import __version__
import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sticky_pi_api.utils import datetime_to_string
from sqlalchemy import Integer, DateTime, String

Base = declarative_base()

class DescribedColumn(Column):
    def __init__(self,  col_type, description="", *args, **kwargs):
        super().__init__(col_type, *args, **kwargs)
        self._description = description

# A base class to add our own customisation to Base, using mixin
class BaseCustomisations(Base):
    # __table__ = None
    __abstract__ = True
    datetime_created = Column(DateTime, nullable=False)
    api_version = Column(String(8), default="1.0.0", nullable=True)
    api_user = Column(String(32), nullable=True)

    def __init__(self, api_user=None, **kwargs):
        kwargs['datetime_created'] = datetime.datetime.now()


        kwargs['api_user'] = api_user
        kwargs['api_version'] = __version__

        super().__init__(**kwargs)

    def to_dict(self):
        out = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime.datetime):
                value = datetime_to_string(value)
            out[column.name] = value
        return out

    @classmethod
    def column_names(cls):
        return cls.__table__.columns.keys()



