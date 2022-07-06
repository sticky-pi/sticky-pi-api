import time
import datetime
import shutil
import os
import logging
import re
import boto3
from io import BytesIO
from abc import ABC, abstractmethod
from sticky_pi_api.types import List, Dict, Union, Any
from sticky_pi_api.database.images_table import Images
from sticky_pi_api.database.tiled_tuboids_table import TiledTuboids
from sticky_pi_api.configuration import LocalAPIConf, BaseAPIConf, RemoteAPIConf
from sticky_pi_api.utils import multipart_etag


class BaseStorage(ABC):
    _multipart_chunk_size = 15 * 1024 * 1024
    _raw_images_dirname = 'raw_images'
    _ml_storage_dirname = 'ml'
    _tiled_tuboids_storage_dirname = 'tiled_tuboids'

    _tiled_tuboid_filenames = {'tuboid': 'tuboid.jpg',
                               'metadata': 'metadata.txt',
                               'context': 'context.jpg'}
    _suffix_map = {'image': '',
                   'thumbnail': '.thumbnail',
                   'thumbnail-mini': '.thumbnail-mini'}
    _allowed_ml_bundle_suffixes = ('.yaml', '.yml', 'model_final.pth', '.svg', '.jpeg', '.jpg', '.txt', '.db')
    _ml_bundle_ml_data_subdir = ('data', 'config')
    _ml_bundle_ml_model_subdir = ('output', 'config')

    def __init__(self, api_conf: BaseAPIConf, *args, **kwargs):
        self._api_conf = api_conf

    @classmethod
    def local_bundle_files_info(cls, bundle_dir, what='all',
                                ignored_dir_names=('.cache',)):
        out = []
        for root, dirs, files in os.walk(bundle_dir, topdown=True, followlinks=True):
            if os.path.basename(root) in ignored_dir_names:
                logging.info("Ignoring %s" % root)
                continue
            for name in files:
                matches = [s for s in cls._allowed_ml_bundle_suffixes if name.endswith(s)]
                if len(matches) == 0:
                    continue
                subdir = os.path.relpath(root, bundle_dir)
                in_data = subdir in cls._ml_bundle_ml_data_subdir
                in_model = subdir in cls._ml_bundle_ml_model_subdir
                path = os.path.join(root, name)
                key = os.path.relpath(path, bundle_dir)
                local_md5 = multipart_etag(path, chunk_size=cls._multipart_chunk_size)
                local_mtime = os.path.getmtime(path)
                if what == 'all' or (in_data and what == 'data') or (in_model and what == 'model'):
                    out.append({'key': key, 'path': path, 'md5': local_md5, 'mtime': local_mtime})
        return out

    @abstractmethod
    def get_ml_bundle_file_list(self, bundle_name: str, what: str = "all") -> List[Dict[str, Union[float, str]]]:
        """
        List and describes the files present in a ML bundle.

        :param bundle_name: the name of the machine learning bundle to fetch the files from
        :param what: One of {``'all'``, ``'data'``,``'model'`` }, to return all files, only the training data(training),
            or only the model (inference), respectively.
        :return: A list of dict containing the fields ``key`` and ``url`` of the files to be downloaded,
            which can be used to download the files
        """
        pass

    def get_ml_bundle_upload_links(self, bundle_name: str, info: List[Dict[str, Union[float, str]]]) -> \
            List[Dict[str, Union[float, str]]]:
        """
        Request a list of upload links to put files in a given ML bundle

        :param bundle_name:
        :param info: A list of dict containing the fields ``key``, ``md5`` ``mtime`` describing the upload candidates.
        :return: A list like ``info`` with the extra key ``url`` pointing to a destination where the file
            can be copied/posted. The list contains only files that did not exist on remote -- hence can be empty.
        """

        already_uploaded_dict = self._already_uploaded_ml_bundle_files(bundle_name)

        out = []
        for i in info:
            to_upload = False
            # file does not exists on remote
            if i['key'] not in already_uploaded_dict:
                to_upload = True
            else:
                remote_info = already_uploaded_dict[i['key']]
                if i['md5'] == remote_info['md5']:
                    to_upload = False
                elif i['mtime'] > remote_info['mtime']:
                    to_upload = True
            if to_upload:
                i['url'] = self._upload_url(os.path.join(self._ml_storage_dirname, bundle_name, i['key']))
                out.append(i)
            else:
                logging.info("Skipping %s (already on remote)" % str(i))
        return out

    @abstractmethod
    def store_image_files(self, image: Images) -> None:
        """
        Saves the files corresponding to a an image.
        Those are generally the original JPEG plus thumbnail and thumbnail-mini

        :param image: an image object
        """
        pass

    @abstractmethod
    def delete_image_files(self, image: Images) -> None:
        """
        Delete the files corresponding to an image.
        :param image: an image object
        """
        pass

    @abstractmethod
    def delete_tiled_tuboid_files(self, tuboid: TiledTuboids) -> None:
        """
        Delete the files corresponding to a tiled tuboid
        :param image: an image object
        """
        pass

    @abstractmethod
    def get_url_for_image(self, image: Union[Images, Dict], what: str = 'metadata') -> str:
        """
        Retrieves the URL to the file corresponding to an image in the database.

        :param image: an image object
        :param what:  One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail-mini'``}
        :return: a url/path as a string. For ``what='metadata'``, an empty string is returned. for consistency
        """
        pass

    @abstractmethod
    def store_tiled_tuboid(self, data: Dict[str, str]) -> None:
        pass

    @abstractmethod
    def get_urls_for_tiled_tuboids(self, data: Dict[str, str]) -> Dict[str, str]:
        pass

    @abstractmethod
    def _upload_url(self, path: str) -> str:
        """
        :param path: the path, relative to the storage root
        :return: a uri to upload content
        """
        pass

    @abstractmethod
    def _already_uploaded_ml_bundle_files(self, bundle_name: str) -> Dict[str, Any]:
        pass


