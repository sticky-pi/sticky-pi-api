import os
import datetime
import hashlib

STRING_DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'


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
