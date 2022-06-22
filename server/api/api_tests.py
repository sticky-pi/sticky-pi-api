import unittest
import logging
import os
from sticky_pi_api.client import RemoteClient, RemoteAPIException
from sticky_pi_api.tests.test_local_client import LocalAndRemoteTests
import boto3
import tempfile
import shutil
import socket
import time

# set logging according to productions/devel/testing
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logging.getLogger().setLevel(logging.INFO)

if not (os.getenv('TESTING') and os.getenv('TESTING').lower() == "true"):
    logging.info('No testing to do. TESTING=%s' % os.getenv('TESTING'))
    exit(0)


class TestRemoteAPIEndToEnd(unittest.TestCase, LocalAndRemoteTests):
    _credentials = {'username': 'admin',
                    'password': os.getenv('API_ADMIN_PASSWORD'),
                    'host': 'spi_nginx',
                    'protocol': 'http',
                    'port': 80}
    _client_n_threads = 4
    _initial_n_users = 2
    _server_error = RemoteAPIException

    def _make_client(self, directory):
        return RemoteClient(directory, n_threads=self._client_n_threads, **self._credentials)

    def _clean_persistent_resources(self, cli):

        # if "." in os.getenv('S3_HOST'):
        #     local_s3_resource = False
        # else:
        #     local_s3_resource = True
        #

        credentials = {"aws_access_key_id": os.getenv('S3_ACCESS_KEY'),
                       "aws_secret_access_key": os.getenv('S3_PRIVATE_KEY'),
                       "endpoint_url": "http://%s:%s" % (
                       socket.gethostbyname(os.getenv('S3_HOST')), os.getenv('S3_PORT')),
                       }
        # if local_s3_resource:
        #     credentials.update({"endpoint_url": "http://%s:%s" % (socket.gethostbyname(os.getenv('S3_HOST')),
        #                                                             os.getenv('S3_PORT'))})
        # else:
        credentials.update({"endpoint_url": "https://%s" % os.getenv('S3_HOST')})
        s3 = boto3.resource('s3', **credentials)
        # fixme. this deletes all existing objects inside the test s3. we hardcode the name to prevent deleting
        #  important files by mistake localslack should make this irrelevent (eventually)
        # try:
        # time.sleep(5)

        # s3.create_bucket(Bucket='sticky-pi-api-dev')
        # except:
        #     pass

        bucket = s3.Bucket('sticky-pi-api-dev')
        bucket.objects.delete()
        # delete all_users
        super()._clean_persistent_resources(cli)

    def __init__(self, method):
        LocalAndRemoteTests.__init__(self)
        unittest.TestCase.__init__(self, method)
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:

            db = self._make_client(temp_dir)
            self._clean_persistent_resources(db)

        finally:
            shutil.rmtree(temp_dir)
