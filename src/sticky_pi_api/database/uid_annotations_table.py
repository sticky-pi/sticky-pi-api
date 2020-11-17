import json
import datetime
from sqlalchemy import Column, Integer,  DateTime, UniqueConstraint, String, Text, ForeignKey
from sticky_pi_client.image_parser import ImageParser
from sticky_pi_client.database.utils import Base, BaseCustomisations


class UIDAnnotations(Base, BaseCustomisations):
    __tablename__ = 'uid_annotations'

    def __init__(self, info):
        column_names = UIDAnnotations.column_names()

        # we just keep the fields that are present in the db, we None the others
        i_dict = {}

        for k in column_names:
            if k in info.keys():
                i_dict[k] = info[k]
            else:
                i_dict[k] = None

        i_dict['datetime_created'] = datetime.datetime.now()
        Base.__init__(self, **i_dict)

    id = Column(Integer, primary_key=True)
    __table_args__ = (UniqueConstraint('parent_image_id', 'algo_name', 'algo_version', name='annotation_id'),
                      )

    parent_image_id = Column(Integer, ForeignKey('images.id'), nullable=False)
    algo_name = Column(String(32), nullable=False) # something like "sticky-pi-universal-insect-detector")
    algo_version = Column(String(46), nullable=False) # something like "1598113346-ad2cd78dfaca12821046dfb8994724d5" ( `X-Y` X:timestamp of the model, Y:md5 of the model)

    datetime_created = Column(DateTime,  nullable=False)
    uploader = Column(Integer, nullable=True)  # the user_id of the user who uploaded the data
    n_objects = Column(Integer, nullable=False)  # the number of detected objects
    json = Column(Text(2 ^ 32), nullable=False) # this is a longtext


    # def __repr__(self):
    #     return "<Annotations(device='%s', datetime='%s', md5='%s', n_objects=%i)>" % (
    #                                 self.device, self.datetime, self.md5, self.n_objects)
