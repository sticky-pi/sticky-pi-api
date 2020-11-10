import os


class LocalDBStorage(object):
    _raw_images_dirname = 'raw_images'

    def __init__(self, local_dir):
        self._local_dir = local_dir

    def store_image_files(self, image):
        target = os.path.join(self._local_dir, self._raw_images_dirname, image.device, image.filename)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(image.file_blob)
        image.thumbnail.save(target + ".thumbnail", format='jpeg')
        image.thumbnail_mini.save(target + ".thumbnail_mini", format='jpeg')

    def get_url_for_image(self, image, what='metadata'):
        if what == 'metadata':
            return ""

        url = os.path.join(self._local_dir, self._raw_images_dirname, image.filename)
        if what == "thumbnail":
            url += ".thumbnail"
        elif what == "thumbnail_mini":
            url += ".thumbnail_mini"
        elif what == "image":
            pass
        else:
            raise ValueError("Unexpected `what` argument: %s. Should be in {'metadata', 'image', 'thumbnail', 'thumbnail_mini'}")

        return url
