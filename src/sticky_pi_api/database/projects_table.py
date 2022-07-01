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
    owner = DescribedColumn(String(2048), index=True, nullable=True)


    def __init__(self, info, api_user_id=None):
        info['api_user_id'] = api_user_id
        super().__init__(**info)





