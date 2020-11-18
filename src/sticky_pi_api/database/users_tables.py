
import datetime
from sqlalchemy import Integer, Boolean, String, DateTime, UniqueConstraint
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class Users(Base, BaseCustomisations):
    __tablename__ = 'users'
    __table_args__ = (UniqueConstraint('username'), UniqueConstraint('email'))

    id = DescribedColumn(Integer, primary_key=True)
    username = DescribedColumn(String(32), index=True, nullable=False)
    email = DescribedColumn(String(64), index=True, nullable=True)
    password_hash = DescribedColumn(String(128))
    is_admin = DescribedColumn(Boolean, default=False)
    datetime_created = DescribedColumn(DateTime, nullable=False,
                                       description="UTC datetime of the upload of the image to the DB")

    def __init__(self, password="", **kwargs):
        kwargs['datetime_created'] = datetime.datetime.now()
        Base.__init__(self, **kwargs)


    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=3600 * 24):
        s = Serializer(app.config['API_SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token, api_secret_key: str):
        s = Serializer(api_secret_key)
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        user = User.query.get(data['id'])
        return user

    @staticmethod
    def get_username(token_or_username, api_secret_key: str):
        user = User.verify_auth_token(token_or_username, api_secret_key)
        if user is None:
            return token_or_username
        else:
            return user.username
