import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import Integer, DateTime, UniqueConstraint, SmallInteger, Float, DECIMAL, String
from sticky_pi_api.utils import string_to_datetime
from sticky_pi_api.database.utils import Base, BaseCustomisations, DescribedColumn


class TiledTuboids(Base, BaseCustomisations):
    __tablename__ = 'tiled_tuboids'
    __table_args__ = (UniqueConstraint('tuboid_id', name='tuboid_id'),)

    itc_labels = relationship("ITCLabels",
                              back_populates="parent_tuboid",
                              cascade="all, delete",
                              passive_deletes=True
                              )

    id = DescribedColumn(Integer, primary_key=True,
                         description="The unique identifier of each series")

    tuboid_id = DescribedColumn(String(100), nullable=False,
                                description="the dirname of the tuboid, acting as a uid")

    id_in_series = DescribedColumn(Integer, nullable=False,
                                   description="the original series id")

    device = DescribedColumn(String(8), nullable=False,
                             description="An 8 char hexadecimal code describing the hardware chip of the device that"
                                         "acquired the image")

    start_datetime = DescribedColumn(DateTime, nullable=False,
                                     description="The UTC date and time at the first shot was taken")

    end_datetime = DescribedColumn(DateTime, nullable=False,
                                   description="The UTC date and time at which the last shot was taken")

    series_start_datetime = DescribedColumn(DateTime, nullable=False,
                                            description="The UTC date and time at the analysed series started")

    series_end_datetime = DescribedColumn(DateTime, nullable=False,
                                          description="The UTC date and time at which the analysed series ended")

    n_shots = DescribedColumn(Integer, nullable=False,
                              description="the number of shots taken")

    algo_version = DescribedColumn(String(46),
                                   nullable=False)  # something like "1598113346-ad2cd78dfaca12821046dfb8994724d5" ( `X-Y` X:timestamp of the model, Y:md5 of the model)

    datetime_created = DescribedColumn(DateTime, nullable=False)
    uploader = DescribedColumn(Integer, nullable=True)  # the user_id of the user who uploaded the data

    def __init__(self, data):

        input = \
            {k: v for k, v in
             zip(['device', 'series_start_datetime', 'series_end_datetime', 'algo_version', 'id_in_series'],
                 data['tuboid_id'].split('.'))}

        assert len(input) == 5, input

        input['id_in_series'] = int(input['id_in_series'])
        input['tuboid_id'] = data['tuboid_id']
        input['n_shots'] = 0
        first_shot_datetime = None

        with open(data['metadata'], 'r') as f:
            while True:
                line = f.readline().rstrip()
                if not line:
                    break
                prefix, center_real, center_imag, scale = line.split(',')
                device, annotation_datetime = prefix.split('.')
                assert device == input['device']
                if first_shot_datetime is None:
                    first_shot_datetime = annotation_datetime
                input['n_shots'] += 1
        input['start_datetime'] = first_shot_datetime
        input['end_datetime'] = annotation_datetime

        input['datetime_created'] = datetime.datetime.now()

        i_dict = {}
        for k, v in input.items():

            try:
                i_dict[k] = string_to_datetime(v)
            except (TypeError, ValueError) as e:
                i_dict[k] = v

        Base.__init__(self, **i_dict)

    def __repr__(self):
        return "<TiledTuboid(device='%s', start_datetime='%s', id_in_series='%s')>" % (
            self.device, self.start_datetime, self.id_in_series)
