import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import  Integer,  DateTime, UniqueConstraint, String, Text, ForeignKey, Column
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class UIDAnnotations(BaseCustomisations):
    __tablename__ = 'uid_annotations'
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

    def __init__(self, info, api_user_id=None):
        column_names = UIDAnnotations.column_names()
        # we just keep the fields that are present in the db, we None the others
        i_dict = {}

        for k in column_names:
            if k in info.keys():
                i_dict[k] = info[k]
            else:
                i_dict[k] = None
        i_dict['api_user_id'] = api_user_id
        super().__init__(**i_dict)


