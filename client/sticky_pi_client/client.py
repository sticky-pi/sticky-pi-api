"""
Main module of the client. Implements classes to interact with the API.
"""

import copy
import logging
import os
import json
import pandas as pd
import sqlalchemy
from sqlalchemy import or_, and_
from sqlalchemy.orm import sessionmaker
import shutil
from joblib import Memory, Parallel, delayed
from sticky_pi_client.image_parser import ImageParser
from sticky_pi_client.utils import string_to_datetime, datetime_to_string
from sticky_pi_client.database.utils import Base
from sticky_pi_client.database.images_table import Images
from sticky_pi_client.database.uid_annotations_table import UIDAnnotations
from sticky_pi_client.storage import LocalDBStorage

from typeguard import typechecked
from typing import List, Dict, Union, Any


# for doc
InfoType = List[Dict[str, str]]
MetadataType = List[Dict[str, Union[float, int, str]]]
AnnotType = List[Dict[str, Union[List, Dict[str, Any]]]]



class BaseClient(object):

    _put_chunk_size = 16  # number of images to handle at the same time during upload
    def __init__(self, local_dir: str, n_threads: int = 8):
        """
        Abstract class that defines the methods of the client (common between remote and local).

        :param local_dir: The path to a local directory that acts as a local storage
        :param n_threads: The number of parallel threads to use to compute statistics on the image (md5 and such)
        """
        self._local_dir = local_dir
        self._n_threads = n_threads
        self._cache = Memory(local_dir, verbose=0)


    def get_images(self, info: InfoType, what: str = 'metadata') -> MetadataType:
        """
        Retrieves information about a given set of images, defined by their parent device and the
        datetime of the picture. *If an image is not available, no data is returned for this image*.

        :param info: A list of dicts. each dicts has, at least, keys: ``'device'`` and ``'datetime'``
        :param what: The nature of the objects to retrieve.
            One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail_mini'``}
        :return: A list of dictionaries with one element for each queried value. Each dictionary contains
            the fields present in the underlying database plus a ``'url'`` fields to retrieve the actual object requested
            (i.e. the ``what``) argument. In the case of ``what='metadata'``, ``url=''`` (i.e. no url is genenrated).
        """
        raise NotImplemented()

    def _put_new_images(self, files: List[str]) -> MetadataType:
        """
        Uploads a set of local image files to the API.
        The user would use ``BaseClient.put_images(files)``,
        which first discovers which files are to be uploaded for incremental upload.

        :param files: A list of path to local files

        :return: The metadata of the files that were actually uploaded
        """
        raise NotImplemented()

    def get_image_series(self, info, what: str = 'metadata') -> MetadataType:
        """
        Retrieves image sequences (i.e. series).
        A series contains all images from a given device within a datetime range.

        :param info: A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``
        :param what: The nature of the objects to retrieve.
            One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail_mini'``}
        :return: A list of dictionaries with one element for each queried value. Each dictionary contains
            the fields present in the underlying database plus a ``'url'`` fields to retrieve the actual object requested
            (i.e. the ``what``) argument. In the case of ``what='metadata'``, ``url=''`` (i.e. no url is generated).
        """

        raise NotImplemented()

    def put_uid_annotations(self, info : AnnotType) -> MetadataType:
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

    def get_uid_annotations_series(self, info: InfoType, what: str = 'metadata') -> MetadataType:
        """
        Retrieves annotations for images within a given datetime range

        :param info: A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``
        :param what: The nature of the object to retrieve. One of {``'metadata'``, ``'json'``}.
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database table (see ``UIDAnnotations``).
            In the case of ``what='metadata'``, the field ``json=''``.
            Otherwise, it contains a json string with the actual annotation data.
        """
        # we first fetch the parent images matching a series
        parent_images = self.get_image_series(info, what="metadata")
        # we filter the metadata as only these two fields are necessary
        info = [{k:v for k, v in p.items() if k in {"device", 'datetime'}} for p in parent_images]

        return self.get_uid_annotations(info, what=what)

    def get_images_with_uid_annotations_series(self, info: InfoType, what_image: str = 'metadata', what_annotation: str = 'metadata') -> MetadataType:
        """
        Retrieves images alongside their annotations (if available)  for images from a given device and
        within a given datetime range

        :param info: A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``
        :param what_image: The nature of the image objects to retrieve.
            One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail_mini'``}
        :param what_annotation: The nature of the object to retrieve. One of {``'metadata'``, ``'json'``}.
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database tables (see ``UIDAnnotations`` and ``Images``).
        """
        # we first fetch the parent images matching a series
        parent_images = self.get_image_series(info, what=what_image)
        # we filter the metadata as only these two fields are necessary
        info = [{k:v for k, v in p.items() if k in {"device", 'datetime'}} for p in parent_images]
        parent_images = pd.DataFrame(parent_images)
        annots = self.get_uid_annotations(info, what=what_annotation)
        annots = pd.DataFrame(annots)

        out = pd.merge(parent_images, annots, how='left', left_on=['id'], right_on=['parent_image_id'], suffixes=('', '_annot'))
        # NaN -> None
        out = out.where(pd.notnull(out), None)
        return out.to_dict(orient='records')

    def put_images(self, files : List[str]) -> MetadataType:
        """
        Incrementally upload a list of local files

        :param files: the paths to the local files
        :return: the data of the uploaded files, as represented in by API
        """
        # instead of dealing with images one by one, we send them by chunks
        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        # first find which files need to be uploaded
        to_upload = []
        chunk_size = self._put_chunk_size * self._n_threads
        for i, group in enumerate(chunker(files, chunk_size)):
            logging.info("Putting images... Computing statistics on files %i-%i / %i" % (i*chunk_size,
                                                                                         i * chunk_size + len(group),
                                                                                         len(files)))
            to_upload += self._diff_images_to_upload(group)

        out = []
        # upload by chunks now
        for i, group in enumerate(chunker(to_upload, self._put_chunk_size)):
            logging.info("Putting images... Uploading files %i-%i / %i" % (i*self._put_chunk_size,
                                                                           i * self._put_chunk_size + len(group),
                                                                           len(to_upload)))

            out += self._put_new_images(group)
        logging.info("Putting images... Complete!")
        return out

    def _diff_images_to_upload(self, files):
        """
        Handles the negotiation process during upload. First trying to get the images to be uploaded,
        First gets the images to be sent. Those that already exists and have the same checksum can be skipped,
        to only upload new images

        :param files: A list of file paths
        :type files: List()
        :return: A list representing the subset of files to be uploaded
        :rtype: List()
        """

        # this is a cached parser so we don't need to recompute md5 etc on local files unless they have changed
        @self._cache.cache
        def local_img_stats(file: str, file_stats: Dict):
            i = ImageParser(file)
            out = {'device': i['device'],
                          'datetime': datetime_to_string(i['datetime']),
                          'md5': i['md5'],
                          'url': file}
            return out
        # we can compute the stats in parallel
        img_dicts = Parallel(n_jobs=self._n_threads)(delayed(local_img_stats)(f, os.stat(f)) for f in files)

        # we request these images from the database
        matches = self.get_images(img_dicts, what='metadata')

        # now we diff: we ignore images that exist on DB AND have the same md5
        # we put images that do not exist on db
        # we warn if md5s are different
        img_dicts = pd.DataFrame(img_dicts)
        matches = pd.DataFrame(matches, columns=img_dicts.columns)
        joined = pd.merge(img_dicts, matches, how='left', on = ['device', 'datetime'], suffixes=('', '_match'))
        joined['same_md5'] = joined.apply(lambda row: row.md5_match == row.md5, axis=1)
        joined['already_on_db'] = joined.apply(lambda row: not pd.isna(row.md5_match), axis=1)
        # images that re not yet on the db:
        out = joined[joined.already_on_db == False].url.tolist()

        # fixme. warn/prompt which has a different md5 (and match md5 is not NA)
        return out

    def delete_cache(self):
        cachedir =  os.path.join(self._cache.location, 'joblib')
        shutil.rmtree(cachedir)

