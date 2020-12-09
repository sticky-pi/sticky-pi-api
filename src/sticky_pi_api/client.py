"""
Main module of the client. Implements classes to interact with the API.
"""

import logging
import os
from abc import ABC
import pandas as pd
import shutil
from joblib import Memory, Parallel, delayed
from sticky_pi_api.image_parser import ImageParser
from sticky_pi_api.utils import datetime_to_string, local_bundle_files_info, chunker, format_io
from sticky_pi_api.types import List, Dict, Union, InfoType, MetadataType
from sticky_pi_api.specifications import LocalAPI, BaseAPISpec
from sticky_pi_api.configuration import LocalAPIConf
from decorate_all_methods import decorate_all_methods
import inspect
import shelve
import dbm


class Cache(dict):
    _sync_each_n = 128

    def __init__(self, path: str):
        super().__init__()
        self._path = path
        self._n_writes = 0
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with shelve.open(path) as d:
            for k, v in d.items():
                self[k] = v

    def add(self, function, results):
        key = inspect.getsource(function)
        if key not in self.keys():
            self[key] = {}
        for r in results:
            self[key].update(r)

        if self._n_writes % self._sync_each_n == self._sync_each_n - 1:
            self._sync()
        self._n_writes += 1

    def get_cached(self, function, hash):
        key = inspect.getsource(function)
        return self[key][hash]

    def _sync(self):
        with shelve.open(self._path, writeback=True) as d:
            for k, v in self.items():
                d[k] = v

    def delete(self):
        try:
            os.remove(self._path)
        except FileExistsError:
            logging.error('trying to detect cache, but file does not exist')


