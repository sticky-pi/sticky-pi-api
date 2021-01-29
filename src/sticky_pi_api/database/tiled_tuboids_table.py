import io
import logging
import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import Integer, DateTime, UniqueConstraint, SmallInteger, Float, DECIMAL, String, ForeignKey, Column
from sticky_pi_api.utils import string_to_datetime
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class TiledTuboids(BaseCustomisations):
    __tablename__ = 'tiled_tuboids'
    __table_args__ = (UniqueConstraint('tuboid_id', name='tuboid_id'),)

    itc_labels = relationship("ITCLabels",
                              back_populates="parent_tuboid",
                              cascade="all, delete",
                              passive_deletes=True
                              )

    id = DescribedColumn(Integer, primary_key=True,
                         description="The unique identifier of each series")

    parent_series_id = Column(Integer, ForeignKey('tuboid_series.id', ondelete="CASCADE"), nullable=False)
    parent_series = relationship("TuboidSeries", back_populates="tiled_tuboids")

    tuboid_id = DescribedColumn(String(100), nullable=False,
                                description="the dirname of the tuboid, acting as a uid")

    id_in_series = DescribedColumn(Integer, nullable=False,
                                   description="the original series id")

    start_datetime = DescribedColumn(DateTime, nullable=False,
                                     description="The UTC date and time at the first shot was taken")

    end_datetime = DescribedColumn(DateTime, nullable=False,
                                   description="The UTC date and time at which the last shot was taken")

    n_shots = DescribedColumn(Integer, nullable=False,
                              description="the number of shots taken")

    def __init__(self, data, parent_tuboid_series, api_user=None):

        info = {'id_in_series':int(data['tuboid_id'].split('.')[-1])}
        info['tuboid_id'] = data['tuboid_id']
        file = data['metadata']

        if type(file) == str:
            with open(file, 'r') as f:
                info.update(self._parse(f))
        elif hasattr(file, 'read'):
            f = io.TextIOWrapper(file, encoding='utf-8')
            info.update(self._parse(f))
            f.detach()
        else:
            raise TypeError('Unexpected type for file. Should be either a path or a file-like. file is %s' % type(file))

        i_dict = {}
        for k, v in info.items():
            try:
                i_dict[k] = string_to_datetime(v)
            except (TypeError, ValueError) as e:
                i_dict[k] = v
        i_dict['api_user'] = api_user

        super().__init__(parent_series_id=parent_tuboid_series.id, **i_dict)

    def to_dict(self):
        # extra info from parent series
        out = BaseCustomisations.to_dict(self)
        out["algo_name_series"] = self.parent_series.algo_name
        out["algo_version_series"] = self.parent_series.algo_version
        out["n_tuboids_series"] = self.parent_series.n_tuboids
        return out

    @staticmethod
    def _parse(file):
        out = {'n_shots': 0}
        file.seek(0)
        first_shot_datetime = None
        annotation_datetime = 0
        while True:
            line = file.readline().rstrip()
            if not line:
                break
            prefix, center_real, center_imag, scale = line.split(',')
            dev, annotation_datetime = prefix.split('.')
            if first_shot_datetime is None:
                first_shot_datetime = annotation_datetime
            out['n_shots'] += 1
        out['start_datetime'] = first_shot_datetime
        out['end_datetime'] = annotation_datetime
        assert out['n_shots'] > 0, 'Empty tuboid sent (0 shots)'
        return out

    def __repr__(self):
        return "<TiledTuboid(%s)>" % (
            self.tuboid_id)
