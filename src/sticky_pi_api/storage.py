import shutil
import os
import logging
from sticky_pi_api.types import List, Dict, Union
from sticky_pi_api.database.images_table import Images
from sticky_pi_api.utils import local_bundle_files_info
from sticky_pi_api.configuration import LocalAPIConf, BaseAPIConf, RemoteAPIConf
from abc import ABC
import boto3
from io import BytesIO


class BaseStorage(ABC):
    _raw_images_dirname = 'raw_images'
    _ml_storage_dirname = 'ml'
    _tiled_tuboids_storage_dirname = 'tiled_tuboids'


    _tiled_tuboid_filenames = {'tuboid': 'tuboid.jpg',
                                    'metadata': 'metadata.txt',
                                    'context': 'context.jpg'}

    def __init__(self, api_conf: BaseAPIConf, *args, **kwargs):
        self._api_conf = api_conf

    def get_ml_bundle_file_list(self, bundle_name: str, what: str = "all") -> List[Dict[str, Union[float, str]]]:
        """
        List and describes the files present in a ML bundle.

        :param bundle_name: the name of the machine learning bundle to fetch the files from
        :param what: One of {``'all'``, ``'data'``,``'model'`` }, to return all files, only the training data(training),
            or only the model (inference), respectively.
        :return: A list of dict containing the fields ``key`` and ``url`` of the files to be downloaded,
            which can be used to download the files
        """
        raise NotImplementedError()

    def get_ml_bundle_upload_links(self, bundle_name: str, info: List[Dict[str, Union[float, str]]]) -> \
            List[Dict[str, Union[float, str]]]:
        """
        Request a list of upload links to put files in a given ML bundle

        :param bundle_name:
        :param info: A list of dict containing the fields ``key``, ``md5`` ``mtime`` describing the upload candidates.
        :return: A list like ``info`` with the extra key ``url`` pointing to a destination where the file
            can be copied/posted. The list contains only files that did not exist on remote -- hence can be empty.
        """
        raise NotImplementedError()

    def store_image_files(self, image: Images) -> None:
        """
        Saves the files corresponding to a an image.
        Those are generally the original JPEG plus thumbnail and thumbnail-mini

        :param image: an image object
        """
        raise NotImplementedError()

    def get_url_for_image(self, image: Images, what: str = 'metadata') -> str:
        """
        Retrieves the URL to the file corresponding to an image in the database.

        :param image: an image object
        :param what:  One of {``'metadata'``, ``'image'``, ``'thumbnail'``, ``'thumbnail_mini'``}
        :return: a url/path as a string. For ``what='metadata'``, an empty string is returned. for consistency
        """
        raise NotImplementedError()

    def store_tiled_tuboid(self, data: Dict[str, str]) -> None:
        raise NotImplementedError()

    def get_urls_for_tiled_tuboids(self, data: Dict[str, str]) -> Dict[str, str]:
        raise NotImplementedError()

