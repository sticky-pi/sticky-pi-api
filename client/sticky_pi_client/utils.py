import datetime
import hashlib

STRING_DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'


def md5(file, chunksize=32768):
    # if the file is a path, open and recurse
    if type(file) == str:
        with open(file, 'rb') as f:
            return md5(f)
    try:
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: file.read(chunksize), b""):
            hash_md5.update(chunk)
    finally:
        file.seek(0)
    return hash_md5.hexdigest()


def string_to_datetime(string):
    return datetime.datetime.strptime(string, STRING_DATETIME_FORMAT)


def datetime_to_string(dt):
    return datetime.datetime.strftime(dt, STRING_DATETIME_FORMAT)