class DiskStorage(BaseStorage):
    def __init__(self, api_conf: LocalAPIConf, *args, **kwargs):
        super().__init__(api_conf, *args, **kwargs)
        self._local_dir = self._api_conf.LOCAL_DIR
        assert os.path.isdir(self._local_dir)

    def _upload_url(self, path):
        return os.path.join(self._local_dir, path)

    def _already_uploaded_ml_bundle_files(self, bundle_name: str) -> Dict[str, Any]:
        bundle_dir = os.path.join(self._local_dir, self._ml_storage_dirname, bundle_name)
        already_uploaded = self.local_bundle_files_info(bundle_dir, what='all')
        already_uploaded_dict = {au['key']: au for au in already_uploaded}
        return already_uploaded_dict

    def store_tiled_tuboid(self, data: Dict[str, str]) -> None:
        tuboid_id = data['tuboid_id']
        series_id = ".".join(tuboid_id.split('.')[0: -1])  # strip out the tuboid specific part
        target_dirname = os.path.join(self._local_dir, self._tiled_tuboids_storage_dirname, series_id, tuboid_id)
        os.makedirs(target_dirname, exist_ok=True)
        for k, v in self._tiled_tuboid_filenames.items():
            assert k in data, (k, data)
            logging.debug("%s => %s" % (data[k], os.path.join(target_dirname, v)))
            shutil.copy(data[k], os.path.join(target_dirname, v))

    def get_urls_for_tiled_tuboids(self, data: Dict[str, str]) -> Dict[str, str]:
        tuboid_id = data['tuboid_id']
        series_id = ".".join(tuboid_id.split('.')[0: -1])  # strip out the tuboid specific part
        target_dirname = os.path.join(self._local_dir, self._tiled_tuboids_storage_dirname, series_id, tuboid_id)
        files_urls = {k: os.path.join(target_dirname, v) for k, v in self._tiled_tuboid_filenames.items()}
        return files_urls

    def store_image_files(self, image: Images) -> None:
        target = os.path.join(self._local_dir, self._raw_images_dirname, image.device, image.filename)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        target, thumbnail, thumb_mini = [target + self._suffix_map[s] for s in ['image', 'thumbnail', 'thumbnail-mini']]
        with open(target, 'wb') as f:
            f.write(image.file_blob)
        image.thumbnail.save(thumbnail, format='jpeg')
        image.thumbnail_mini.save(thumb_mini, format='jpeg')

    def delete_image_files(self, image: Images) -> None:
        target = os.path.join(self._local_dir, self._raw_images_dirname, image.device, image.filename)
        for s in ['image', 'thumbnail', 'thumbnail-mini']:
            to_del = target + self._suffix_map[s]
            logging.info('Removing %s' % to_del)
            os.remove(to_del)

    def delete_tiled_tuboid_files(self, tuboid: TiledTuboids) -> None:
        # name of the series
        tuboid_dirname, _ = os.path.splitext(tuboid.tuboid_id)
        target_dir = os.path.join(self._local_dir, self._tiled_tuboids_storage_dirname, tuboid_dirname,
                                  tuboid.tuboid_id)
        for k, v in self._tiled_tuboid_filenames.items():
            to_del = os.path.join(target_dir, v)
            logging.info('Removing %s' % to_del)
            os.remove(to_del)
        os.rmdir(target_dir)

    def get_url_for_image(self, image: Union[Images, Dict], what: str = 'metadata') -> str:
        if what == 'metadata':
            return ""

        url = os.path.join(self._local_dir, self._raw_images_dirname, image["device"], image["filename"])
        if what == "thumbnail":
            url += ".thumbnail"
        elif what == "thumbnail-mini":
            url += ".thumbnail-mini"
        elif what == "image":
            pass
        else:
            raise ValueError(
                "Unexpected `what` argument: %s. Should be in {'metadata', 'image', 'thumbnail', 'thumbnail-mini'}")

        return url

    def get_ml_bundle_file_list(self, bundle_name: str, what: str = "all") -> List[Dict[str, Union[float, str]]]:
        bundle_dir = os.path.join(self._local_dir, self._ml_storage_dirname, bundle_name)
        if not os.path.isdir(bundle_dir):
            logging.warning('No such ML bundle: %s' % bundle_name)
            return []
        out = self.local_bundle_files_info(bundle_dir, what)
        for o in out:
            o['url'] = o['path']
        return out

