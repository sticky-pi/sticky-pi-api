import datetime
<<<<<<< HEAD
from sqlalchemy.orm import relationship
from sqlalchemy import  Integer,  DateTime, UniqueConstraint, String, Text, ForeignKey, Column
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn
=======
from sqlalchemy import Column, Integer,  DateTime, UniqueConstraint, String, Text, ForeignKey
# from sticky_pi_client.image_parser import ImageParser
from sticky_pi_api.database.utils import Base, BaseCustomisations
>>>>>>> 7daa60a... Revert "Feature tiled tuboids"


class UIDAnnotations(BaseCustomisations):
    __tablename__ = 'uid_annotations'
<<<<<<< HEAD
    __table_args__ = (UniqueConstraint('parent_image_id', 'algo_name', 'algo_version', name='annotation_id'), )

    id = DescribedColumn(Integer, primary_key=True)

    parent_image_id = Column(Integer, ForeignKey('images.id', ondelete="CASCADE"), nullable=False)
    # parent_image_id = Column(Integer, ForeignKey('images.id'), nullable=False)
    parent_image = relationship("Images", back_populates="uid_annotations")

    algo_name = DescribedColumn(String(64), nullable=False) # something like "sticky-pi-universal-insect-detector")
    algo_version = DescribedColumn(String(46), nullable=False) # something like "1598113346-ad2cd78dfaca12821046dfb8994724d5" ( `X-Y` X:timestamp of the model, Y:md5 of the model)

    # datetime_created = DescribedColumn(DateTime,  nullable=False)
    # uploader = DescribedColumn(Integer, nullable=True)  # the user_id of the user who uploaded the data
    n_objects = DescribedColumn(Integer, nullable=False)  # the number of detected objects
    json = DescribedColumn(Text(4294000000), nullable=False)  # this is a longtext
=======
>>>>>>> 7daa60a... Revert "Feature tiled tuboids"

    def __init__(self, info, api_user=None):
        column_names = UIDAnnotations.column_names()

        # we just keep the fields that are present in the db, we None the others
        i_dict = {}

        for k in column_names:
            if k in info.keys():
                i_dict[k] = info[k]
            else:
                i_dict[k] = None
        i_dict['api_user'] = api_user
        super().__init__(**i_dict)


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
