import time
import datetime
from sqlalchemy import Integer, Boolean, String, DateTime, UniqueConstraint
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class Users(BaseCustomisations):
    __tablename__ = 'users'
    __table_args__ = (UniqueConstraint('username'), UniqueConstraint('email'))

    id = DescribedColumn(Integer, primary_key=True)
    username = DescribedColumn(String(32), index=True, nullable=False)
    email = DescribedColumn(String(64), index=True, nullable=True)
    password_hash = DescribedColumn(String(128), nullable=False)
    is_admin = DescribedColumn(Boolean, default=False)
    can_write = DescribedColumn(Boolean, default=True)

    def __init__(self, password, api_user=None, **kwargs):
        my_dict = kwargs
        my_dict['password_hash'] = pwd_context.encrypt(password)
        my_dict['api_user'] = api_user
        super().__init__(**my_dict)

    def verify_password(self, password):
        out = pwd_context.verify(password, self.password_hash)
        return out

    def generate_auth_token(self, api_secret_key, expiration=3600 * 24):
        now = int(time.time())
        exp_timestamp = now + expiration
        s = Serializer(api_secret_key, expires_in=expiration)
        token = s.dumps({'id': self.id})
        return {'token': token.decode('ascii'), 'expiration': exp_timestamp}


