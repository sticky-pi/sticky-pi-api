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
from sticky_pi_api.storage import DiskStorage, BaseStorage
from sticky_pi_api.configuration import BaseAPIConf
from sticky_pi_api.database.images_table import Images
from sticky_pi_api.database.uid_annotations_table import UIDAnnotations
from sticky_pi_api.types import InfoType, MetadataType, AnnotType, List, Union, Dict, Any
from sticky_pi_api.database.users_tables import Users
from sticky_pi_api.utils import chunker




class BaseAPISpec(object):
    # def __init__(self, *args, **kwargs):
    #     pass

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

    def _put_new_images(self, files: List[str]) -> MetadataType:
        """
        Uploads a set of client image files to the API.
        The user would use ``BaseClient.put_images(files)``,
        which first discovers which files are to be uploaded for incremental upload.

        :param files: A list of path to client files

        :return: The metadata of the files that were actually uploaded
        """
        raise NotImplementedError()

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

    def get_uid_annotations(self, info: InfoType, what: str = 'metadata') -> MetadataType:
        """
        Reteives annotations for a given set of images.

        :param info: A list of dict with keys: ``'device'`` and ``'datetime'``
        :param what: The nature of the object to retrieve. One of {``'metadata'``, ``'json'``}.
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database table (see ``UIDAnnotations``).
            In the case of ``what='metadata'``, the field ``json=''``.
            Otherwise, it contains a json string with the actual annotation data.
        """
        raise NotImplementedError()

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

    def put_users(self, info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add a list of users defined by a dict of proprieties.

        :param info: A list of dictionary each dictionary has the fields  {``'username'``, ``'password'``},
            and optionally: {``'email'``, ``'is_admin'``,``'model'`` },
        :return: A list of dictionaries describing the users that were created
        """
        raise NotImplementedError()




class BaseAPI(BaseAPISpec):
    _storage_class = BaseStorage
    _get_image_chunk_size = 64  # the maximal number of images to request from the database in one go
    def __init__(self, api_conf: BaseAPIConf, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configuration = api_conf
        self._storage = self._storage_class(api_conf = api_conf, *args, **kwargs)
        self._db_engine = self._create_db_engine()

        Base.metadata.create_all(self._db_engine, Base.metadata.tables.values(), checkfirst=True)

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
        for i in info:
            if not isinstance(i['datetime'], datetime.datetime):
                i['datetime'] = string_to_datetime(i['datetime'])
        session = sessionmaker(bind=self._db_engine)()

        # We fetch images by chunks:
        for i, info_chunk in enumerate(chunker(info, self._get_image_chunk_size)):
            logging.info("Putting images... %i-%i / %i" %
                         (i * self._get_image_chunk_size,
                          i * self._get_image_chunk_size + len(info_chunk),
                          len(info)))

            conditions = [and_(Images.datetime == inf['datetime'], Images.device == inf['device']) for inf in info_chunk]
            q = session.query(Images).filter(or_(*conditions))

            for img in q:
                img_dict = img.to_dict()
                img_dict['url'] = self._storage.get_url_for_image(img, what)
                out.append(img_dict)
        return out

    def get_image_series(self, info: MetadataType, what: str = 'metadata'):
        session = sessionmaker(bind=self._db_engine)()
        out = []

        info = copy.deepcopy(info)
        for i in info:
            i['start_datetime'] = string_to_datetime(i['start_datetime'])
            i['end_datetime'] = string_to_datetime(i['end_datetime'])

        for i in info:
            q = session.query(Images).filter(Images.datetime >= i['start_datetime'],
                                             Images.datetime < i['end_datetime'],
                                             Images.device.like(i['device']))

            if q.count() == 0:
                logging.warning('No data for series %s' % str(i))
                #raise Exception("more than one match for %s" % i)

            for img in q.all():
                img_dict = img.to_dict()
                img_dict['url'] = self._storage.get_url_for_image(img, what)
                out.append(img_dict)


            # warn when trying to retrieve the URL of an image that does not exist
            # "metadata" to be used when diffing to see if data exists in db
            # elif what != "metadata":
            #     logging.warning("No image for %s at %s" % (i['device'], i['datetime']))

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

# TODO here implement a mysql connection
# class Remote(BaseAPI):
#     _storage_class = #TODO s3 Storage
#     _database_filename = 'database.db'
#
#     def _create_db_engine(self, local_dir):
#         engine_url = "sqlite:///%s" % os.path.join(local_dir, self._database_filename)
#         return sqlalchemy.create_engine(engine_url)

