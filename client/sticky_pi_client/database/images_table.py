import datetime
from sqlalchemy import Column, Integer,  DateTime, UniqueConstraint, SmallInteger, Float, DECIMAL, CHAR
from sticky_pi_client.image_parser import ImageParser
from sticky_pi_client.database.utils import Base, BaseCustomisations


class Images(Base, BaseCustomisations):
    __tablename__ = 'images'

    def __init__(self, file):
        parser = ImageParser(file)
        self._file_blob = parser.file_blob
        self._thumbnail = parser.thumbnail
        self._thumbnail_mini = parser.thumbnail_mini

        column_names = Images.column_names()

        # we just keep the fields that are present in the db, we None the others
        i_dict = {}
        for k in column_names:
            if k in parser.keys():
                i_dict[k] = parser[k]
            else:
                i_dict[k] = None

        i_dict['datetime_created'] = datetime.datetime.now()

        Base.__init__(self, **i_dict)

    @property
    def filename(self):
        return "%s.%s.jpg" % (self.device, self.datetime.strftime('%Y-%m-%d_%H-%M-%S'))

    @property
    def file_blob(self):
        return self._file_blob

    @property
    def thumbnail(self):
        return self._thumbnail

    @property
    def thumbnail_mini(self):
        return self._thumbnail_mini

    id = Column(Integer, primary_key=True)

    image_id = UniqueConstraint('device_id', 'datetime')

    device = Column(CHAR(8), nullable=False)
    datetime = Column(DateTime, nullable=False)
    md5 = Column(CHAR(32), nullable=False)
    datetime_created = Column(DateTime,  nullable=False)

    device_version = Column(CHAR(10), default="1.0.0", nullable=True)
    api_version = Column(CHAR(10), default="1.0.0", nullable=True)
    uploader = Column(CHAR(10), nullable=True)

    width = Column(SmallInteger, nullable=False)
    height = Column(SmallInteger, nullable=False)

    # Nullable, if GPS fails
    alt = Column(SmallInteger, nullable=True)
    lat = Column(DECIMAL(9, 6), nullable=True)
    lng = Column(DECIMAL(9, 6), nullable=True)

    # Nullable, if sensors fail
    temp = Column(Float, nullable=True)
    hum = Column(Float, nullable=True)

    no_flash_shutter_speed  = Column(Float, nullable=False)
    no_flash_exposure_time = Column(Float, nullable=False)
    no_flash_bv = Column(Float, nullable=False)
    no_flash_iso = Column(Float, nullable=False)


    def __repr__(self):
        return "<Image(device='%s', datetime='%s', md5='%s')>" % (
                                    self.device, self.datetime, self.md5)
