import logging
import time
from sqlalchemy import Integer, Boolean, String, UniqueConstraint
from sqlalchemy.orm import relationship
from itsdangerous import URLSafeTimedSerializer as Serializer
from passlib.apps import custom_app_context as pwd_context
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class Projects(BaseCustomisations):
    __tablename__ = 'projects'
    # two users may have the same email? Also, email can be null
    # __table_args__ = (UniqueConstraint('username'), )
    # __table_args__ = (UniqueConstraint('username') , UniqueConstraint('email'))


    project_permissions = relationship("ProjectPermissions",
                                   back_populates="parent_project",
                                   cascade="all, delete",
                                   passive_deletes=True
                                   )



    id = DescribedColumn(Integer, primary_key=True)
    name = DescribedColumn(String(32), index=True, nullable=False)
    description = DescribedColumn(String(20), index=True, nullable=True)
    notes = DescribedColumn(String(2048), index=True, nullable=True)

    @staticmethod
    def default_series_fields(sqlite=False):
        if sqlite:
            ai = "AUTOINCREMENT"
            i = "INTEGER"
        else:
            ai = "AUTO_INCREMENT"
            i = "INT"

        out = (f"id {i} PRIMARY KEY {ai} NOT NULL  ",
                "device CHAR(8) NOT NULL ",
                "start_datetime DATETIME NOT NULL ",
                "end_datetime DATETIME NOT NULL ",
               "UNIQUE(device, start_datetime, end_datetime)")

        out = f'({",".join(out)})'
        return out
    def series_table_name(self):
        return f"project_series_{self.id}"

    def create_table_mysql_statement(self, sqlite=False):
        return f"CREATE TABLE {self.series_table_name()} {self.default_series_fields(sqlite)}"
    def __init__(self, api_user_id=None, **kwargs):
        info = kwargs
        info['api_user_id'] = api_user_id
        super().__init__(**info)





