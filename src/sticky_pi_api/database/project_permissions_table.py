from sqlalchemy import SmallInteger, String, UniqueConstraint, Column, Integer, ForeignKey
from sticky_pi_api.database.utils import  BaseCustomisations, DescribedColumn
from sqlalchemy.orm import relationship


class ProjectPermissions(BaseCustomisations):
    __tablename__ = 'project_permissions'
    __table_args__ = (UniqueConstraint('parent_user_id', "parent_project_id"), )

    parent_project_id = Column(Integer, ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    parent_project = relationship("Projects", back_populates="project_permissions")


    parent_user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    parent_user = relationship("Users", back_populates="project_permissions")

    # parent_project_id = DescribedColumn(String(32), index=True, nullable=False)
    # username = DescribedColumn(String(20), index=True, nullable=True)

    id = DescribedColumn(Integer, primary_key=True)
    level = DescribedColumn(SmallInteger, nullable=False)


    def __init__(self, api_user_id=None, **kwargs):
        info = kwargs
        info['api_user_id'] = api_user_id
        super().__init__(**info)





