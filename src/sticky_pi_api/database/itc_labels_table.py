import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import Integer, DateTime, UniqueConstraint, String, Text, ForeignKey, Column
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class ITCLabels(BaseCustomisations):
    __tablename__ = 'itc_labels'
    __table_args__ = (UniqueConstraint('parent_tuboid_id', 'algo_name', 'algo_version', name='label_id'),)

    id = DescribedColumn(Integer, primary_key=True)

    parent_tuboid_id = Column(Integer, ForeignKey('tiled_tuboids.id', ondelete="CASCADE"), nullable=False)
    parent_tuboid = relationship("TiledTuboids", back_populates="itc_labels")

    algo_name = DescribedColumn(String(32), nullable=False)  # something like "sticky-pi-universal-insect-detector")
    algo_version = DescribedColumn(String(46),
                                   nullable=False)  # something like "1598113346-ad2cd78dfaca12821046dfb8994724d5" ( `X-Y` X:timestamp of the model, Y:md5 of the model)

    # datetime_created = DescribedColumn(DateTime, nullable=False)
    # uploader = DescribedColumn(Integer, nullable=True,
    #                            description='The user_id of the user who uploaded the data')
    label = DescribedColumn(Integer, nullable=False)

    pattern = DescribedColumn(String(128), nullable=False,
                              description='A regex pattern describing the taxonomy')

    type = DescribedColumn(String(32), nullable=False,
                           description='The type of object (pre-taxonomic level)')

    order = DescribedColumn(String(32), nullable=True,
                            description='Taxonomy, order name')

    family = DescribedColumn(String(32), nullable=True,
                             description='Taxonomy, family name')

    genus = DescribedColumn(String(32), nullable=True,
                            description='Taxonomy, genus name')

    species = DescribedColumn(String(32), nullable=True,
                              description='Taxonomy, species name')

    def __init__(self, info, api_user_id=None):
        column_names = ITCLabels.column_names()
        # we just keep the fields that are present in the db, we None the others
        i_dict = {}
        for k in column_names:
            if k in info.keys():
                i_dict[k] = info[k]
            else:
                i_dict[k] = None
        i_dict['api_user_id'] = api_user_id
        super().__init__( **i_dict)

