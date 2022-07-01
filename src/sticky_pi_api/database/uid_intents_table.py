import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import Integer,  DateTime, UniqueConstraint, String, Text, ForeignKey, Column
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class UIDIntents(BaseCustomisations):
    _max_age = 60 *60
    _max_requested_images = 64

    __tablename__ = 'uid_intents'

    __table_args__ = None

    id = DescribedColumn(Integer, primary_key=True)


    parent_image_id = Column(Integer, ForeignKey('images.id', ondelete="CASCADE"), nullable=False)
    parent_image = relationship("Images", back_populates="uid_intents")

    @classmethod
    def max_requested_images(cls):
        return cls._max_requested_images

    @classmethod
    def min_intent_timestamp(cls):
        now = datetime.datetime.now()
        return now - datetime.timedelta(seconds=cls._max_age)

    def __init__(self, info, api_user_id=None):
        info['api_user_id'] = api_user_id

        super().__init__(**info)