@decorate_all_methods(format_io, exclude=['__init__'])
class BaseClient(BaseAPISpec, ABC):
    _put_chunk_size = 16  # number of images to handle at the same time during upload
    _cache_dirname = "cache"

    def __init__(self, local_dir: str, n_threads: int = 8):
        """
        Abstract class that defines the methods of the client (common between remote and client).

        :param local_dir: The path to a client directory that acts as a client storage
        :param n_threads: The number of parallel threads to use to compute statistics on the image (md5 and such)
        """

        self._local_dir = local_dir
        self._n_threads = n_threads
        self._local_dir = local_dir
        os.makedirs(self._local_dir, exist_ok=True)
        cache_file = os.path.join(local_dir, self._cache_dirname, 'cache.pkl')
        self._cache = Cache(cache_file)

    @property
    def local_dir(self):
        return self._local_dir

    def get_uid_annotations_series(self, info: InfoType, what: str = 'metadata') -> MetadataType:
        """
        Retrieves annotations for images within a given datetime range

        TODO add ref to api specs, where params hould be inherited (so we don't write twice the same doc)

        :param info: A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``
        :param what: The nature of the object to retrieve. One of {``'metadata'``, ``'data'``}.
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database table (see ``UIDAnnotations``).
            In the case of ``what='metadata'``, the field ``json=''``.
            Otherwise, it contains a json string with the actual annotation data.
        """
        # we first fetch the parent images matching a series
        parent_images = self.get_image_series(info, what="metadata")
        # we filter the metadata as only these two fields are necessary
        info = [{k: v for k, v in p.items() if k in {"device", 'datetime'}} for p in parent_images]

        return self.get_uid_annotations(info, what=what)

    def get_images_with_uid_annotations_series(self, info: InfoType, what_image: str = 'metadata', what_annotation: str = 'metadata') -> MetadataType:
        """
        Retrieves images alongside their annotations (if available)  for images from a given device and
        within a given datetime range.


        :param info: A list of dicts. each dicts has, at least, the keys:
            ``'device'``, ``'start_datetime'`` and ``'end_datetime'``
        :param what_image: The nature of the image objects to retrieve.
            One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail_mini'``}
        :param what_annotation: The nature of the object to retrieve. One of {``'metadata'``, ``'data'``}.
        :return: A list of dictionaries with one element for each queried value.
            Each dictionary contains the fields present in the underlying database tables (see ``UIDAnnotations`` and ``Images``).
        """
        # we first fetch the parent images matching a series

        parent_images = self.get_image_series(info, what=what_image)

        if len(parent_images) == 0:
            logging.warning('No image found for provided info!')
            return [{}]

        # we filter the metadata as only these two fields are necessary
        info = [{k: v for k, v in p.items() if k in {"device", 'datetime'}} for p in parent_images]

        parent_images = pd.DataFrame(parent_images)

        annots = self.get_uid_annotations(info, what=what_annotation)

        if len(annots) == 0:
            annots = pd.DataFrame([], columns=['parent_image_id'])
        else:
            annots = pd.DataFrame(annots)

        out = pd.merge(parent_images, annots, how='left', left_on=['id'], right_on=['parent_image_id'], suffixes=('', '_annot'))
        # NaN -> None
        out = out.where(pd.notnull(out), None).sort_values(['device', 'datetime'])
        out = out.to_dict(orient='records')
        return out

    def get_tiled_tuboid_series_itc_labels(self, info: InfoType, what: str = "metadata") -> MetadataType:

        tiled_tuboids = pd.DataFrame(self.get_tiled_tuboid_series(info, what))
        if len(tiled_tuboids) == 0:
            logging.warning('No tuboids found for %s' % info)
            return []

        itc_labels = pd.DataFrame(self._get_itc_labels([{'tuboid_id': i} for i in tiled_tuboids.tuboid_id]))

        if len(itc_labels) == 0:
            logging.warning('No ITC labels found for %s' % info)
            out = tiled_tuboids
        else:
            # force suffixes for ITC
            itc_labels.columns = itc_labels.columns.map(lambda x: str(x) + '_itc')
            out = pd.merge(tiled_tuboids, itc_labels, how='left', left_on=['tuboid_id'],
                       right_on=['parent_tuboid_id_itc'])

        out = out.where(pd.notnull(out), None) #.sort_values(['device', 'datetime'])
        out = out.to_dict(orient='records')
        return out


    def put_images(self, files: List[str]) -> MetadataType:
        """
        Incrementally upload a list of client files

        :param files: the paths to the client files
        :return: the data of the uploaded files, as represented in by API
        """
        # instead of dealing with images one by one, we send them by chunks
        # first find which files need to be uploaded
        to_upload = []
        chunk_size = self._put_chunk_size * self._n_threads

        for i, group in enumerate(chunker(files, chunk_size)):
            logging.info("Putting images - step 1/2 ... Computing statistics on files %i-%i / %i" % (i * chunk_size,
                                                                                         i * chunk_size + len(group),
                                                                                         len(files)))

            to_upload += self._diff_images_to_upload(group)

        if len(to_upload) == 0:
            logging.warning('No image to upload!')
        out = []
        # upload by chunks now
        for i, group in enumerate(chunker(to_upload, self._put_chunk_size)):
            logging.info("Putting images - step 2/2 ... Uploading files %i-%i / %i" % (i*self._put_chunk_size,
                                                                           i * self._put_chunk_size + len(group),
                                                                           len(to_upload)))

            out += self._put_new_images(group)
        logging.info("Putting images... Complete!")
        return out

    def put_tiled_tuboids(self, tuboid_directories: List[str]):
        def parse_tuboid_dir(directory):
            dirname = os.path.basename(os.path.normpath(directory))

            metadata_file = os.path.join(directory, 'metadata.txt')
            tuboid_file = os.path.join(directory, 'tuboid.jpg')
            context_file = os.path.join(directory, 'context.jpg')
            assert len(dirname.split('.')) == 5  # 5 fields in this dir
            assert os.path.isfile(metadata_file)
            assert os.path.isfile(context_file)
            assert os.path.isfile(tuboid_file)
            return {'tuboid_id': dirname,
                    'metadata': metadata_file,
                    'tuboid': tuboid_file,
                    'context': context_file}
        out = []
        for i, group in enumerate(chunker(tuboid_directories, self._put_chunk_size)):
            to_upload = [parse_tuboid_dir(g) for g in group]
            logging.info("Putting tuboids ... Uploading files %i-%i / %i" % (i*self._put_chunk_size,
                                                                             i * self._put_chunk_size + len(group),
                                                                             len(to_upload)))
            out += self._put_tiled_tuboids(to_upload)
        return out

    def delete_cache(self):
        self._cache.delete()

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


        def local_img_stats(file: str, file_stats: Dict, cache):
            if (file, file_stats) in cache.keys():
                try:
                    return cache.get_cached(local_img_stats, (file, file_stats))
                except KeyError:
                    pass

            i = ImageParser(file)
            out = {(file, file_stats):
                            {'device': i['device'],
                            'datetime': i['datetime'],
                            'md5': i['md5'],
                            'url': file}}
            return out

        # we can compute the stats in parallel

        if self._n_threads > 1:
            img_dicts = Parallel(n_jobs=self._n_threads)(delayed(local_img_stats)(f, os.path.getmtime(f), self._cache) for f in files)
        else:
            img_dicts = [local_img_stats(f, os.path.getmtime(f)) for f in files]

        self._cache.add(local_img_stats, img_dicts)
        # we request these images from the database
        info = [list(imd.values())[0] for imd in img_dicts]

        matches = self.get_images(info, what='metadata')

        # now we diff: we ignore images that exist on DB AND have the same md5
        # we put images that do not exist on db
        # we warn if md5s are different
        info = pd.DataFrame(info)
        matches = pd.DataFrame(matches, columns=info.columns)

        joined = pd.merge(info, matches, how='left', on = ['device', 'datetime'], suffixes=('', '_match'))
        joined['same_md5'] = joined.apply(lambda row: row.md5_match == row.md5, axis=1)
        joined['already_on_db'] = joined.apply(lambda row: not pd.isna(row.md5_match), axis=1)
        # images that re not yet on the db:
        out = joined[joined.already_on_db == False].url.tolist()

        # fixme. warn/prompt which has a different md5 (and match md5 is not NA)
        return out

    def get_ml_bundle_dir(self, bundle_name: str, bundle_dir: str, what: str) -> List[Dict[str, Union[float, str]]]:
        # bundle_name = os.path.basename(os.path.normpath(bundle_dir))
        local_files = local_bundle_files_info(bundle_dir, what)
        remote_files = self._get_ml_bundle_file_list(bundle_name, what)
        already_downloaded_dict = {au['key']: au for au in local_files}
        files_to_download = []
        for r in remote_files:
            to_download = False
            # file does not exists on remote
            if r['key'] not in already_downloaded_dict:
                to_download = True
            else:
                local_info = already_downloaded_dict[r['key']]
                if r['md5'] == local_info['md5']:
                    to_download = False
                elif r['mtime'] > local_info['mtime']:
                    to_download = True
            if to_download:
                #r['url'] = os.path.join()
                files_to_download.append(r)

            else:
                logging.info("Skipping %s (already on local)" % str(r['key']))

        for f in files_to_download:
            self._get_ml_bundle_file(f['url'], os.path.join(bundle_dir, f['key']))

        return files_to_download

    def put_ml_bundle_dir(self, bundle_name: str, bundle_dir: str, what: str = 'all') -> List[Dict[str, Union[float, str]]]:
        # bundle_name = os.path.basename(os.path.normpath(bundle_dir))
        files_to_upload = local_bundle_files_info(bundle_dir, what)
        files_to_upload = self._get_ml_bundle_upload_links(bundle_name, files_to_upload)
        for f in files_to_upload:
            if f['url'] is not None:
                self._put_ml_bundle_file(f['path'], f['url'])
        return files_to_upload

    def _put_ml_bundle_file(self, path: str, key: str):
        raise NotImplementedError()

    def _get_ml_bundle_file(self, url: str, target: str):
        raise NotImplementedError()


