import copy
import logging
import os
import pandas as pd
import sqlalchemy

from sqlalchemy.orm import sessionmaker
from sticky_pi_client.utils import string_to_datetime
from sticky_pi_client.database.utils import Base
from sticky_pi_client.database.images_table import Images
from sticky_pi_client.storage import LocalDBStorage


class BaseClient(object):
    _put_chunk_size = 50


    def __init__(self):
        """
        Abstract class that defines the methods of the client.
        """
        pass

    def get_images(self, info, what='metadata'):
        """
        :param info: A list of dict with keys: 'device' and 'datetime'
        :type info: List(Dict())
        :param what: The nature of the object to retrieve. One of {'metadata','image','thumbnail','thumbnail_mini'}.
        what only impact the "url" fields of the result. In the case of 'metadata', "url"="".
        Otherwise, it contains a string that point to the location of the requested object
        :type what: str
        :return: A list of dictionaries with one element for each queried value. Each dictionary contains
        the fields present in the underlying database plus a url fields to retrieve the actual image.
        :rtype: List(Dict())
        """
        raise NotImplemented()

    def put_images(self, files):
        raise NotImplemented()

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
        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        to_upload = []
        for group in chunker(files, self._put_chunk_size):
            img_dicts = []
            # we prepare a dict of images key for each chunk
            for f in group:
                im = Images(f)
                i = im.to_dict()
                img_dicts.append({'device': i['device'],
                                  'datetime': i['datetime'],
                                  'md5': i['md5'],
                                  'url': f})

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
            to_upload += joined[joined.already_on_db == False].url.tolist()

        # fixme. warn/prompt which has a different md5 (and match md5 is not NA)
        return to_upload


class LocalClient(BaseClient):
    _database_filename = 'database.db'

    def __init__(self, local_dir):
        self._local_dir = local_dir
        self._storage = LocalDBStorage(local_dir)
        engine_url = "sqlite:///%s" % os.path.join(local_dir, self._database_filename)
        self._db_engine = sqlalchemy.create_engine(engine_url)
        Base.metadata.create_all(self._db_engine, Base.metadata.tables.values(), checkfirst=True)

    def put_images(self, files):
        # we fist look which images are to be uploaded
        files = self._diff_images_to_upload(files)
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

    def get_images(self, info, what='metadata'):
        session = sessionmaker(bind=self._db_engine)()
        out = []

        info = copy.deepcopy(info)
        for i in info:
            i['datetime'] = string_to_datetime(i['datetime'])

        for i in info:
            q = session.query(Images).filter_by(datetime=i['datetime'], device=i['device'])
            if q.count() == 1:
                img = q.one()
                img_dict = img.to_dict()
                img_dict['url'] = self._storage.get_url_for_image(img, what)
                out.append(img_dict)

            elif q.count() > 1:
                raise Exception("more than one match for %s" % i)
            # warn when trying to retrieve the URL of an image that does not exist
            # "metadata" to be used when diffing to see if data exists in db
            elif what != "metadata":
                logging.warning("No image for %s at %s" % (i['device'], i['datetime']))

        return out



    def get_image_series(self, info, what='metadata'):
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

