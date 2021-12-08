import datetime
import copy
import logging
import os
import json
import sqlalchemy
from sqlalchemy import or_, and_
from sqlalchemy.orm import sessionmaker
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
# from multiprocessing.pool import Pool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy import event
from sqlalchemy.dialects import mysql
import sqlite3
import time

from sticky_pi_api.utils import json_io_converter
from sticky_pi_api.database.utils import Base
from sticky_pi_api.storage import DiskStorage, BaseStorage, S3Storage
from sticky_pi_api.configuration import BaseAPIConf
from sticky_pi_api.database.images_table import Images
from sticky_pi_api.database.uid_annotations_table import UIDAnnotations
from sticky_pi_api.types import InfoType, MetadataType, AnnotType, List, Union, Dict, Any, Tuple
from sticky_pi_api.database.utils import BaseCustomisations
from sticky_pi_api.database.users_tables import Users
from sticky_pi_api.database.tuboid_series_table import TuboidSeries
from sticky_pi_api.database.tiled_tuboids_table import TiledTuboids
from sticky_pi_api.database.itc_labels_table import ITCLabels

from sticky_pi_api.utils import chunker, json_inputs_to_python, json_out_parser
from decorate_all_methods import decorate_all_methods
from abc import ABC, abstractmethod


# this decorator ensures json inputs are formated as python objects
@decorate_all_methods(json_inputs_to_python, exclude=['__init__', '_put_new_images', '_put_tiled_tuboids'])
class BaseAPISpec(ABC):
    @abstractmethod
    def get_images(self, info: InfoType, what: str = 'metadata', client_info: Dict[str, Any] = None) -> MetadataType:
        """
        Retrieves information about a given set of images, defined by their parent device and the
        datetime of the picture. *If an image is not available, no data is returned for this image*.

        :param client_info: optional information about the client/user contains key ``'username'``
        :param info: A list of dicts. each dicts has, at least, keys: ``'device'`` and ``'datetime'``
        :param what: The nature of the objects to retrieve.
            One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail-mini'``}
        :return: A list of dictionaries with one element for each queried value. Each dictionary contains
            the fields present in the underlying database plus a ``'url'`` fields to retrieve the actual object requested
            (i.e. the ``what``) argument. In the case of ``what='metadata'``, ``url=''`` (i.e. no url is generated).
        """
        pass

    @abstractmethod
    def delete_images(self, info: MetadataType, client_info: Dict[str, Any] = None):
        """
        #fixme. this is false. it now takes a set of images as returned by get_images
        Delete a set of images, defined by their parent device and the
        datetime of the picture.

        :param client_info: optional information about the client/user contains key ``'username'``
        :param info: A list of dicts. each dicts has, at least, keys: ``'device'`` and ``'datetime'``
        :return: A list of dictionaries with one element for each deleted image.
        """
        pass

    # fixme should be called series?
    @abstractmethod
    def delete_tiled_tuboids(self, info: InfoType, client_info: Dict[str, Any] = None) -> MetadataType:
        """
        Delete a set of tiled tuboids series, defined by their parent device, start a
        datetime.

        :param client_info: optional information about the client/user contains key ``'username'``
        :param info: A list of dicts. each dicts has, at least, keys: ``'device'``,
            ``'start_datetime'`` and ``'end_datetime'``
        :return: A list of dictionaries with one element for each deleted image.
        """
        pass

    @abstractmethod
    def _put_new_images(self, files: List[str], client_info: Dict[str, Any] = None) -> MetadataType:
        """
        Uploads a set of client image files to the API.
        The user would use ``BaseClient.put_images(files)``,
        which first discovers which files are to be uploaded for incremental upload.

        :param client_info: optional information about the client/user contains key ``'username'``
        :param files: A list of path to client files

        :return: The metadata of the files that were actually uploaded
        """
        pass

    @abstractmethod
    def get_image_series(self, info, what: str = 'metadata', client_info: Dict[str, Any] = None) -> MetadataType:
        """
        Retrieves image sequences (i.e. series).
        A series contains all images from a given device within a datetime range.

        :param client_info: optional information about the client/user contains key ``'username'``
        :param info: A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``. ``device`` is interpreted to the MySQL like operator.
            For instance,one can match all devices with ``device="%"``.
        :param what: The nature of the objects to retrieve.
            One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail-mini'``}
        :return: A list of dictionaries with one element for each queried value. Each dictionary contains
            the fields present in the underlying database plus a ``'url'`` fields to retrieve the actual object requested
            (i.e. the ``what``) argument. In the case of ``what='metadata'``, ``url=''`` (i.e. no url is generated).
        """

        pass

    @abstractmethod
    def put_uid_annotations(self, info: AnnotType, client_info: Dict[str, Any] = None) -> MetadataType:
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
        :param client_info: optional information about the client/user contains key ``'username'``
        :return: The metadata of the uploaded annotations (i.e. a list od dicts. each field of the dict naming a column in the database).
            This corresponds to the annotation data as represented in ``UIDAnnotations``
        """
        pass

    @abstractmethod
    def get_uid_annotations(self, info: InfoType, what: str = 'metadata',
                            client_info: Dict[str, Any] = None) -> MetadataType:
        """
        Retrieves annotations for a given set of images.

        :param info: A list of dict with keys: ``'device'`` and ``'datetime'``
        :param what: The nature of the object to retrieve. One of {``'metadata'``, ``'json'``}.
        :param client_info: optional information about the client/user contains key ``'username'``
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database table (see ``UIDAnnotations``).
            In the case of ``what='metadata'``, the field ``json=''``.
            Otherwise, it contains a json string with the actual annotation data.
        """
        pass

    @abstractmethod
    def get_uid_annotations_series(self, info: InfoType, what: str = 'metadata',
                                   client_info: Dict[str, Any] = None) -> MetadataType:
        """
        Retrieves annotations for a given set of images.

        :param info:  A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``. ``device`` is interpreted to the MySQL like operator.
        :param what: The nature of the object to retrieve. One of {``'metadata'``, ``'json'``}.
        :param client_info: optional information about the client/user contains key ``'username'``
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database table (see ``UIDAnnotations``).
            In the case of ``what='metadata'``, the field ``json=''``.
            Otherwise, it contains a json string with the actual annotation data.
        """
        pass

    @abstractmethod
    def _put_tiled_tuboids(self, files: List[Dict[str, Union[Dict, str]]],
                           client_info: Dict[str, Any] = None) -> MetadataType:
        """
            Uploads a set of client tiled tuboid files to the API.
            The user would use ``BaseClient.put_tiled_tuboid(files)``.


            :param files: A list of dict. Each dict contains keys:
                * ``tuboid_id``: a formatted string describing the tuboid series and tuboid id e.g. ``08038ade.2020-07-08_20-00-00.2020-07-09_15-00-00.0002``
                * ``series_info``: a dictionary with information regarding the series the tuboid belong to.
                    I.e. keys ``'algo_name'``, ``'algo_version'``, ``'start_datetime'``, ``'end_datetime'``, ``'device'``
                * ``metadata``: the path to a comma-separated files that contains metadata for each tuboid shot, or a file-like object
                * ``tuboid``: the path to a tiled jpg containing (some of) the shots described in metadata, in the same order, or a file-like object
                * ``context``: the path to an illustration (jpg) of the detected object highlighted in the whole image of the first shot, or a file-like object
            :param client_info: optional information about the client/user contains key ``'username'``
            :return: The metadata of the files that were actually uploaded
            """
        pass

    @abstractmethod
    def get_tiled_tuboid_series(self, info: InfoType, what: str = "metadata",
                                client_info: Dict[str, Any] = None) -> MetadataType:
        """
        Retrieves tiled tuboids -- i.e. stitched annotations into a tile,
        where the assumption is one tuboid per instance.
        A series contains all tuboids fully  contained within a range

        :param info: A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``. ``device`` is interpreted to the MySQL like operator.
            For instance,one can match all devices with ``device="%"``.
        :param what: The nature of the objects to retrieve, either ``'data'`` or ``'metadata'``. ``'metadata'`` will not
            add the extra three fields mapping the files to the results
        :param client_info: optional information about the client/user contains key ``'username'``
        :return: A list of dictionaries with one element for each queried value. Each dictionary contains
            the fields present in the underlying database plus the fields ``'metadata'``, ``'tuboid'`` and ``'context'``
            fields, which have a url to fetch the relevant file.
        """
        pass

    @abstractmethod
    def _get_itc_labels(self, info: List[Dict], client_info: Dict[str, Any] = None) -> MetadataType:
        """
        Retrieves labels for a given set of tiled tuboid

        :param client_info: optional information about the client/user contains key ``'username'``
        :param info: A list of dict with key: ``'tuboid_id'``
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database table (see ``ITCLabels``).
        """
        pass

    @abstractmethod
    def put_itc_labels(self, info: List[Dict[str, Union[str, int]]],
                       client_info: Dict[str, Any] = None) -> MetadataType:
        """
        Stores labels for a given set of tiled tuboid

        :param info: A list of dict with keys: ``'tuboid_id'``, ``'label'``, ``'pattern'``,
            ``'algo_version'``and ``'algo_name'``  (see ``ITCLabels``).
        :param client_info: optional information about the client/user contains key ``'username'``
        :return: the field corresponding to the labels that were submitted
        """
        pass

    @abstractmethod
    def _get_ml_bundle_file_list(self, info: str, what: str = "all", client_info: Dict[str, Any] = None) -> List[
        Dict[str, Union[float, str]]]:
        """
        Get a list of file for a given ML Bundle.

        A ML bundle contains files necessary to train and run a ML training/inference (data, configs and model).
        :param info: the name of the machine learning bundle to fetch the files from
        :param what: One of {``'all'``, ``'data'``,``'model'`` }, to return all files, only the training data(training),
            or only the model (inference), respectively.
        :param client_info: optional information about the client/user contains key ``'username'``
        :return: A list of dict containing the fields ``key``, ``url`` and ``mtime`` of the files to be downloaded,
         which can be used to download the files
        """
        pass

    @abstractmethod
    def _get_ml_bundle_upload_links(self, info: List[Dict[str, Union[float, str]]],
                                    client_info: Dict[str, Any] = None) -> \
            List[Dict[str, Union[float, str]]]:
        """
        Ask the client for a list of upload url for the files described in info.


        :param info: a list of dict with fields {``bundle_name``,``'key'``, ``'md5'``, ``'mtime'``}.
            ``'key'`` is the file path, relative to the storage root (e.g. ``data/mydata.jpg``).
             ``bundle_name`` is the name of the machine learning bundle to fetch the files from
        :param client_info: optional information about the client/user contains key ``'username'``
        :return: The same list of dictionaries as ``info``, with an extra field pointing to a destination url ``'url'``,
            where the client can then upload their data.
        """
        pass

    @abstractmethod
    def get_users(self, info: List[Dict[str, str]] = None, client_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get a list of API users. Either all users (Default), or filter users by field if ``info`` is specified.
        In the latter case, the union of all matched users is returned.

        :param info: A dictionary acting as a filter, using an SQL like-type match.
            For instance ``{'username': '%'}`` return all users.
        :param client_info: optional information about the client/user contains key ``'username'``
        :return: A list of users as represented in the underlying database, as one dictionary [per user,
            with the keys being database column names. Note that the crypo/sensitive
            fields are not returned (e.g. password_hash)
        """
        pass

    @abstractmethod
    def put_users(self, info: List[Dict[str, Any]], client_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Add a list of users defined by a dict of proprieties.

        :param info: A list of dictionary each dictionary has the fields  {``'username'``, ``'password'``},
            and optionally: {``'email'``, ``'is_admin'``},
        :param client_info: optional information about the client/user contains key ``'username'``
        :return: A list of dictionaries describing the users that were created
        """
        pass

    @abstractmethod
    def get_token(self, client_info: Dict[str, Any] = None) -> Dict[str, Union[str, int]]:
        """
        A authentication token for a user.
        injection in this function.

        :param client_info: optional information about the client/user contains key ``'username'``
        :return: a dictionary with the keys ``'token'`` and ``'expiration'``, an ascii formatted token,
            and expiration timestamp, respectively
        """
        pass


@decorate_all_methods(json_inputs_to_python, exclude=['__init__', '_put_new_images', '_put_tiled_tuboids'])
class BaseAPI(BaseAPISpec, ABC):
    _storage_class = BaseStorage
    _get_image_chunk_size = 64  # the maximal number of images to request from the database in one go

    def __init__(self, api_conf: BaseAPIConf, *args, **kwargs):
        # super().__init__()
        self._configuration = api_conf
        self._storage = self._storage_class(api_conf=api_conf, *args, **kwargs)
        self._db_engine = self._create_db_engine()

        Base.metadata.create_all(self._db_engine, Base.metadata.tables.values(), checkfirst=True)
        self._serializer = Serializer(self._configuration.SECRET_API_KEY)

    @abstractmethod
    def _create_db_engine(self, *args, **kwargs) -> sqlalchemy.engine.Engine:
        pass

    def _put_new_images(self, files: List[str], client_info: Dict[str, Any] = None):
        session = sessionmaker(bind=self._db_engine)()
        try:
            # store the uploaded images
            out = []
            # for each image
            for f in files:
                # We parse the image file to make to its own DB object

                api_user = client_info['username'] if client_info is not None else None
                im = Images(f, api_user=api_user)
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
        finally:
            session.close()

    def _put_tiled_tuboids(self, files: List[Dict[str, Union[str, Dict]]],
                           client_info: Dict[str, Any] = None):  # fixme return type
        session = sessionmaker(bind=self._db_engine)()
        try:
            # store the uploaded images
            out = []
            # for each tuboid
            while len(files) > 0:
                data = files.pop()
                # We parse the tuboid data as an entry
                api_user = client_info['username'] if client_info is not None else None
                ts = TuboidSeries(data['series_info'])
                q = session.query(TuboidSeries).filter(TuboidSeries.start_datetime == ts.start_datetime,
                                                       TuboidSeries.end_datetime == ts.end_datetime,
                                                       TuboidSeries.device == ts.device,
                                                       TuboidSeries.algo_name == ts.algo_name,
                                                       TuboidSeries.algo_version == ts.algo_version
                                                       )
                # we add this series if it does not exist
                if q.count() == 0:
                    logging.info('Adding new tuboid series %s' % ts)
                    session.add(ts)
                    session.commit()
                    files += [data]
                    return self._put_tiled_tuboids(files, client_info)
                else:
                    ts = q.first()
                    logging.info('Using tuboid series %s' % ts)

                tub = TiledTuboids(data, parent_tuboid_series=ts, api_user=api_user)
                q = session.query(TiledTuboids).filter(TiledTuboids.parent_series_id == ts.id)
                if not (q.count() < ts.n_tuboids):
                    raise IntegrityError(
                        'Cannot add more tuboids to parent series %s. Already all of them are there' % ts, None, None)

                assert tub.start_datetime >= ts.start_datetime, 'tuboid starts before its parent series'
                assert tub.end_datetime <= ts.end_datetime, 'tuboid ends after its parent series'

                session.add(tub)

                # try to store images, only commit if storage worked.
                # rollback otherwise
                try:
                    self._storage.store_tiled_tuboid(data)
                    session.commit()
                    out.append(tub.to_dict())
                except Exception as e:
                    session.rollback()
                    logging.error("Storage Error. Failed to store tuboid %s" % tub)
                    logging.error(e)
                    raise e
            return out
        finally:
            session.close()

    def _get_ml_bundle_file_list(self, info: str, what: str = "all", client_info: Dict[str, Any] = None) -> \
            List[Dict[str, Union[float, str]]]:
        return self._storage.get_ml_bundle_file_list(info, what)

    def _get_ml_bundle_upload_links(self, info: List[Dict[str, Union[float, str]]],
                                    client_info: Dict[str, Any] = None) -> \
            List[Dict[str, Union[float, str]]]:
        new_info = {}
        for i in info:
            bundle = i['bundle_name']
            if bundle not in new_info.keys():
                new_info[bundle] = []
            new_info[bundle].append(i)
        out = []
        for bundle_name, info in new_info.items():
            out += self._storage.get_ml_bundle_upload_links(bundle_name, info)
        return out
    @abstractmethod
    def _columns_name_types(self, table: BaseCustomisations):
        pass

    @abstractmethod
    def _sql_select_fields(self, col_name_types: List[Tuple[str, str]], make_filename:bool = True):
        pass

    @abstractmethod
    def _sql_in_tuples(self, field_names: Tuple, tuple_list: List[Tuple]):
        pass

    def _sql_in_tuples(self, field_names: Tuple, tuple_list: List[Tuple]):
        ins = [str(tuple(m)) for m in tuple_list]
        condition = f"({', '.join(field_names)}) in ({','.join(ins)})"
        return condition

    def _sql_in_tuples(self, field_names: Tuple, tuple_list: List[Tuple]):
        ors = []
        for t in tuple_list:
            ands = " AND ".join([f"{f} = '{v}'" for f, v in zip(field_names, t)])
            ands = f"({ands})"
            ors.append(ands)
        condition = " OR ".join(ors)
        return condition



    def get_images(self, info: MetadataType, what: str = 'metadata', client_info: Dict[str, Any] = None):
        colnames = self._columns_name_types(Images)
        sql_select = self._sql_select_fields(colnames, make_filename=True)

        out = []
        # for i, info_chunk in enumerate(chunker(info, self._get_image_chunk_size)):
        matches = [tuple((str(inf['datetime']), inf['device'])) for inf in info]
        condition = self._sql_in_tuples(('SUBSTR(datetime, 1, 19)', 'device'), matches)
        full_query = f"SELECT {sql_select} FROM {Images.table_name()} WHERE {condition}"
        with self._db_engine.connect() as connection:
            full_results = connection.execute(full_query.replace("%", "%%"))
            for row in full_results:
                img_dict = dict(row)
                img_dict["url"] = self._storage.get_url_for_image(img_dict, what=what)
                del img_dict["filename"]
                out.append(img_dict)
        return self._manual_output_handler(out)

    def get_image_series(self, info: MetadataType, what: str = 'metadata', client_info: Dict[str, Any] = None):
        # session = sessionmaker(bind=self._db_engine)() # try:
        out = []
        colnames = self._columns_name_types(Images)
        sql_select = self._sql_select_fields(colnames, make_filename=True)
        for i in info:
            conditions = [f"datetime >= \"{str(i['start_datetime'])}\"",
                          f"datetime < \"{str(i['end_datetime'])}\"",
                          f"device like \"{i['device']}\""]
            full_query = f"SELECT {sql_select} FROM {Images.table_name()} WHERE {' AND '.join(conditions)}"
            img_dict = None
            with self._db_engine.connect() as connection:
                full_results = connection.execute(full_query.replace("%", "%%"))
                for row in full_results:
                    img_dict = dict(row)
                    img_dict["url"] = self._storage.get_url_for_image(img_dict, what=what)
                    del img_dict["filename"]
                    out.append(img_dict)
            if img_dict is None:
                logging.warning('No data for series %s' % str(i))
        return self._manual_output_handler(out)
        # finally:
        #     session.close()

    def delete_images(self, info: MetadataType, client_info: Dict[str, Any] = None) -> MetadataType:
        out = []
        session = sessionmaker(bind=self._db_engine)()
        try:
            # We fetch images by chunks:
            for i, info_chunk in enumerate(chunker(info, self._get_image_chunk_size)):
                logging.info("Deleting images... %i-%i / %i" %
                             (i * self._get_image_chunk_size,
                              i * self._get_image_chunk_size + len(info_chunk),
                              len(info)))

                conditions = [and_(Images.datetime == inf['datetime'], Images.device == inf['device'])
                              for inf in info_chunk]

                q = session.query(Images).filter(or_(*conditions))

                for img in q:
                    img_dict = img.to_dict()
                    session.delete(img)
                    try:
                        self._storage.delete_image_files(img)
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        logging.error("Storage Error. Failed to delete image %s" % img)
                        logging.error(e)
                        raise e
                    out.append(img_dict)
            return out
        finally:
            session.close()

    def put_uid_annotations(self, info: AnnotType, client_info: Dict[str, Any] = None):
        info = copy.deepcopy(info)
        session = sessionmaker(bind=self._db_engine)()
        try:
            all_annots = []
            # for each image
            for data in info:

                json_str = json.dumps(data, default=json_io_converter)
                dic = data['metadata']
                annotations = data['annotations']

                n_objects = len(annotations)
                dic['json'] = json_str

                # fixme. here we should get multiple images in one go, prior to parsing annotations ?

                q = session.query(Images).filter(Images.datetime == dic['datetime'], Images.device == dic['device'])

                if q.count() == 0:
                    raise ValueError("could not find parent image for %s" % str(dic))
                if q.count() > 1:
                    raise ValueError("<More than one parent image for  %s" % str(dic))
                parent_img = q.first()
                # dic['parent_image_id'] = parent_img["id"]
                dic['n_objects'] = n_objects
                if dic['md5'] != parent_img.md5:
                    raise ValueError("Trying to add an annotation for %s, but md5 differ" % str(data))
                dic['parent_image_id'] = parent_img.id
                annot = UIDAnnotations(dic)
                parent_img.uid_annotations.append(annot)

                all_annots.append(annot)
                session.add(annot)

                # https://stackoverflow.com/questions/3659142/bulk-insert-with-sqlalchemy-orm

            session.commit()
            out = []
            for annot in all_annots:
                o = annot.to_dict()
                o["json"] = ""
                out.append(o)

            return out
        finally:
            session.close()

    def get_uid_annotations(self, info: MetadataType, what: str = 'metadata', client_info: Dict[str, Any] = None):
        out = []
        session = sessionmaker(bind=self._db_engine)()
        try:

            for i, info_chunk in enumerate(chunker(info, self._get_image_chunk_size)):
                logging.info("Getting image annotations... %i-%i / %i" %
                             (i * self._get_image_chunk_size,
                              i * self._get_image_chunk_size + len(info_chunk),
                              len(info)))

                conditions = [UIDAnnotations.parent_image.has(and_(Images.datetime == inf['datetime'],
                                                                   Images.device == inf['device']))
                              for inf in info_chunk]

                q = session.query(UIDAnnotations).filter(or_(*conditions))
                for annots in q:
                    annot_dict = annots.to_dict()
                    if what == 'metadata':
                        del annot_dict['json']
                    out.append(annot_dict)

            return out
        finally:
            session.close()

    def get_uid_annotations_series(self, info: MetadataType, what: str = 'metadata',
                                   client_info: Dict[str, Any] = None):

        colnames = self._columns_name_types(UIDAnnotations)
        if what == 'metadata':
            colnames = [c for c in colnames if c[0] != "json"]

        sql_select = self._sql_select_fields(colnames, make_filename=False)
        out = []
        for i in info:
            conditions = ["images.id = uid_annotations.parent_image_id",
                          f"images.datetime >= \"{str(i['start_datetime'])}\"",
                          f"images.datetime < \"{str(i['end_datetime'])}\"",
                          f"images.device like \"{i['device']}\""]
            full_query = f"SELECT {sql_select} from {UIDAnnotations.table_name()} WHERE EXISTS (Select 1 FROM {Images.table_name()} WHERE {' AND '.join(conditions)})"
            row_dict = None
            with self._db_engine.connect() as connection:
                full_results = connection.execute(full_query.replace("%", "%%"))
                for row in full_results:
                    row_dict = dict(row)
                    out.append(row_dict)
            if row_dict is None:
                logging.warning('No data for series %s' % str(i))
        return self._manual_output_handler(out)

    def get_tiled_tuboid_series(self, info: InfoType, what: str = 'metadata',
                                client_info: Dict[str, Any] = None) -> MetadataType:
        session = sessionmaker(bind=self._db_engine)()
        try:
            out = []
            assert what in ('data', 'metadata')

            info = copy.deepcopy(info)
            for i in info:
                q = session.query(TiledTuboids).filter(TiledTuboids.parent_series.has(
                    and_(TuboidSeries.start_datetime >= i['start_datetime'],
                         # here we need to include both bounds in case a tuboid ends just in between
                         TuboidSeries.end_datetime <= i['end_datetime'],
                         TuboidSeries.device.like(i['device']))))

                if q.count() == 0:
                    logging.warning('No data for series %s' % str(i))

                for tub in q.all():
                    tub_dict = tub.to_dict()
                    if what == 'data':
                        tub_dict.update(self._storage.get_urls_for_tiled_tuboids(tub_dict))
                    out.append(tub_dict)
            return out
        finally:
            session.close()

    def delete_tiled_tuboids(self, info: InfoType, client_info: Dict[str, Any] = None) -> MetadataType:
        out = []
        info = copy.deepcopy(info)
        session = sessionmaker(bind=self._db_engine)()
        try:
            # We fetch images by chunks:

            for inf in info:
                q = session.query(TuboidSeries).filter(TuboidSeries.start_datetime >= inf['start_datetime'],
                                                       TuboidSeries.end_datetime <= inf['end_datetime'],
                                                       TuboidSeries.device.like(inf['device']))

                for ts in q:
                    img_dict = ts.to_dict()
                    all_tuboids = [t for t in
                                   session.query(TiledTuboids).filter(TiledTuboids.parent_series_id == ts.id)]
                    session.delete(ts)
                    try:
                        for tub in all_tuboids:
                            self._storage.delete_tiled_tuboid_files(tub)
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        logging.error("Storage Error. Failed to delete series %s" % tub)
                        logging.error(e)
                        raise e
                    out.append(img_dict)
            return out
        finally:
            session.close()

    def put_itc_labels(self, info: List[Dict[str, Union[str, int]]],
                       client_info: Dict[str, Any] = None) -> MetadataType:
        info = copy.deepcopy(info)
        session = sessionmaker(bind=self._db_engine)()
        try:
            out = []

            # for each image
            for data in info:
                q = session.query(TiledTuboids).filter(TiledTuboids.tuboid_id == data['tuboid_id'])
                assert q.count() == 1, "No match for %s" % data
                data['parent_tuboid_id'] = q.first().id
                api_user = client_info['username'] if client_info is not None else None
                label = ITCLabels(data, api_user=api_user)
                out.append(label.to_dict())
                session.add(label)
                session.commit()
            return out
        finally:
            session.close()

    def _get_itc_labels(self, info: List[Dict], client_info: Dict[str, Any] = None) -> MetadataType:
        info = copy.deepcopy(info)
        out = []
        session = sessionmaker(bind=self._db_engine)()
        try:
            for i, info_chunk in enumerate(chunker(info, self._get_image_chunk_size)):
                logging.info("Getting tuboid label... %i-%i / %i" %
                             (i * self._get_image_chunk_size,
                              i * self._get_image_chunk_size + len(info_chunk),
                              len(info)))
                # can be a single row
                tuboid_ids = [TiledTuboids.tuboid_id == j['tuboid_id'] for j in info_chunk]
                conditions = or_(*tuboid_ids)
                q = session.query(TiledTuboids).filter(conditions)
                parent_tuboid_ids = [ITCLabels.parent_tuboid_id == r.id for r in q.all()]
                conditions = or_(*parent_tuboid_ids)
                q = session.query(ITCLabels).filter(conditions)

                for annots in q:
                    out.append(annots.to_dict())
            return out
        finally:
            session.close()

    def put_users(self, info: List[Dict[str, Any]], client_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        info = copy.deepcopy(info)
        session = sessionmaker(bind=self._db_engine)()
        try:
            out = []
            for data in info:
                api_user = client_info['username'] if client_info is not None else None
                user = Users(**data, api_user=api_user)
                out.append(user.to_dict())
                session.add(user)
                session.commit()
            out = self.get_users([{'username': o['username'] for o in out}])

            return out
        finally:
            session.close()

    def get_users(self, info: List[Dict[str, str]] = None, client_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        out = []
        if info is None:
            info = [{'username': "%"}]
        session = sessionmaker(bind=self._db_engine)()
        try:
            for inf in info:
                conditions = [and_(getattr(Users, k).like(inf[k]) for k in inf.keys())]
                q = session.query(Users).filter(or_(*conditions))

                for user in q.all():
                    user.password_hash = "***********"
                    user_dict = user.to_dict()
                    out.append(user_dict)
            return out
        finally:
            session.close()

    def verify_password(self, username_or_token: str, password: str):
        session = sessionmaker(bind=self._db_engine)()
        try:
            if not username_or_token:
                logging.warning('No such user or token `%s`' % username_or_token)
                return False

            try:
                data = self._serializer.loads(username_or_token)
                user = session.query(Users).get(data['id'])
            except SignatureExpired:
                user = None  # valid token, but expired
            except BadSignature:
                user = None  # invalid token

            if not user:
                # try to authenticate with username/password
                user = session.query(Users).filter(Users.username == username_or_token).first()
                if not user:
                    logging.warning('No such user: `%s`' % username_or_token)
                    return False
                if not user.verify_password(password):
                    logging.warning('Failed to authenticate `%s` with password' % username_or_token)
                    return False
            return user.username
        finally:
            session.close()

    def _make_db_session(self):
        return sessionmaker(bind=self._db_engine)()

    #this is when serialisation is maually done for optimisation. In this case, the Local API will want to
    # reserialise into python compatible data (e.g. at this stage, dates are string already).
    # for the remote API, this method will just return its argument
    @abstractmethod
    def _manual_output_handler(self, out: Any):
        pass

# from https://docs.sqlalchemy.org/en/13/dialects/sqlite.html#foreign-key-support
# this allow cascade delete on sqlite3
# see https://github.com/sqlalchemy/sqlalchemy/issues/4858
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class LocalAPI(BaseAPI):
    _storage_class = DiskStorage
    _database_filename = 'database.db'

    def _create_db_engine(self):
        local_dir = self._configuration.LOCAL_DIR
        engine_url = "sqlite:///%s" % os.path.join(local_dir, self._database_filename)
        return sqlalchemy.create_engine(engine_url, connect_args={"check_same_thread": False, 'timeout': 60})

    def _make_db_session(self):
        return sessionmaker(bind=self._db_engine)(autoflush=False)

    def get_token(self, client_info: Dict[str, Any] = None):
        return {'token': None, 'expiration': 0}

    def _columns_name_types(self, table: BaseCustomisations):
        with self._db_engine.connect() as connection:
            q = "PRAGMA table_info(%s);" % \
                table.table_name()
            result = connection.execute(q)
            out = [(r[1], r[2].lower()) for r in result]
            return out

            # return [(c_name, c_type) for c_name, c_type in result]

    def _sql_select_fields(self, col_name_types: List[Tuple[str, str]], make_filename:bool = False):
        cols = []
        for c_name, c_type in col_name_types:
            if c_type == "datetime":
                cols.append(f'SUBSTR(REPLACE({c_name}, " ", "T"), 1, 19) || "Z" AS {c_name}')
            else:
                cols.append(c_name)
        if make_filename:
            cols.append('device || "." || REPLACE(SUBSTR(REPLACE(datetime, " ", "_"), 1, 19), ":", "-") || ".jpg"AS filename')
        out = ', '.join(cols)
        return out

    def _manual_output_handler(self, out: Any):
        json_a = json.dumps(out)
        out = json.loads(json_a, object_hook=json_out_parser)
        return out

class RemoteAPI(BaseAPI):
    _storage_class = S3Storage
    _get_image_chunk_size = 1024  # the maximal number of images to request from the database in one go

    def _manual_output_handler(self, out: Any):
        return out

    def get_token(self, client_info: Dict[str, Any] = None) -> Dict[str, Union[str, int]]:
        session = sessionmaker(bind=self._db_engine)()
        username = client_info['username']
        user = session.query(Users).filter(Users.username == username).first()
        token = user.generate_auth_token(self._configuration.SECRET_API_KEY)
        return token

    def put_images(self, files: List[str], client_info: Dict[str, Any] = None):
        return self._put_new_images(files, client_info=client_info)

    def _columns_name_types(self, table: BaseCustomisations):
        with self._db_engine.connect() as connection:
            q = "select column_name, data_type from information_schema.columns where table_name = '%s';" % \
                table.table_name()
            result = connection.execute(q)
            return [(c_name, c_type) for c_name, c_type in result]


    def _sql_select_fields(self, col_name_types: List[Tuple[str, str]], make_filename:bool = False):
        cols = []
        for c_name, c_type in col_name_types:
            if c_type == "datetime":
                cols.append(f'DATE_FORMAT({c_name}, "%Y-%m-%dT%H:%i:%SZ") AS {c_name}')
            elif c_type == "decimal":
                cols.append(f'CAST({c_name} as DOUBLE)  AS {c_name}')
            else:
                cols.append(c_name)
        if make_filename:
            cols.append('concat(device, ".", DATE_FORMAT(datetime, "%Y-%m-%d_%H-%i-%S"), ".jpg") AS filename')
        return ', '.join(cols)


    def _create_db_engine(self):
        engine_url = "mysql+mysqldb://%s:%s@%s/%s?charset=utf8mb4" % (self._configuration.MYSQL_USER,
                                                                      self._configuration.MYSQL_PASSWORD,
                                                                      self._configuration.MYSQL_HOST,
                                                                      self._configuration.MYSQL_DATABASE
                                                                      )
        return sqlalchemy.create_engine(engine_url, pool_recycle=3600, echo=True)
        # return sqlalchemy.create_engine(engine_url, pool_recycle=3600)
