import logging
import os
from sticky_pi_client.database.images_table import Images
from sticky_pi_client.utils import local_bundle_files_info
from typing import List, Dict, Union


class BaseStorage(object):
    def __init__(self, *args, **kwargs):
        pass

    def get_ml_bundle_file_list(self, bundle_name: str, what: str = "all") -> List[Dict[str, Union[float, str]]]:
        """
        Download locally the content of an `ML bundle'.
        A ML bundle contains files necessary to train and run a ML training/inference (data, configs and model).

        :param bundle_name: the name of the machine learning buncle to fetch the files from
        :param what: One of {``'all'``, ``'data'``,``'model'`` }, to return all files, only the training data(training),
        or only the model (inference), respectively.
        :return: A list of dict containing the fields ``key`` and ``url`` of the files to be downloaded,
         which can be used to download the files
        """
        raise NotImplementedError()

    def get_ml_bundle_upload_links(self, bundle_name: str, info: List[Dict[str, Union[float, str]]]) -> \
            List[Dict[str, Union[float, str]]]:
        raise NotImplementedError()

    def store_image_files(self, image: Images) -> None:
        raise NotImplementedError()

    def get_url_for_image(self, image: Images, what: str = 'metadata') -> str:
        raise NotImplementedError()


class DiskStorage(BaseStorage):
    _raw_images_dirname = 'raw_images'
    _ml_storage_dirname = 'ml'

    def __init__(self, local_dir: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert os.path.isdir(local_dir)
        self._local_dir = local_dir

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


#todo
# class S3Storage(BaseStorage):
#     pass