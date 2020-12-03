<<<<<<< HEAD
import logging
import requests
import tempfile
import shutil
import pandas as pd
=======
>>>>>>> 7daa60a... Revert "Feature tiled tuboids"
import os
import hashlib
<<<<<<< HEAD
import json
from decimal import Decimal
import re
import datetime
import functools
=======
>>>>>>> 7daa60a... Revert "Feature tiled tuboids"

STRING_DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
DATESTRING_REGEX=re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")

class URLOrFileOpen(object):
    def __init__(self, file_or_url, mode):
        self._file_or_url = file_or_url
        self.mode = mode
        self._tmp_dir_path = None
        self._file = None

    def __enter__(self):
        if not os.path.isfile(self._file_or_url):
            resp = requests.get(self._file_or_url, allow_redirects=True)
            self._tmp_dir_path = tempfile.mkdtemp(prefix='sticky-pi-')
            file_name = os.path.basename(self._file_or_url).split('?')[0]
            self._file_or_url = os.path.join(self._tmp_dir_path, file_name)
            with open(self._file_or_url, 'wb') as f:
                f.write(resp.content)

        self._file = open(self._file_or_url, self.mode)
        return self._file

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self._file:
            self._file.close()
        if self._tmp_dir_path:
            shutil.rmtree(self._tmp_dir_path)


<<<<<<< HEAD
def chunker(seq, size: int):
    """
    Breaks an interable into a list of smaller chunks of size ``size`` (or less for the last chunk)

    :param seq: an iterable
    :param size: the size of the chunk
    :return:
    """
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def json_io_converter(o):
    if isinstance(o, datetime.datetime):
        if o:
            return datetime_to_string(o)
        else:
            return None
    elif isinstance(o, Decimal):
        return float(o)
    elif hasattr(o, 'read'):
        return o
    else:
        raise Exception('Un-parsable json object: %s' % o)


def json_out_parser(o):
    for k, v in o.items():
        if isinstance(v, str) and DATESTRING_REGEX.search(v):
            o[k] = string_to_datetime(o[k])
    return o


# def format_io(func):
#     @functools.wraps(func)
#     def _format_input_output(self, *args, **kwargs):
#         formated_a = []
#         for a in args:
#             json_a = json.dumps(a, default=json_io_converter)
#             a = json.loads(json_a, object_hook=json_out_parser)
#             formated_a.append(a)
#
#         formated_k = {}
#         for k, v in kwargs.items():
#             json_v = json.dumps(v, default=json_io_converter)
#             v = json.loads(json_v, object_hook=json_out_parser)
#             formated_k[k] = v
#
#         out = func(self, *formated_a, **formated_k)
#         logging.warning('out')
#         logging.warning(out)
#         return out
#     return _format_input_output


def json_inputs_to_python(func):
    @functools.wraps(func)
    def _json_inputs_to_python(self, *args, **kwargs):
        formated_a = []
        for a in args:
            json_a = json.dumps(a, default=json_io_converter)
            a = json.loads(json_a, object_hook=json_out_parser)
            formated_a.append(a)

        formated_k = {}
        for k, v in kwargs.items():
            json_v = json.dumps(v, default=json_io_converter)
            v = json.loads(json_v, object_hook=json_out_parser)
            formated_k[k] = v

        out = func(self, *formated_a, **formated_k)
        # it it the responsibility of the serializer to then encode to json, on the remote api
        return out
    return _json_inputs_to_python


def python_inputs_to_json(func):
    @functools.wraps(func)
    def _python_inputs_to_json(self, *args, **kwargs):
        formated_a = []
        for a in args:
            json_a = json.dumps(a, default=json_io_converter)
            a = json.loads(json_a)
            formated_a.append(a)

        formated_k = {}
        for k, v in kwargs.items():
            json_v = json.dumps(v, default=json_io_converter)
            v = json.loads(json_v)
            formated_k[k] = v

        out = func(self, *formated_a, **formated_k)
        # it it the responsibility of the serializer to then decode to json, on the remote client
        return out
    return _python_inputs_to_json



=======
>>>>>>> 7daa60a... Revert "Feature tiled tuboids"
def md5(file, chunk_size=32768):
    # if the file is a path, open and recurse
    if type(file) == str:
        with open(file, 'rb') as f:
            return md5(f)
    try:
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: file.read(chunk_size), b""):
            hash_md5.update(chunk)
    finally:
        file.seek(0)
    return hash_md5.hexdigest()


def multipart_etag(file, chunk_size):
    if type(file) == str:
        with open(file, 'rb') as f:
            return multipart_etag(f, chunk_size)
    file.seek(0)
    md5s = []
    while True:
        data = file.read(chunk_size)

        if not data:
            break
        md5s.append(hashlib.md5(data))

    if len(md5s) > 1:
        digests = b"".join(m.digest() for m in md5s)
        new_md5 = hashlib.md5(digests)
        new_etag = '%s-%s' % (new_md5.hexdigest(), len(md5s))
    elif len(md5s) == 1:  # file smaller than chunk size
        new_etag = '%s' % md5s[0].hexdigest()
    else:  # empty file
        new_etag = ''

    file.seek(0)
    return new_etag

def string_to_datetime(string):
    return datetime.datetime.strptime(string, STRING_DATETIME_FORMAT)


def datetime_to_string(dt):
    return datetime.datetime.strftime(dt, STRING_DATETIME_FORMAT)


<<<<<<< HEAD
=======
def local_bundle_files_info(bundle_dir, what='all',
                            allowed_ml_bundle_suffixes=('.yaml', '.yml', 'model_final.pth', '.svg', '.jpeg', '.jpg'),
                            ml_bundle_ml_data_subdir=('data', 'config'),
                            ml_bundle_ml_model_subdir=('output', 'config'),
                            multipart_chunk_size = 8 * 1024 * 1024):
    out = []
    for root, dirs, files in os.walk(bundle_dir, topdown=True, followlinks=True):
        for name in files:
            matches = [s for s in allowed_ml_bundle_suffixes if name.endswith(s)]
            if len(matches) == 0:
                continue
            subdir = os.path.relpath(root, bundle_dir)
            in_data = subdir in ml_bundle_ml_data_subdir
            in_model = subdir in ml_bundle_ml_model_subdir

            path = os.path.join(root, name)
            key = os.path.relpath(path, bundle_dir)
            local_md5 = multipart_etag(path, chunk_size=multipart_chunk_size)
            local_mtime = os.path.getmtime(path)
            if what == 'all' or (in_data and what == 'data') or (in_model and what == 'model'):
                out.append({'key': key, 'path': path, 'md5': local_md5, 'mtime': local_mtime})
    return out
>>>>>>> 7daa60a... Revert "Feature tiled tuboids"
