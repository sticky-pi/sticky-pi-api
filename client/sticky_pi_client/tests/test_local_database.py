import json
import unittest
from sticky_pi_client.client import LocalClient
from sqlalchemy.exc import IntegrityError
import datetime
import pytz

import glob

class TestImageParser(unittest.TestCase):
    _test_images = [i for i in sorted(glob.glob("raw_images/**/*.jpg"))]

    _test_annotation = '''
                    {"annotations": [{"contour": [[[2194, 1597]], [[2189, 1602]], [[2189, 1617]], [[2200, 1630]], [[2201, 1634]], [[2221, 1656]], [[2240, 1656]], [[2245, 1647]], [[2245, 1632]], [[2236, 1621]], [[2241, 1613]], [[2239, 1607]], [[2236, 1605]], [[2225, 1605]], [[2211, 1597]]], "name": "insect", "stroke_colour": "#0000ff", "value": 0, "fill_colour": "#ff0000"}], "metadata": {"algo_name": "sticky-pi-universal-insect-detector", "algo_version": "1598113346-ad2cd78dfaca12821046dfb8994724d5", "device": "5c173ff2", "datetime": "2020-06-20_21-33-24", "md5": "9e6e908d9c29d332b511f8d5121857f8"}}
                    '''
    _test_image_for_annotation = "raw_images/5c173ff2/5c173ff2.2020-06-20_21-33-24.jpg"

    def test_init(self):
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_put(self):
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)
            uploaded = db.put_images(self._test_images[0:2])
            self.assertEqual(len(uploaded), 2)
            uploaded = db.put_images(self._test_images)
            self.assertEqual(len(uploaded), len(self._test_images) - 2)
            # should fail to put images that are already there:

            with self.assertRaises(IntegrityError) as context:
                db._put_new_images(self._test_images[0:1])
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_get(self):
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)
            db.put_images(self._test_images)
            out = db.get_images([{'device': "1b74105a", 'datetime': "2020-07-05_10-07-16"}])
            self.assertEqual(len(out), 1)

            out = db.get_images([{'device': "1b74105a", 'datetime': "2020-07-05_10-07-16"}], what='image')
            self.assertEqual(len(out), 1)

            # we try to parse the image from its url
            from sticky_pi_client.image_parser import ImageParser
            img_dict = ImageParser(out[0]['url'])
            self.assertEqual(out[0]['md5'], img_dict['md5'])
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_get_image_series(self):
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)
            db.put_images(self._test_images)
            out = db.get_image_series([{'device': "0a5bb6f4",
                                        'start_datetime': "2020-06-20_00-00-00",
                                        'end_datetime': "2020-06-22_00-00-00"}], what='image')

            self.assertEqual(len(out), 5)
            # self.assertEqual(, img_dict['md5'])
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_put_image_uid_annotations(self):
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)

            db.put_images([self._test_image_for_annotation])
            db.put_image_uid_annotations([self._test_annotation])

        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_get_image_uid_annotations(self):
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)

            db.put_images([self._test_image_for_annotation])
            db.put_image_uid_annotations([self._test_annotation])

            # should fail to upload twice the same annotations
            with self.assertRaises(IntegrityError) as context:
                db.put_image_uid_annotations([self._test_annotation])

            out = db.get_image_uid_annotations([{'device':'5c173ff2', 'datetime':'2020-06-20_21-33-24'}])
            out = db.get_image_uid_annotations([{'device': '5c173ff2', 'datetime': '2020-06-20_21-33-24'}], what='data')
            self.assertEqual(json.loads(out[0]['json']), json.loads(self._test_annotation))

        finally:
            import shutil
            shutil.rmtree(temp_dir)