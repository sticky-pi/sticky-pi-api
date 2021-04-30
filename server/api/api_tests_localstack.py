import logging
import boto3
import os
from unittest import TestCase
import time
import glob
import filecmp
import tempfile
import requests
from botocore.client import ClientError

# TODO should be sleep 10 for using docker!
time.sleep(1)

# set basic logging
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logging.getLogger().setLevel(logging.INFO)

test_dir = os.path.dirname(__file__)


#spi_s3_ip = socket.gethostbyname("spi_s3")

class Test(TestCase):
    credentials = {"aws_access_key_id": "ABCDSICKY",
                       "aws_secret_access_key": "ABCDSTICKY",
                       #"endpoint_url": f"http://{spi_s3_ip}:4566",
                       "endpoint_url": "http://localhost:4566",
                       "region_name": 'us-east-1',
                       "use_ssl": True
                       }
    s3Client = boto3.client('s3', **credentials)
    _endpoint = credentials["endpoint_url"]
    _test_dir = test_dir
    _test_images = [i for i in sorted(glob.glob(os.path.join(_test_dir, "test_images/**/*.jpg")))]

    def test_create_bucket(self):
        # create bucket
        self.s3Client.create_bucket(Bucket='test-bucket')
        bucket = self.s3Client.list_buckets()
        print(bucket['Buckets'][0])
        try:
            # another check that creation was successful
            self.s3Client.head_bucket(Bucket='test-bucket')
        except ClientError:
            print(ClientError)
    
    def test_upload_file(self):
        self.s3Client.create_bucket(Bucket='test-bucket')
        try:
            #upload file
            self.s3Client.upload_file(Filename=self._test_images[0], Bucket='test-bucket', Key='img')
            # check that upload was successful
            self.s3Client.head_object(Bucket='test-bucket', Key='img')
            objects = self.s3Client.list_objects_v2(Bucket='test-bucket', Prefix='img')
            assert objects.get('Prefix') == 'img'
        except ClientError:
            print(ClientError)

    def test_download_file(self):
        self.s3Client.create_bucket(Bucket='test-bucket')
        try:
            # upload file
            self.s3Client.upload_file(Filename=self._test_images[1], Bucket='test-bucket', Key='img2')
            with tempfile.TemporaryDirectory() as d:
                # download file to temp directory
                temp_filename= os.path.join(d, 'something')
                self.s3Client.download_file(Bucket='test-bucket', Key='img2', Filename=temp_filename)
                # assert download was successful
                assert(filecmp.cmp(temp_filename, self._test_images[1]))
        except ClientError:
            print(ClientError)

    def test_get_presigned_url(self):
        self.s3Client.create_bucket(Bucket='test-bucket')
           # get presigned url (expires in 1 hr)
        try:
            url = self.s3Client.generate_presigned_url(ClientMethod='get_object',
                                                        Params={'Bucket': 'test-bucket', 'Key': 'test-key'},
                                                        ExpiresIn=3600)
            # assert getting url was successful (somewhat from storage.py)
            prefix, suffix = url.split("?")
            s3_prefix = f"{self._endpoint}/{'test-bucket'}/{'test-key'}"
            assert prefix == s3_prefix
            # assert can upload using presigned URL TODO
        except ClientError:
            print(ClientError)
