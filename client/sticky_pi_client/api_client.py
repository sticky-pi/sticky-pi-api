"""
a module
document me please
s
dd
"""



class BaseAPIClient(object):
    def __init__(self, local_dir):
        """
        Local api client

        :param local_dir: the local directory where the local database is/will be set up
        :type local_dir: basestring

        """

        self._local_dir = local_dir


    def put_images(self, images):
        pass


    def get_images(self, images):
        pass

