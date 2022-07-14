import logging
import time
import datetime
from sqlalchemy import Integer, Boolean, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from itsdangerous import URLSafeTimedSerializer as Serializer
from itsdangerous import SignatureExpired
from passlib.apps import custom_app_context as pwd_context
#
# from itsdangerous import TimestampSigner

from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class Users(BaseCustomisations):
    __tablename__ = 'users'
    # two users may have the same email? Also, email can be null
    __table_args__ = (UniqueConstraint('username'), )
    # __table_args__ = (UniqueConstraint('username') , UniqueConstraint('email'))



    project_permissions = relationship("ProjectPermissions",
                                   back_populates="parent_user",
                                   cascade="all, delete",
                                   passive_deletes=True
                                   )


    token_expiration = 3600 * 24

    id = DescribedColumn(Integer, primary_key=True)
    username = DescribedColumn(String(32), index=True, nullable=False)
    email = DescribedColumn(String(64), index=True, nullable=True)
    password_hash = DescribedColumn(String(128), nullable=False)
    is_admin = DescribedColumn(Boolean, default=False)
    can_write = DescribedColumn(Boolean, default=True)


    def __init__(self, password, api_user_id=None, **kwargs):
        my_dict = kwargs
        my_dict['password_hash'] = pwd_context.encrypt(password)
        my_dict['api_user_id'] = api_user_id
        super().__init__(**my_dict)

    def verify_password(self, password):
        out = pwd_context.verify(password, self.password_hash)
        return out


    def generate_auth_token(self, api_secret_key):
        now = int(time.time())
        exp_timestamp = now + self.token_expiration
        s = Serializer(api_secret_key)
        token = s.dumps({'id': self.id})
        return {'token': token, 'expiration': exp_timestamp}





