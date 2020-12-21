import io
import logging
import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import Integer, DateTime, UniqueConstraint, SmallInteger, Float, DECIMAL, String
from sticky_pi_api.utils import string_to_datetime
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class TuboidSeries(BaseCustomisations):
    __tablename__ = 'tuboid_series'
    __table_args__ = (UniqueConstraint('device', 'start_datetime', 'end_datetime', 'algo_name', 'algo_version', name='tiled_series_id'),)

    tiled_tuboids = relationship("TiledTuboids",
                              back_populates="parent_series",
                              cascade="all, delete",
                              passive_deletes=True
                              )

    id = DescribedColumn(Integer, primary_key=True,
                         description="The unique identifier of each series")

    device = DescribedColumn(String(8), nullable=False,
                             description="An 8 char hexadecimal code describing the hardware chip of the device that"
                                         "acquired the image")

    start_datetime = DescribedColumn(DateTime, nullable=False,
                                     description="The UTC date and time at the first shot was taken")

    end_datetime = DescribedColumn(DateTime, nullable=False,
                                   description="The UTC date and time at which the last shot was taken")


    n_images = DescribedColumn(Integer, nullable=False,
                              description="the number of shots taken")

    n_tuboids = DescribedColumn(Integer, nullable=False,
                               description="the number of shots taken")

    algo_name = DescribedColumn(String(64), nullable=False)  # something like "sticky-pi-universal-insect-detector")

    algo_version = DescribedColumn(String(46),
                                   nullable=False)  # something like "1598113346-ad2cd78dfaca12821046dfb8994724d5" ( `X-Y` X:timestamp of the model, Y:md5 of the model)

    # datetime_created = DescribedColumn(DateTime, nullable=False)
    # uploader = DescribedColumn(Integer, nullable=True)  # the user_id of the user who uploaded the data

    def __init__(self, data, api_user=None):

        i_dict = {}
        for k, v in data.items():
            try:
                i_dict[k] = string_to_datetime(v)
            except (TypeError, ValueError) as e:
                i_dict[k] = v

        i_dict['api_user'] = api_user
        super().__init__(**i_dict)

    def __repr__(self):
        return "<TuboidSeries(device='%s', start_datetime='%s', end_datetime='%s')>" % (
            self.device, self.start_datetime, self.end_datetime)