class DiskStorage(BaseStorage):
    def __init__(self, api_conf: LocalAPIConf,  *args, **kwargs):
        super().__init__(api_conf, *args, **kwargs)
        self._local_dir = self._api_conf.LOCAL_DIR
        assert os.path.isdir(self._local_dir)

    def store_tiled_tuboid(self, data: Dict[str, str]) -> None:
        tuboid_id = data['tuboid_id']
        series_id = ".".join(tuboid_id.split('.')[0: -1]) # strip the tuboid specific part
        target_dirname = os.path.join(self._local_dir, self._tiled_tuboids_storage_dirname, series_id, tuboid_id)
        os.makedirs(target_dirname, exist_ok=True)
        for k, v in self._tiled_tuboid_filenames.items():
            assert k in data, (k, data)
            logging.debug("%s => %s" % (data[k], os.path.join(target_dirname, v)))
            shutil.copy(data[k], os.path.join(target_dirname, v))

    def get_urls_for_tiled_tuboids(self, data: Dict[str, str]) -> Dict[str, str]:
        tuboid_id = data['tuboid_id']
        series_id = ".".join(tuboid_id.split('.')[0: -1])  # strip the tuboid specific part
        target_dirname = os.path.join(self._local_dir, self._tiled_tuboids_storage_dirname, series_id, tuboid_id)
        files_urls = {k: os.path.join(target_dirname, v) for k, v in self._tiled_tuboid_filenames.items()}
        return files_urls

    def store_image_files(self, image: Images) -> None:
        target = os.path.join(self._local_dir, self._raw_images_dirname, image.device, image.filename)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(image.file_blob)
        image.thumbnail.save(target + ".thumbnail", format='jpeg')
        image.thumbnail_mini.save(target + ".thumbnail_mini", format='jpeg')

    def get_url_for_image(self, image: Images, what: str = 'metadata') -> str:
        if what == 'metadata':
            return ""

        url = os.path.join(self._local_dir, self._raw_images_dirname, image.device, image.filename)
        if what == "thumbnail":
            url += ".thumbnail"
        elif what == "thumbnail_mini":
            url += ".thumbnail_mini"
        elif what == "image":
            pass
        else:
            raise ValueError("Unexpected `what` argument: %s. Should be in {'metadata', 'image', 'thumbnail', 'thumbnail_mini'}")

        return url

    def get_ml_bundle_file_list(self, bundle_name: str, what: str = "all") -> List[Dict[str, Union[float, str]]]:
        bundle_dir = os.path.join(self._local_dir, self._ml_storage_dirname, bundle_name)
        if not os.path.isdir(bundle_dir):
            logging.warning('No such ML bundle: %s' % bundle_name)
            return []
        out = local_bundle_files_info(bundle_dir, what)
        for o in out:
            o['url'] = o['path']
        return out

    def get_ml_bundle_upload_links(self, bundle_name: str, info: List[Dict[str, Union[float, str]]]) -> \
            List[Dict[str, Union[float, str]]]:
        bundle_dir = os.path.join(self._local_dir, self._ml_storage_dirname, bundle_name)

        already_uploaded = local_bundle_files_info(bundle_dir, what='all')
        already_uploaded_dict = {au['key']: au for au in already_uploaded}
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
                i['url'] = os.path.join(self._local_dir, self._ml_storage_dirname, bundle_name, i['key'])
                out.append(i)
            else:
                logging.info("Skipping %s (already on remote)" % str(i))
        return out


class S3Storage(BaseStorage):
    _multipart_chunk_size = 8 * 1024 * 1024

    def __init__(self, api_conf: RemoteAPIConf,  *args, **kwargs):
        super().__init__(api_conf, *args, **kwargs)
        credentials = {"aws_access_key_id": api_conf.S3_ACCESS_KEY,
                       "aws_secret_access_key": api_conf.S3_PRIVATE_KEY,
                       "endpoint_url": "http://%s" % api_conf.S3_HOST,
                       }
        self._bucket_name = api_conf.S3_BUCKET_NAME
        self._s3_client = boto3.resource('s3', **credentials)

    def store_image_files(self, image: Images) -> None:
        tmp = BytesIO()
        image.thumbnail.save(tmp, format='jpeg')
        tmp_mini = BytesIO()
        image.thumbnail_mini.save(tmp_mini, format='jpeg')
        self._s3_client.Bucket()
        self._s3_client.Object(self._bucket_name,
                               os.path.join(self._raw_images_dirname,
                                            image.device,
                                            image.filename)).put(Body=image.file_blob)
        self._s3_client.Object(self._bucket_name,
                               os.path.join(self._raw_images_dirname,
                                            image.device,
                                            image.filename + '.thumbnail')).put(Body=tmp.getvalue())
        self._s3_client.Object(self._bucket_name,
                               os.path.join(self._raw_images_dirname,
                                            image.device,
                                            image.filename + '.thumbnail_mini')).put(Body=tmp_mini.getvalue())

    def get_url_for_image(self, image: Images, what: str = 'metadata') -> str:
        return "see https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html"

        # target = os.path.join(self._local_dir, self._raw_images_dirname, image.device, image.filename)
        # os.makedirs(os.path.dirname(target), exist_ok=True)
        # with open(target, 'wb') as f:
        #     f.write(image.file_blob)
        # image.thumbnail.save(target + ".thumbnail", format='jpeg')
        # image.thumbnail_mini.save(target + ".thumbnail_mini", format='jpeg')

# self._bucket_conf = {
#             "S3BUCKET_PRIVATE_KEY": os.environ.get("S3BUCKET_PRIVATE_KEY"),
#             "S3BUCKET_ACCESS_KEY": os.environ.get("S3BUCKET_ACCESS_KEY"),
#             "bucket": name,
#             "S3BUCKET_HOST": os.environ.get("S3BUCKET_HOST")
#         }
