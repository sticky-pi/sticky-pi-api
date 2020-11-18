import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sticky_pi_api.utils import datetime_to_string

Base = declarative_base()


# A base class to add our own customisation to Base, using mixin
class BaseCustomisations(object):
    __table__ = None

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



class DescribedColumn(Column):
    def __init__(self,  col_type, description="", *args, **kwargs):
        super().__init__(col_type, *args, **kwargs)
        self._description = description