@decorate_all_methods(format_io, exclude=['__init__'])
class LocalClient(BaseClient, LocalAPI):
    def __init__(self, local_dir: str, n_threads: int = 8, *args, **kwargs):
        # ad hoc API config for the local API. define the local_dir variable
        api_conf = LocalAPIConf(LOCAL_DIR=local_dir)
        BaseClient.__init__(self, local_dir=local_dir, n_threads=n_threads)
        # use this config for the local/internal mock API
        LocalAPI.__init__(self, api_conf, *args, **kwargs)

    def _put_ml_bundle_file(self, path: str, url: str):
        if not os.path.isdir(os.path.dirname(url)):
            os.makedirs(os.path.dirname(url), exist_ok=True)
        logging.info("%s => %s" % (os.path.basename(path), url))
        shutil.copy(path, url)

    def _get_ml_bundle_file(self, url: str, target: str):
        if not os.path.isdir(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target), exist_ok=True)
        logging.info("%s => %s" % (url, target))
        shutil.copy(url, target)



# import requests
# class RemoteAPIConnector(BaseAPISpec):
#     # todo create init that can handle tocken/credentials
#     def _put_new_images(self, files: List[str]) -> MetadataType:
#       todo. create a request



# class RemoteClient(LocalClient, RemoteAPIConnector):
#     def _put_new_images(self, files: List[str]) -> MetadataType:
#         LocalClient._put_new_images(self, files)
#         RemoteAPIConnector._put_new_images(self, files)



