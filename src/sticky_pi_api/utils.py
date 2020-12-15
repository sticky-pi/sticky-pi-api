import pandas as pd
import logging
import os
import datetime
import hashlib
import json
from decimal import Decimal
import re
import datetime

STRING_DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'


def chunker(seq, size: int):
    """
    Breaks an interable into a list of smaller chunks of size ``size`` (or less for the last chunk)

    :param seq: an iterable
    :param size: the size of the chunk
    :return:
    """
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def format_io(func):
    def io_converter(o):
        if isinstance(o, datetime.datetime):
            if o:
                return datetime_to_string(o)
            else:
                return None
        elif isinstance(o, Decimal):
            return float(o)
        else:
            raise Exception('Un-parsable json object')

    def out_parser(o):
        for k, v in o.items():
            if isinstance(v, str) and re.search(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$", v):
                o[k] = string_to_datetime(o[k])

        return o

    def _format_input_output(self, *args, **kwargs):
        formated_a = []
        for a in args:
            json_a = json.dumps(a, default=io_converter)
            a = json.loads(json_a)
            formated_a.append(a)

        formated_k = {}
        for k, v in kwargs.items():
            json_v = json.dumps(v, default=io_converter)
            v = json.loads(json_v)
            formated_k[k] = v

        out = func(self, *formated_a, **formated_k)
        json_out = json.dumps(out, default=io_converter)
        out = json.loads(json_out, object_hook=out_parser)
        return out

    return _format_input_output


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
    if pd.isnull(dt):
        return None
    return datetime.datetime.strftime(dt, STRING_DATETIME_FORMAT)


def local_bundle_files_info(bundle_dir, what='all',
                            allowed_ml_bundle_suffixes=('.yaml', '.yml', 'model_final.pth', '.svg', '.jpeg', '.jpg'),
                            ml_bundle_ml_data_subdir=('data', 'config'),
                            ml_bundle_ml_model_subdir=('output', 'config'),
                            multipart_chunk_size = 8 * 1024 * 1024,
                            ignored_dir_names=('.cache', )):
    out = []

    for root, dirs, files in os.walk(bundle_dir, topdown=True, followlinks=True):
        if os.path.basename(root) in ignored_dir_names:
            logging.info("Ignoring %s" % root)
            continue
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
