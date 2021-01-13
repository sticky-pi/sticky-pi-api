from sticky_pi_api._version import __version__
import datetime
import json
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sticky_pi_api.utils import datetime_to_string, json_io_converter, json_out_parser
from sqlalchemy import Integer, DateTime, String, Text

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
    #
    cached_json_repr = Column(Text(16000000), nullable=True) # mediumtext
    cached_json_expire_datetime = Column(DateTime, nullable=True) # mediumtext

    def __init__(self, api_user=None, **kwargs):
        kwargs['datetime_created'] = datetime.datetime.now()
        kwargs['api_user'] = api_user
        kwargs['api_version'] = __version__

        super().__init__(**kwargs)

    def to_dict(self):
        out = {}
        for column in self.__table__.columns:
            if column.name.startswith('cached_'):
                continue
            value = getattr(self, column.name)
            if isinstance(value, datetime.datetime):
                value = datetime_to_string(value)
            out[column.name] = value
        return out


    def set_cached_repr(self, extra_fields=None):
        now = datetime.datetime.now()
        expiration = now + self._cache_expiration
        self.cached_json_expire_datetime = expiration
        content = self.to_dict()
        content.update(extra_fields)
        self.cached_json_repr = json.dumps(content, default=json_io_converter)
        return content

    def get_cached_repr(self):
        now = datetime.datetime.now()
        if self.cached_json_expire_datetime is None or now > self.cached_json_expire_datetime:
            return None
        else:
            return json.loads(self.cached_json_repr, object_hook=json_out_parser)

    @classmethod
    def column_names(cls):
        return cls.__table__.columns.keys()



