import datetime
import copy
import logging
import os
import json
import sqlalchemy
from sqlalchemy import or_, and_
from sqlalchemy.orm import sessionmaker
from sticky_pi_api.utils import string_to_datetime
from sticky_pi_api.database.utils import Base
from sticky_pi_api.storage import DiskStorage, BaseStorage, S3Storage
from sticky_pi_api.configuration import BaseAPIConf
from sticky_pi_api.database.images_table import Images
from sticky_pi_api.database.uid_annotations_table import UIDAnnotations
from sticky_pi_api.types import InfoType, MetadataType, AnnotType, List, Union, Dict, Any
from sticky_pi_api.database.users_tables import Users
from sticky_pi_api.database.tiled_tuboids_table import TiledTuboids
from sticky_pi_api.database.itc_labels_table import ITCLabels
from sticky_pi_api.utils import chunker, datetime_to_string, format_io
from decorate_all_methods import decorate_all_methods
from abc import ABC, abstractmethod


@decorate_all_methods(format_io, exclude=['__init__'])
class BaseAPISpec(ABC):
    # def __init__(self, *args, **kwargs):
    #     pass
    @abstractmethod
    def get_images(self, info: InfoType, what: str = 'metadata') -> MetadataType:
        """
        Retrieves information about a given set of images, defined by their parent device and the
        datetime of the picture. *If an image is not available, no data is returned for this image*.

        :param info: A list of dicts. each dicts has, at least, keys: ``'device'`` and ``'datetime'``
        :param what: The nature of the objects to retrieve.
            One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail_mini'``}
        :return: A list of dictionaries with one element for each queried value. Each dictionary contains
            the fields present in the underlying database plus a ``'url'`` fields to retrieve the actual object requested
            (i.e. the ``what``) argument. In the case of ``what='metadata'``, ``url=''`` (i.e. no url is generated).
        """
        raise NotImplementedError()

    @abstractmethod
    def _put_new_images(self, files: List[str]) -> MetadataType:
        """
        Uploads a set of client image files to the API.
        The user would use ``BaseClient.put_images(files)``,
        which first discovers which files are to be uploaded for incremental upload.

        :param files: A list of path to client files

        :return: The metadata of the files that were actually uploaded
        """
        raise NotImplementedError()

    @abstractmethod
    def get_image_series(self, info, what: str = 'metadata') -> MetadataType:
        """
        Retrieves image sequences (i.e. series).
        A series contains all images from a given device within a datetime range.

        :param info: A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``. ``device`` is interpreted to the MySQL like operator.
            For instance,one can match all devices with ``device="%"``.
        :param what: The nature of the objects to retrieve.
            One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail_mini'``}
        :return: A list of dictionaries with one element for each queried value. Each dictionary contains
            the fields present in the underlying database plus a ``'url'`` fields to retrieve the actual object requested
            (i.e. the ``what``) argument. In the case of ``what='metadata'``, ``url=''`` (i.e. no url is generated).
        """

        raise NotImplementedError()

    @abstractmethod
    def put_uid_annotations(self, info: AnnotType) -> MetadataType:
        """
        :param info: A list of dictionaries corresponding to annotations (one list element per image).
            The annotations are formatted as a dictionaries with two keys: ``'annotations'`` and ``'metadata'``.

            * ``'metadata'`` must have the fields:
                * ``'algo_name'``: the name of the algorithm used to find the object (e.g. ``'sticky-pi-universal-insect-detector'``)
                * ``'algo_version'``: The version of the algorithm as `timestamp-md5` (e.g. ``'1598113346-ad2cd78dfaca12821046dfb8994724d5'``)
                * ``'device'``: The device that took the annotated image (e.g. ``'5c173ff2'``)
                * ``'datetime'``: The datetime at which the image was taken (e.g. ``'2020-06-20_21-33-24'``)
                * ``'md5'``: The md5 of the image that was analysed (e.g. ``'9e6e908d9c29d332b511f8d5121857f8'``)
            * ``'annotations'`` is a list where each element represent an object. It has the fields:
                * ``'contour'``: a 3d array encoding the position of the vertices (as convention in OpenCV)
                * ``'name'``: the name/type of the object (e.g. ``'insect'``)
                * ``'fill_colour'`` and  ``'stroke_colour'``: the colours of the contour (if it is to be drawn -- e.g. ``'#0000ff'``)
                * ``'value'``: an optional integer further describing the contour (e.g. ``1``)

        :return: The metadata of the uploaded annotations (i.e. a list od dicts. each field of the dict naming a column in the database).
            This corresponds to the annotation data as represented in ``UIDAnnotations``
        """
        raise NotImplementedError()

    @abstractmethod
    def get_uid_annotations(self, info: InfoType, what: str = 'metadata') -> MetadataType:
        """
        Retrieves annotations for a given set of images.

        :param info: A list of dict with keys: ``'device'`` and ``'datetime'``
        :param what: The nature of the object to retrieve. One of {``'metadata'``, ``'json'``}.
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database table (see ``UIDAnnotations``).
            In the case of ``what='metadata'``, the field ``json=''``.
            Otherwise, it contains a json string with the actual annotation data.
        """
        raise NotImplementedError()

    @abstractmethod
    def _put_tiled_tuboids(self, files: List[Dict[str, str]]) -> MetadataType:
        """
            Uploads a set of client tiled tuboid files to the API.
            The user would use ``BaseClient.put_tiled_tuboid(files)``.


            :param files: A list of dict. Each dict contains keys:
                * ``tuboid_id``: a formatted string describing the tuboid series and tuboid id e.g. ``08038ade.2020-07-08_20-00-00.2020-07-09_15-00-00.0002``
                * ``metadata``: the path to a comma-separated files that contains metadata for each tuboid shot
                * ``tuboid``: the path to a tiled jpg containing (some of) the shots described in metadata, in the same order
                * ``context``: the path to an illustration (jpg) of the detected object highlighted in the whole image of the first shot

            :return: The metadata of the files that were actually uploaded
            """
        raise NotImplementedError()

    @abstractmethod
    def get_tiled_tuboid_series(self, info: InfoType, what: str = "metadata") -> MetadataType:
        """
        Retrieves tiled tuboids -- i.e. stitched annotations into a tile,
        where the assumption is one tuboid per instance.
        A series contains all tuboids fully  contained within a range

        :param info: A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``. ``device`` is interpreted to the MySQL like operator.
            For instance,one can match all devices with ``device="%"``.
        :param what: The nature of the objects to retrieve, either ``'data'`` or ``'metadata'``. ``'metadata'`` will not
            add the extra three fields mapping the files to the results
        :return: A list of dictionaries with one element for each queried value. Each dictionary contains
            the fields present in the underlying database plus the fields ``'metadata'``, ``'tuboid'`` and ``'context'``
            fields, which have a url to fetch the relevant file.
        """
        raise NotImplementedError()

    @abstractmethod
    def _get_itc_labels(self, info: List[Dict]) -> MetadataType:
        """
        Retrieves labels for a given set of tiled tuboid

        :param info: A list of dict with key: ``'tuboid_id'``
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database table (see ``ITCLabels``).
        """
        raise NotImplementedError()

    @abstractmethod
    def put_itc_labels(self, info: List[Dict[str, Union[str, int]]]) -> MetadataType:
        """
        Stores labels for a given set of tiled tuboid

        :param info: A list of dict with keys: ``'tuboid_id'``, ``'label'``, ``'pattern'``,
            ``'algo_version'``and ``'algo_name'``  (see ``ITCLabels``).
        :return: the field corresponding to the labels that were submitted
        """
        raise NotImplementedError()


    @abstractmethod
    def _get_ml_bundle_file_list(self, bundle_name: str, what: str = "all") -> List[Dict[str, Union[float, str]]]:
        """
        Get a list of file for a given ML Bundle.

        A ML bundle contains files necessary to train and run a ML training/inference (data, configs and model).
        :param bundle_name: the name of the machine learning buncle to fetch the files from
        :param what: One of {``'all'``, ``'data'``,``'model'`` }, to return all files, only the training data(training),
            or only the model (inference), respectively.
        :return: A list of dict containing the fields ``key`` and ``url`` of the files to be downloaded,
         which can be used to download the files
        """
        raise NotImplementedError()

    @abstractmethod
    def _get_ml_bundle_upload_links(self, bundle_name: str, info: List[Dict[str, Union[float, str]]]) -> \
            List[Dict[str, Union[float, str]]]:
        """
        Ask the client for a list of upload url for the files described in info.

        :param bundle_name: the name of the machine learning bundle to fetch the files from
        :param info: a list of dict with fields {``'key'``, ``'md5'``, ``'mtime'``}.
            ``'key'`` is the file path, relative to the storage root (e.g. ``data/mydata.jpg``)
        :return: The same list of dictionaries as ``info``, with an extra field pointing to a destination url ``'url'``,
            where the client can then upload their data.
        """
        raise NotImplementedError()


    @abstractmethod
    def get_users(self, info: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        Get a list of API users. Either all users (Default), or filter users by field if ``info`` is specified.
        In the latter case, the union of all matched users is returned.

        :param info: A dictionary acting as a filter, using an SQL like-type match.
            For instance ``{'username': '%'}`` return all users.
        :return: A list of users as represented in the underlying database, as one dictionary [per user,
            with the keys being database column names. Note that the crypo/sensitive
            fields are not returned (e.g. password_hash)
        """
        raise NotImplementedError()

    @abstractmethod
    def put_users(self, info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add a list of users defined by a dict of proprieties.

        :param info: A list of dictionary each dictionary has the fields  {``'username'``, ``'password'``},
            and optionally: {``'email'``, ``'is_admin'``,``'model'`` },
        :return: A list of dictionaries describing the users that were created
        """
        raise NotImplementedError()


@decorate_all_methods(format_io, exclude=['__init__'])
class BaseAPI(BaseAPISpec, ABC):
    _storage_class = BaseStorage
    _get_image_chunk_size = 64  # the maximal number of images to request from the database in one go

    def __init__(self, api_conf: BaseAPIConf, *args, **kwargs):
        super().__init__()
        self._configuration = api_conf
        self._storage = self._storage_class(api_conf=api_conf, *args, **kwargs)
        self._db_engine = self._create_db_engine()

        Base.metadata.create_all(self._db_engine, Base.metadata.tables.values(), checkfirst=True)

    @abstractmethod
    def _create_db_engine(self, *args, **kwargs) -> sqlalchemy.engine.Engine:
        raise NotImplementedError()

    def _put_new_images(self, files: List[str]):
        session = sessionmaker(bind=self._db_engine)()
        # store the uploaded images
        out = []
        # for each image
        for f in files:
            # We parse the image file to make to its own DB object
            im = Images(f)
            out.append(im.to_dict())
            session.add(im)

            # try to store images, only commit if storage worked.
            # rollback otherwise
            try:
                self._storage.store_image_files(im)
                session.commit()
            except Exception as e:
                session.rollback()
                logging.error("Storage Error. Failed to store image %s" % im)
                logging.error(e)
                raise e
        return out

    def _put_tiled_tuboids(self, files: List[Dict[str, str]]):  # fixme return type
        session = sessionmaker(bind=self._db_engine)()
        # store the uploaded images
        out = []
        # for each tuboid
        for data in files:
            # print(data)
            # We parse the tuboid data as a entry
            tub = TiledTuboids(data)

            # fixme we should check that no tuboid exists within this -- implicit -- series.
            # ie no overlap of [series_start_datetime, series_end_datetime] allowed for same device, algo_version,...
            out.append(tub.to_dict())
            session.add(tub)

            # try to store images, only commit if storage worked.
            # rollback otherwise
            try:
                self._storage.store_tiled_tuboid(data)
                session.commit()
            except Exception as e:
                session.rollback()
                logging.error("Storage Error. Failed to store tuboid %s" % tub)
                logging.error(e)
                raise e
        return out

    def _get_ml_bundle_file_list(self, bundle_name: str, what: str = "all") -> List[Dict[str, Union[float, str]]]:
        return self._storage.get_ml_bundle_file_list(bundle_name, what)

    def _get_ml_bundle_upload_links(self, bundle_name: str, info: List[Dict[str, Union[float, str]]]) -> \
            List[Dict[str, Union[float, str]]]:
        return self._storage.get_ml_bundle_upload_links(bundle_name, info)

    def put_uid_annotations(self, info: AnnotType):
        info = copy.deepcopy(info)
        session = sessionmaker(bind=self._db_engine)()
        out = []
        # for each image
        for data in info:

            json_str = json.dumps(data, default=str)
            dic = data['metadata']
            annotations = data['annotations']

            n_objects = len(annotations)
            dic['json'] = json_str

            # fixme. here we should get multiple images in one go, prior to parsing annotations ?
            parent_img_list = self.get_images([dic])

            if len(parent_img_list) != 1:
                raise ValueError("could not find parent image for %s" % str(dic))
            parent_img = parent_img_list[0]

            dic['parent_image_id'] = parent_img["id"]
            dic['n_objects'] = n_objects
            if dic['md5'] != parent_img['md5']:
                raise ValueError("Trying to add an annotation for %s, but md5 differ" % str(data))

            annot = UIDAnnotations(dic)

            o = annot.to_dict()
            o["json"] = ""
            out.append(o)
            session.add(annot)
            session.commit()
        return out

    def get_uid_annotations(self, info: MetadataType, what: str = 'metadata'):
        images = self.get_images(info)

        out = []

        for i, images_chunk in enumerate(chunker(images, self._get_image_chunk_size)):
            logging.info("Getting image annotations... %i-%i / %i" %
                         (i * self._get_image_chunk_size,
                          i * self._get_image_chunk_size + len(images_chunk),
                          len(info)))

            image_ids = [Images.id == img['id'] for img in images_chunk]
            session = sessionmaker(bind=self._db_engine)()
            conditions = or_(*image_ids)

            q = session.query(Images.id).filter(conditions)

            parent_img_ids = [i[0] for i in q.all()]
            q = session.query(UIDAnnotations).filter(UIDAnnotations.parent_image_id.in_(parent_img_ids))
            # q = session.query(UIDAnnotations)

            for annots in q:
                annot_dict = annots.to_dict()
                if what == 'metadata':
                    del annot_dict['json']
                elif what == 'data':
                    pass
                else:
                    raise ValueError("Unexpected `what` argument: %s. Should be in {'metadata', 'data'}")
                out.append(annot_dict)
        return out

    def get_images(self, info: MetadataType, what: str = 'metadata'):
        out = []
        info = copy.deepcopy(info)
        session = sessionmaker(bind=self._db_engine)()

        # We fetch images by chunks:

        for i, info_chunk in enumerate(chunker(info, self._get_image_chunk_size)):

            logging.info("Getting images... %i-%i / %i" %
                         (i * self._get_image_chunk_size,
                          i * self._get_image_chunk_size + len(info_chunk),
                          len(info)))

            for inf in info_chunk:
                inf['datetime'] = string_to_datetime(inf['datetime'])

            conditions = [and_(Images.datetime == inf['datetime'], Images.device == inf['device'])
                          for inf in info_chunk]

            q = session.query(Images).filter(or_(*conditions))

            for img in q:
                img_dict = img.to_dict()
                img_dict['url'] = self._storage.get_url_for_image(img, what)
                out.append(img_dict)
        return out

    def get_tiled_tuboid_series(self, info: InfoType, what: str='metadata') -> MetadataType:
        session = sessionmaker(bind=self._db_engine)()
        out = []
        assert what in ('data', 'metadata')

        info = copy.deepcopy(info)
        for i in info:
            i['start_datetime'] = string_to_datetime(i['start_datetime'])
            i['end_datetime'] = string_to_datetime(i['end_datetime'])
            q = session.query(TiledTuboids).filter(TiledTuboids.start_datetime >= i['start_datetime'],
                                                   # nthe here we need to include both bounds in case a tuboid ends just in between
                                                   TiledTuboids.end_datetime <= i['end_datetime'],
                                                   TiledTuboids.device.like(i['device']))

            if q.count() == 0:
                logging.warning('No data for series %s' % str(i))
                # raise Exception("more than one match for %s" % i)

            for tub in q.all():
                tub_dict = tub.to_dict()
                if what == 'data':
                    tub_dict.update(self._storage.get_urls_for_tiled_tuboids(tub_dict))
                out.append(tub_dict)
        return out

    def get_image_series(self, info: MetadataType, what: str = 'metadata'):
        session = sessionmaker(bind=self._db_engine)()
        out = []

        info = copy.deepcopy(info)
        for i in info:
            i['start_datetime'] = string_to_datetime(i['start_datetime'])
            i['end_datetime'] = string_to_datetime(i['end_datetime'])
            q = session.query(Images).filter(Images.datetime >= i['start_datetime'],
                                             Images.datetime < i['end_datetime'],
                                             Images.device.like(i['device']))

            if q.count() == 0:
                logging.warning('No data for series %s' % str(i))
                # raise Exception("more than one match for %s" % i)

            for img in q.all():
                img_dict = img.to_dict()
                img_dict['url'] = self._storage.get_url_for_image(img, what)
                out.append(img_dict)
        return out

    def put_itc_labels(self, info: List[Dict[str, Union[str, int]]]) -> MetadataType:
        info = copy.deepcopy(info)
        session = sessionmaker(bind=self._db_engine)()
        out = []
        # for each image
        for data in info:
            q = session.query(TiledTuboids).filter(TiledTuboids.tuboid_id == data['tuboid_id'])
            assert q.count() == 1, "No match for %s" % data
            data['parent_tuboid_id'] = q.first().tuboid_id
            label = ITCLabels(data)
            out.append(label.to_dict())
            session.add(label)
            session.commit()
        return out

    def _get_itc_labels(self, info: List[Dict]) -> MetadataType:
        info = copy.deepcopy(info)
        out = []
        for i, info_chunk in enumerate(chunker(info, self._get_image_chunk_size)):
            logging.info("Getting tuboid label... %i-%i / %i" %
                         (i * self._get_image_chunk_size,
                          i * self._get_image_chunk_size + len(info_chunk),
                          len(info)))
            tuboid_ids = [ITCLabels.parent_tuboid_id  == j['tuboid_id'] for j in info_chunk]

            session = sessionmaker(bind=self._db_engine)()
            conditions = or_(*tuboid_ids)
            q = session.query(ITCLabels).filter(conditions)

            for annots in q:
                out.append(annots.to_dict())
        return out

    def put_users(self, info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        info = copy.deepcopy(info)
        session = sessionmaker(bind=self._db_engine)()
        out = []
        for data in info:
            user = Users(**data)
            out.append(user.to_dict())
            user.hash_password(data["password"])
            session.add(user)
            session.commit()
        return out

    def get_users(self, info: Dict[str, str] = None) -> List[Dict[str, Any]]:
        if info is None:
            info = {}

        session = sessionmaker(bind=self._db_engine)()
        out = []
        conditions = [and_(getattr(Users, i).like(info[i]) for i in info.keys())]
        q = session.query(Users).filter(or_(*conditions))

        for user in q.all():
            user.password_hash = "***********"
            user_dict = user.to_dict()
            out.append(user_dict)
        return out


class LocalAPI(BaseAPI):
    _storage_class = DiskStorage
    _database_filename = 'database.db'

    def _create_db_engine(self):
        local_dir = self._configuration.LOCAL_DIR
        engine_url = "sqlite:///%s" % os.path.join(local_dir, self._database_filename)
        return sqlalchemy.create_engine(engine_url, connect_args={"check_same_thread": False})


class RemoteAPI(BaseAPI):
    _storage_class = S3Storage

    def _create_db_engine(self):
        engine_url = "mysql+pymsql://%s:%s@%s/%s?charset=utf8mb4" % (self._configuration.MYSQL_USER,
                                                                     self._configuration.MYSQL_PASSWORD,
                                                                     self._configuration.MYSQL_HOST,
                                                                     self._configuration.MYSQL_DB_NAME
                                                                     )

        return sqlalchemy.create_engine(engine_url)
