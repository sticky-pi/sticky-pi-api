"""
Main module of the client. Implements classes to interact with the API.
"""

import time
import logging
import os
from abc import ABC, abstractmethod
import pandas as pd
import shutil
from joblib import Parallel, delayed
import inspect
import shelve
import requests
from typing import Any
import json
from decorate_all_methods import decorate_all_methods
from sticky_pi_api.image_parser import ImageParser
from sticky_pi_api.utils import datetime_to_string, chunker, python_inputs_to_json, json_out_parser
from sticky_pi_api.storage import BaseStorage
from sticky_pi_api.types import List, Dict, Union, InfoType, MetadataType, AnnotType
from sticky_pi_api.specifications import LocalAPI, BaseAPISpec
from sticky_pi_api.configuration import LocalAPIConf


class Cache(dict):
    _sync_each_n = 1024

    def __init__(self, path: str):
        super().__init__()
        self._path = path
        self._n_writes = 0
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.isfile(path):
            with shelve.open(path, flag='r') as d:
                for k, v in d.items():
                    self[k] = v

    def add(self, function, results):
        if len(results) == 0:
            return
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



# all the client methods may take python argument, the argument are implicitly transformed
# to json-compatible values using this decorator


@decorate_all_methods(python_inputs_to_json, exclude=['__init__', '_diff_images_to_upload'])
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
        # info = [{k: v for k, v in p.items() if k in {"device", 'datetime'}} for p in parent_images]

        parent_images = pd.DataFrame(parent_images)

        annots = self.get_uid_annotations_series(info, what=what_annotation)

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
            out = pd.merge(tiled_tuboids, itc_labels, how='left', left_on=['id'],
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

    def put_tiled_tuboids(self, tuboid_directories: List[str], series_info: Dict[str, Any]):

        def parse_tuboid_dir(directory):
            dirname = os.path.basename(os.path.normpath(directory))

            metadata_file = os.path.join(directory, 'metadata.txt')
            tuboid_file = os.path.join(directory, 'tuboid.jpg')
            context_file = os.path.join(directory, 'context.jpg')
            assert len(dirname.split('.')) == 5  # 5 fields in this dir
            assert os.path.isfile(metadata_file)
            assert os.path.isfile(context_file)
            assert os.path.isfile(tuboid_file)
            assert all([k in series_info.keys() for k in ('algo_name', 'algo_version', 'start_datetime', 'end_datetime', 'device', 'n_images', )])

            return {'tuboid_id': dirname,
                    'series_info': series_info,
                    'metadata': metadata_file,
                    'tuboid': tuboid_file,
                    'context': context_file}
        out = []
        for i, group in enumerate(chunker(tuboid_directories, self._put_chunk_size)):
            to_upload = [parse_tuboid_dir(g) for g in group]
            logging.info("Putting tuboids... Uploading files %i-%i / %i" % (i*self._put_chunk_size,
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


        def local_img_stats(file: str, file_stats: float):
            i = ImageParser(file)
            out_ = {(file, file_stats):
                            {'device': i['device'],
                            'datetime': i['datetime'],
                            'md5': i['md5'],
                            'url': file}}
            return out_

        # we can compute the stats in parallel
        cached_results = []
        to_compute = []

        for f in files:
            key = f, os.path.getmtime(f)
            try:
                res = {key: self._cache.get_cached(local_img_stats, key)}
                cached_results.append(res)
            except KeyError as e:
                to_compute.append(key)

        if self._n_threads > 1:
            computed = Parallel(n_jobs=self._n_threads)(delayed(local_img_stats)(*tc) for tc in to_compute)
        else:
            computed = [local_img_stats(*tc) for tc in to_compute]

        logging.info('Caching %i image stats (%i already pre-computed)' % (len(computed), len(cached_results)))

        self._cache.add(local_img_stats, computed)

        computed += cached_results

        # we request these images from the database
        info = [list(imd.values())[0] for imd in computed]
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
        local_files = BaseStorage.local_bundle_files_info(bundle_dir, what)
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
                files_to_download.append(r)
            else:
                logging.info("Skipping %s (already on local)" % str(r['key']))

        for f in files_to_download:
            self._get_ml_bundle_file(f['url'], os.path.join(bundle_dir, f['key']))
            os.utime(os.path.join(bundle_dir, f['key']), (time.time(), f['mtime']))

        return files_to_download

    def put_ml_bundle_dir(self, bundle_name: str, bundle_dir: str, what: str = 'all') -> List[Dict[str, Union[float, str]]]:
        # bundle_name = os.path.basename(os.path.normpath(bundle_dir))
        files_to_upload = BaseStorage.local_bundle_files_info(bundle_dir, what)
        for f in files_to_upload:
            f['bundle_name'] = bundle_name
        files_to_upload = self._get_ml_bundle_upload_links(files_to_upload)

        for f in files_to_upload:
            if f['url'] is not None:
                self._put_ml_bundle_file(f['path'], f['url'])
        return files_to_upload

    @abstractmethod
    def _put_ml_bundle_file(self, path: str, url: str):
        pass

    @abstractmethod
    def _get_ml_bundle_file(self, url: str, target: str):
        pass

    @abstractmethod
    def _put_new_images(self, files: List[str], client_info: Dict[str, Any] = None) -> MetadataType:
        pass


@decorate_all_methods(python_inputs_to_json, exclude=['__init__'])
class LocalClient(LocalAPI, BaseClient):
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


class RemoteAPIException(Exception):
    pass


# all the client methods may take python argument, the argument are implicitly transformed
# to json-compatible values using this decorator
@decorate_all_methods(python_inputs_to_json, exclude=['__init__', '_default_client_to_api'])
class RemoteAPIConnector(BaseAPISpec):
    _max_retry_attempts = 5
    _sleep_time_between_attempts = 1

    def __init__(self, host: str, username: str, password: str, protocol: str = 'https', port: int = 443):
        self._host = host
        self._username = username
        self._password = password
        self._protocol = protocol
        self._port = int(port)
        self._token = {'token': None, 'expiration': 0}

    def _default_client_to_api(self, entry_point, info=None, what: str = None, files=None, attempt=0):

        if entry_point != 'get_token':
            if self._token['expiration'] < int(time.time()) + 60:  # we add 60s just to be sure
                self._token = self.get_token()
            auth = self._token['token'], ''
        else:
            auth = self._username, self._password

        url = "%s://%s:%i/%s" % (self._protocol, self._host, self._port, entry_point)
        if what is not None:
            url += "/" + what
        logging.debug('Requesting %s' % url)
        response = requests.post(url, json=info, files=files, auth=auth)
        if response.status_code == 200:
            return response.json(object_hook=json_out_parser)
        else:

            if attempt >= self._max_retry_attempts:
                logging.error("Failed to request url: %s" % url)
                raise RemoteAPIException(response.content)
            else:
                time.sleep(self._sleep_time_between_attempts)
                attempt += 1
                logging.warning("Failed to request url: %s. Retrying... Attempt %i" % (url, attempt))
                self._default_client_to_api(entry_point, info, what, files, attempt)

    def get_token(self, client_info: Dict[str, Any] = None) -> str:
        return self._default_client_to_api('get_token', info=None)

    def _put_new_images(self, files: List[str], client_info: Dict[str, Any] = None) -> MetadataType:
        out = []
        for file in files:
            with open(file, 'rb') as f:
                payload = {os.path.basename(file): f}
                out += self._default_client_to_api('_put_new_images', files=payload)
        return out

    # custom handling of file objects to upload
    def get_users(self, info: List[Dict[str, str]] = None, client_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return self._default_client_to_api('get_users', info)

    def put_users(self, info: List[Dict[str, Any]], client_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return self._default_client_to_api('put_users', info)

    def get_images(self, info: InfoType, what: str = 'metadata', client_info: Dict[str, Any] = None) -> MetadataType:
        return self._default_client_to_api('get_images', info, what=what)

    def get_image_series(self, info, what: str = 'metadata', client_info: Dict[str, Any] = None) -> MetadataType:
        return self._default_client_to_api('get_image_series', info, what=what)

    def delete_images(self, info: InfoType, client_info: Dict[str, Any] = None) -> MetadataType:
        return self._default_client_to_api('delete_images', info)

    def delete_tiled_tuboids(self, info: InfoType, client_info: Dict[str, Any] = None) -> MetadataType:
        return self._default_client_to_api('delete_tiled_tuboids', info)

    def put_uid_annotations(self, info: AnnotType, client_info: Dict[str, Any] = None) -> MetadataType:
        return self._default_client_to_api('put_uid_annotations', info)

    def get_uid_annotations(self, info: InfoType, what: str = 'metadata', client_info: Dict[str, Any] = None) -> MetadataType:
        return self._default_client_to_api('get_uid_annotations', info, what=what)

    def get_uid_annotations_series(self, info: InfoType, what: str = 'metadata', client_info: Dict[str, Any] = None) -> MetadataType:
        return self._default_client_to_api('get_uid_annotations_series', info, what=what)

    def get_tiled_tuboid_series(self, info: InfoType, what: str = "metadata", client_info: Dict[str, Any] = None) \
            -> MetadataType:
        return self._default_client_to_api('get_tiled_tuboid_series', info=info, what=what)


    def _put_tiled_tuboids(self, files: List[Dict[str, str]], client_info: Dict[str, Any] = None) -> MetadataType:
        out = []
        for dic in files:
            # data = {'tuboid_id': dic.pop('tuboid_id')}

            with open(dic['metadata'], 'r') as m, open(dic['tuboid'], 'rb') as t, open(dic['context'], 'rb') as c:
                payload = {'metadata': ('metadata.txt', m,  'application/text'),
                           'tuboid': ('tuboid.jpg', t,  'application/octet-stream'),
                           'context': ('context.jpg', c,  'application/octet-stream'),
                           'tuboid_id': ('tuboid_id', json.dumps(dic['tuboid_id']), 'application/json'),
                           'series_info': ('series_info', json.dumps(dic['series_info']), 'application/json'),
                           }
                out += self._default_client_to_api('_put_tiled_tuboids', files=payload, info=None)
        return out

    def _get_itc_labels(self, info: List[Dict], client_info: Dict[str, Any] = None) -> MetadataType:
        return self._default_client_to_api('_get_itc_labels', info)

    def put_itc_labels(self, info: List[Dict[str, Union[str, int]]], client_info: Dict[str, Any] = None) -> MetadataType:
        return self._default_client_to_api('put_itc_labels', info)

    def _get_ml_bundle_file_list(self, info: str, what: str = "all", client_info: Dict[str, Any] = None) -> List[Dict[str, Union[float, str]]]:
        return self._default_client_to_api('_get_ml_bundle_file_list', info, what=what)

    def _get_ml_bundle_upload_links(self,  info: List[Dict[str, Union[float, str]]], client_info: Dict[str, Any] = None) -> \
            List[Dict[str, Union[float, str]]]:
        return self._default_client_to_api('_get_ml_bundle_upload_links', info)


@decorate_all_methods(python_inputs_to_json, exclude=['__init__'])
class RemoteClient(RemoteAPIConnector, BaseClient):
    def __init__(self, local_dir: str, host, username, password, protocol: str = 'https', port: int = 443,  n_threads: int = 8):
        BaseClient.__init__(self, local_dir=local_dir, n_threads=n_threads)
        RemoteAPIConnector.__init__(self, host, username, password, protocol, port)

    def _put_ml_bundle_file(self, path: str, url: Union[str, Dict]):
        #fixme,  name this is actually not a url here, but a json str => dict
        response = url
        object_name = os.path.basename(path)
        logging.info("%s => %s" % (os.path.basename(path), response['fields']['key']))
        with open(path, 'rb') as f:
            files = {'file': (object_name, f)}
            http_response = requests.post(response['url'], data=response['fields'], files=files)
        assert http_response.status_code == 204, response

    def _get_ml_bundle_file(self, url: str, target: str):

        dirname = os.path.dirname(target)
        if not os.path.isdir(dirname):
            os.makedirs(dirname, exist_ok=True)

        with open(target, 'wb') as data:
            logging.info("%s => %s" % (url, target))
            r = requests.get(url)
            data.write(r.content)
        assert os.path.isfile(target), 'File not writen!'

