import datetime
from sqlalchemy.orm import relationship

from sqlalchemy import Integer, DateTime, UniqueConstraint, SmallInteger, Float, DECIMAL, String, Index, Boolean

from sticky_pi_api.image_parser import ImageParser
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class Images(BaseCustomisations):
    __tablename__ = 'images'
    __table_args__ = (UniqueConstraint('device', 'datetime', name='image_id'), Index("image_uid", 'device', 'datetime'))

    uid_annotations = relationship("UIDAnnotations",
                                   back_populates="parent_image",
                                   cascade="all, delete",
                                   passive_deletes=True
                                   )

    # tasks = relationship("Task", back_populates="project", passive_deletes=True)

    id = DescribedColumn(Integer, primary_key=True,
                         description="The unique identifier of each image")
    device = DescribedColumn(String(8), nullable=False,
                             description="An 8 char hexadecimal code describing the hardware chip of the device that"
                                         "acquired the image")
    datetime = DescribedColumn(DateTime, nullable=False,
                               description="The UTC date and time at which the image was taken")

    md5 = DescribedColumn(String(32), nullable=False,
                          description="An md5 checksum of the whole JPEG image. Used internally for"
                                      "sanity checks and  incremental transfers")

    device_version = DescribedColumn(String(8), default="1.0.0", nullable=True,
                                     description="The version of the firmware on the device -- that took the image")

    width = DescribedColumn(SmallInteger, nullable=False,
                            description="Width of the image, in pixels")
    height = DescribedColumn(SmallInteger, nullable=False,
                             description="Height of the image, in pixels")

    # Nullable, if GPS fails
    lat = DescribedColumn(DECIMAL(9, 6), nullable=True)
    lng = DescribedColumn(DECIMAL(9, 6), nullable=True)
    alt = DescribedColumn(SmallInteger, nullable=True,
                          description="Altitude")

    # Nullable, if sensors fail
    temp = DescribedColumn(Float, nullable=True)
    hum = DescribedColumn(Float, nullable=True)

    lum = DescribedColumn(Float, nullable=True, description="Light intensity")
    bat = DescribedColumn(SmallInteger, nullable=True, description="How much battery is left [0, 100]")
    but = DescribedColumn(Boolean, nullable=True, description="Whether device was manually turned on (button)")

    def __init__(self, file, api_user=None):
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
        i_dict['api_user'] = api_user
        super().__init__(**i_dict)


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

    def __repr__(self):
        return "<Image(device='%s', datetime='%s', md5='%s')>" % (
            self.device, self.datetime, self.md5)
