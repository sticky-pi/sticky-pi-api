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