@typechecked
class LocalClient(BaseClient):
    _database_filename = 'database.db'

    def __init__(self, local_dir: str):
        """
        A local API client that emulates its own API/Database. It has two main purposes:

            1. Allowing users to store data fully locally
            2.  Serving as a cache for the remote API (so the remote resources do not need to be fetched every time)

        :param local_dir: The path to a local directory that acts as a local storage
        """

        super().__init__(local_dir)
        self._local_dir = local_dir
        os.makedirs(self._local_dir,exist_ok=True)
        self._storage = LocalDBStorage(local_dir)
        engine_url = "sqlite:///%s" % os.path.join(local_dir, self._database_filename)
        self._db_engine = sqlalchemy.create_engine(engine_url)
        Base.metadata.create_all(self._db_engine, Base.metadata.tables.values(), checkfirst=True)

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

    def put_uid_annotations(self, info: AnnotType):
        info = copy.deepcopy(info)
        session = sessionmaker(bind=self._db_engine)()
        out = []
        # for each image
        for data in info:
            json_str = json.dumps(data)
            # print(json_str)
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
            del o["json"]
            out.append(o)
            session.add(annot)
            session.commit()
        return out

    def get_uid_annotations(self, info: MetadataType, what: str = 'metadata'):
        images = self.get_images(info)
        image_ids = [Images.id == img['id'] for img in images]
        session = sessionmaker(bind=self._db_engine)()
        conditions = or_(*image_ids)

        q = session.query(Images.id).filter(conditions)

        out = []
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
            i['datetime'] = string_to_datetime(i['datetime'])
        session = sessionmaker(bind=self._db_engine)()

        # we can fetch all images at once
        conditions = [and_(Images.datetime == i['datetime'], Images.device == i['device']) for i in info]
        q = session.query(Images).filter(or_(*conditions))

        for img in q:
            img_dict = img.to_dict()
            img_dict['url'] = self._storage.get_url_for_image(img, what)
            out.append(img_dict)


        #todo here, check wether requested images all exist in db. (in the case we ask for more than metadata)

        # for i in info:
        #     q = session.query(Images).filter(Images.datetime == i['datetime'], Images.device == i['device'])
        #     if q.count() == 1:
        #         img = q.one()
        #         img_dict = img.to_dict()
        #         img_dict['url'] = self._storage.get_url_for_image(img, what)
        #         out.append(img_dict)
        #
        #     elif q.count() > 1:
        #         raise Exception("more than one match for %s" % i)
        #     # warn when trying to retrieve the URL of an image that does not exist
        #     # "metadata" to be used when diffing to see if data exists in db
        #     elif what != "metadata":
        #         logging.warning("No image for %s at %s" % (i['device'], i['datetime']))

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
                                             Images.device == i['device'])

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


class RemoteClient(LocalClient):
    def __init__(self, local_dir, api_root, username, password):
        super().__init__(local_dir)
        self._username = username
        self._password = password

    def put_images(self, files):
        # first, We add data to the local DB
        super().put_images(files)
        #todo, here, send POST a request with the files

    def get_images(self, info, what='metadata'):
        # TODO first, we send a request to the server and get the image metadata (plus URL)

        # Then, we look at local images, with the same query
        local_images = super().get_images(info, what)

        # TODO we compare both sets of images, giving priority to the remote
        # We download each image that is not yet in local db
        # and we send it to the local db to retreive its local URL