try:
    import uwsgi

    class URLCache(object):
        _cache_block_size = 128 # bytes. matche uwsgi config
        def __init__(self, expiration, name='s3_url_cache'):
            self._name = name
            self._expiration = expiration

        def __getitem__(self, item):
            out = uwsgi.cache_get(item, self._name)
            if out is not None:
                return out.decode('ascii')

        def __setitem__(self, item, value):

            assert len(value) < self._cache_block_size, f"object too large to cache: {value}"
            expire = int(self._expiration * 0.95)  # a margin to make cache expire before the link
            uwsgi.cache_update(item, value.encode('ascii'), expire, self._name)


except ImportError:
    # TODO alternative, dict base class
    pass


class S3Storage(BaseStorage):
    _expiration = 3600 * 24 * 7  # urls are valid for a week

    def __init__(self, api_conf: RemoteAPIConf, *args, **kwargs):
        super().__init__(api_conf, *args, **kwargs)

        credentials = {"aws_access_key_id": api_conf.S3_ACCESS_KEY,
                       "aws_secret_access_key": api_conf.S3_PRIVATE_KEY,
                       }
        # if "." in api_conf.S3_HOST:
        #     local_s3_resource = False
        # else:
        #     local_s3_resource = True
        #
        # if local_s3_resource:
        credentials.update({"endpoint_url": "https://%s" % api_conf.S3_HOST, "use_ssl": True})
        # else:
        #     import socket
        #     credentials.update({"endpoint_url": "http://%s" % socket.gethostbyname(api_conf.S3_HOST),
        #                         "use_ssl": False})


        self._cached_urls = URLCache(expiration=self._expiration)
        self._bucket_name = api_conf.S3_BUCKET_NAME
        self._endpoint = credentials["endpoint_url"]
        self._s3_ressource = boto3.resource('s3', **credentials)

        # fixme ensure versioning is enabled. now, hangs
        # versioning = client.BucketVersioning(self._bucket_conf['bucket'])
        # print(versioning.status())
        # versioning.enable()

    def _s3_url_prefix(self, key):
        key = key.replace(' ', '%20')
        return f"{self._endpoint}/{self._bucket_name}/{key}"

    def store_image_files(self, image: Images) -> None:
        tmp = BytesIO()
        image.thumbnail.save(tmp, format='jpeg')
        tmp_mini = BytesIO()
        image.thumbnail_mini.save(tmp_mini, format='jpeg')

        for suffix, body in zip(['', '.thumbnail', '.thumbnail-mini'],
                                [image.file_blob, tmp.getvalue(), tmp_mini.getvalue()]):
            self._s3_ressource.Object(self._bucket_name,
                                      self._image_key(image, suffix)).put(Body=body)

    def delete_image_files(self, image: Images) -> None:
        for k, v in self._suffix_map.items():
            key = self._image_key(image, v)
            logging.info('Removing %s' % key)
            self._s3_ressource.meta.client.delete_object(Bucket=self._bucket_name, Key=key)

    def delete_tiled_tuboid_files(self, tuboid: TiledTuboids) -> None:
        # name of the series
        tuboid_dirname, _ = os.path.splitext(tuboid.tuboid_id)
        target_dir = os.path.join(self._tiled_tuboids_storage_dirname, tuboid_dirname, tuboid.tuboid_id)
        for k, v in self._tiled_tuboid_filenames.items():
            to_del = os.path.join(target_dir, v)
            logging.info('Removing %s' % to_del)
            self._s3_ressource.meta.client.delete_object(Bucket=self._bucket_name, Key=to_del)

    def _image_key(self, image, suffix):
        return os.path.join(self._raw_images_dirname,
                            image["device"],
                            image["filename"] + suffix)

    def get_url_for_image(self, image: Union[Images, Dict], what: str = 'metadata') -> str:
        if what == 'metadata':
            return ""
        suffix = self._suffix_map[what]
        return self._presigned_url(self._image_key(image, suffix))

    def get_ml_bundle_file_list(self, bundle_name: str, what: str = "all") -> List[Dict[str, Union[float, str]]]:

        bucket = self._s3_ressource.Bucket(self._bucket_name)
        out = []

        bundle_dir = os.path.join(self._ml_storage_dirname, bundle_name)

        for obj in bucket.objects.filter(Prefix=bundle_dir):
            # strip the bundle dirname
            key = os.path.relpath(obj.key, bundle_dir)

            matches = [s for s in self._allowed_ml_bundle_suffixes if key.endswith(s)]

            if len(matches) == 0:
                continue
            subdir = os.path.basename(os.path.dirname(key))
            in_data = subdir in self._ml_bundle_ml_data_subdir
            in_model = subdir in self._ml_bundle_ml_model_subdir
            if what == 'all' or (in_data and what == 'data') or (in_model and what == 'model'):
                remote_md5 = obj.e_tag[1:-1]
                remote_last_modified = datetime.datetime.timestamp(obj.last_modified)
                url = self._presigned_url(obj.key)

                o = {'key': key, 'path': obj.key, 'md5': remote_md5, 'mtime': remote_last_modified,
                     'url': url}
                out.append(o)
        return out

    def _already_uploaded_ml_bundle_files(self, bundle_name: str) -> Dict[str, Dict[str, Any]]:
        bucket = self._s3_ressource.Bucket(self._bucket_name)
        already_uploaded_dict = {}
        bundle_dir = os.path.join(self._ml_storage_dirname, bundle_name)
        for obj in bucket.objects.filter(Prefix=bundle_dir + '/'):
            # strip the bundle dirname
            key = os.path.relpath(obj.key, bundle_dir)
            remote_md5 = obj.e_tag[1:-1]
            mtime = datetime.datetime.timestamp(obj.last_modified)
            already_uploaded_dict[key] = {'path': obj.key, 'md5': remote_md5, 'mtime': mtime}
        return already_uploaded_dict

    def _upload_url(self, path) -> Dict:
        out = self._s3_ressource.meta.client.generate_presigned_post(self._bucket_name,
                                                                     path,
                                                                     Fields=None,
                                                                     Conditions=None,
                                                                     ExpiresIn=self._expiration)
        return out

    def _presigned_url(self, key) -> str:
        suffix = self._cached_urls[key]

        if suffix is not None:
            out = f"{self._s3_url_prefix(key)}?{suffix}"
        else:
            out = self._s3_ressource.meta.client.generate_presigned_url('get_object',
                                                                        Params={'Bucket': self._bucket_name,
                                                                                'Key': key},
                                                                        ExpiresIn=self._expiration)
            prefix, suffix = out.split("?")
            assert prefix == self._s3_url_prefix(key), f"Wrong URL prefix: {prefix}, for key: {key}, cache will fail"
            self._cached_urls[key] = suffix  # , now + self._expiration - 60) # a minute of margin so we don't serve urls that are obsolete at reception
            # logging.warning(f"setting cache for {key}")
            assert suffix == self._cached_urls[key], f'Could not read cache for {key}'
        return out

    def store_tiled_tuboid(self, data: Dict[str, str]) -> None:
        tuboid_id = data['tuboid_id']
        series_id = ".".join(tuboid_id.split('.')[0: -1])  # strip out the tuboid specific part
        for k, v in self._tiled_tuboid_filenames.items():
            assert k in data, (k, data)
            key = os.path.join(self._tiled_tuboids_storage_dirname, series_id, tuboid_id, v)
            logging.debug("%s => %s" % (data[k], os.path.join(k, v)))
            data[k].seek(0)
            self._s3_ressource.Object(self._bucket_name,
                                      key).put(Body=data[k])

    def get_urls_for_tiled_tuboids(self, data: Dict[str, str]) -> Dict[str, str]:
        tuboid_id = data['tuboid_id']
        series_id = ".".join(tuboid_id.split('.')[0: -1])  # strip out the tuboid specific part
        target_dirname = os.path.join(self._tiled_tuboids_storage_dirname, series_id, tuboid_id)
        files_urls = {k: self._presigned_url(os.path.join(target_dirname, v)) for k, v in
                      self._tiled_tuboid_filenames.items()}
        return files_urls
