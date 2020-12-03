import os
import tempfile
import json
import unittest
from sticky_pi_api.client import LocalClient
from sqlalchemy.exc import IntegrityError
from contextlib import redirect_stderr
from io import StringIO
import shutil
import glob
import logging

logging.getLogger().setLevel(logging.INFO)


dir = os.path.dirname(__file__)

class TestLocalClient(unittest.TestCase):
    _test_images = [i for i in sorted(glob.glob(os.path.join(dir, "raw_images/**/*.jpg")))]
    _ml_bundle_dir = os.path.join(dir, 'ml_bundle')
    _test_annotation = {"annotations": [
        dict(contour=[[[2194, 1597]], [[2189, 1602]], [[2189, 1617]], [[2200, 1630]], [[2201, 1634]], [[2221, 1656]],
                      [[2240, 1656]], [[2245, 1647]], [[2245, 1632]], [[2236, 1621]], [[2241, 1613]], [[2239, 1607]],
                      [[2236, 1605]], [[2225, 1605]], [[2211, 1597]]],
             name="insect",
             stroke_colour="#0000ff",
             value=0,
             fill_colour="#ff0000")],
        "metadata": dict(algo_name="sticky-pi-universal-insect-detector",
                         algo_version="1598113346-ad2cd78dfaca12821046dfb8994724d5", device="5c173ff2",
                         datetime="2020-06-20_21-33-24", md5="9e6e908d9c29d332b511f8d5121857f8")}

    _test_image_for_annotation = os.path.join(dir,"raw_images/5c173ff2/5c173ff2.2020-06-20_21-33-24.jpg")


    def test_users(self):

        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            users = [
                {'username': 'ada', 'password': 'lovelace', 'email': 'mymail@computer.com'},
                {'username': 'grace', 'password': 'hopper', 'is_admin': True},
                    ]
            cli = LocalClient(temp_dir)
            cli.put_users(users)

            # cannot add same users twice
            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises(IntegrityError) as context:
                    cli.put_users(users)

            out = cli.get_users()
            self.assertEqual(len(out), 2)

            out = cli.get_users(info={'username':'%'})
            self.assertEqual(len(out), 2)

            out = cli.get_users(info={'username':'ad%'})
            self.assertEqual(len(out), 1)

        finally:
            shutil.rmtree(temp_dir)

    def test_init(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)
        finally:
            shutil.rmtree(temp_dir)

    #
    def test_put(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)
            uploaded = db.put_images(self._test_images[0:2])
            self.assertEqual(len(uploaded), 2)
            uploaded = db.put_images(self._test_images)
            self.assertEqual(len(uploaded), len(self._test_images) - 2)
            # should fail to put images that are already there:
            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises(IntegrityError) as context:
                    db._put_new_images(self._test_images[0:1])
        finally:
            shutil.rmtree(temp_dir)
    #
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
            from sticky_pi_api.image_parser import ImageParser
            img_dict = ImageParser(out[0]['url'])
            self.assertEqual(out[0]['md5'], img_dict['md5'])
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_get_image_series(self):
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
            shutil.rmtree(temp_dir)
    # #
    def test_put_image_uid_annotations(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)

            db.put_images([self._test_image_for_annotation])
            db.put_uid_annotations([self._test_annotation])

            # should fail to upload twice the same annotations
            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises(IntegrityError) as context:
                    db.put_uid_annotations([self._test_annotation])

            # should fail to upload orphan annotations
            annot = self._test_annotation
            annot['metadata']['device'] = '01234567'
            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises(ValueError) as context:
                    db.put_uid_annotations([annot])
        finally:
            shutil.rmtree(temp_dir)

    def test_get_image_uid_annotations(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)

            # get annotation of non-existing parent image return an empty list
            out = db.get_uid_annotations([{'device': '5c173ff2', 'datetime': '2020-06-20_21-33-24'}])
            self.assertEqual(out, [])

            db.put_images([self._test_image_for_annotation])
            # parent image exists, but no annotation for it. empty list expected
            out = db.get_uid_annotations([{'device': '5c173ff2', 'datetime': '2020-06-20_21-33-24'}])
            self.assertEqual(out, [])
            db.put_uid_annotations([self._test_annotation])

            # we put two random images without annotation just to  make it harder
            db.put_images(self._test_images[0:2])

            # now we should have only one annotation out
            out = db.get_uid_annotations([{'device':'5c173ff2', 'datetime':'2020-06-20_21-33-24'}])
            self.assertEqual(len(out), 1)

            out = db.get_uid_annotations([{'device': '5c173ff2', 'datetime': '2020-06-20_21-33-24'}], what='data')
            self.assertDictEqual(json.loads(out[0]['json']), self._test_annotation)

        finally:
            shutil.rmtree(temp_dir)
    #
    def test_get_uid_annotations_series(self):
        import copy
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)
            from sticky_pi_api.image_parser import ImageParser
            from sticky_pi_api.utils import datetime_to_string

            to_upload = [ti for ti in self._test_images if ImageParser(ti)['device'] == '0a5bb6f4']
            db.put_images(to_upload)


            # we upload annotations for all, but the last image

            annot_to_up = []
            for ti in to_upload[:-1]:
                p = ImageParser(ti)
                annotation_stub = copy.deepcopy(self._test_annotation)
                annotation_stub['metadata']['device'] = p['device']
                annotation_stub['metadata']['datetime'] = datetime_to_string(p['datetime'])
                annotation_stub['metadata']['md5'] = p['md5']
                annot_to_up.append(annotation_stub)

            db.put_uid_annotations(annot_to_up)

            out = db.get_uid_annotations_series([{'device': '0a5bb6f4',
                                                        'start_datetime': '2020-01-01_00-00-00',
                                                        'end_datetime': '2020-12-31_00-00-00'}])
            # should return just the annotations for the matched query , not one per image (one image has no annot)
            self.assertEqual(len(out), len(to_upload[:-1]))

        finally:
            shutil.rmtree(temp_dir)

    def test_get_image_with_uid_annotations_series(self):
        import copy
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = LocalClient(temp_dir)
            from sticky_pi_api.image_parser import ImageParser
            from sticky_pi_api.utils import datetime_to_string

            to_upload = [ti for ti in self._test_images if ImageParser(ti)['device'] == '0a5bb6f4']
            db.put_images(to_upload)


            # we upload annotations for all, but the last image

            annot_to_up = []
            for ti in to_upload[:-1]:
                p = ImageParser(ti)
                annotation_stub = copy.deepcopy(self._test_annotation)
                annotation_stub['metadata']['device'] = p['device']
                annotation_stub['metadata']['datetime'] = datetime_to_string(p['datetime'])
                annotation_stub['metadata']['md5'] = p['md5']
                annot_to_up.append(annotation_stub)

            db.put_uid_annotations(annot_to_up)

            out = db.get_images_with_uid_annotations_series([{'device': '0a5bb6f4',
                                                            'start_datetime': '2020-01-01_00-00-00',
                                                            'end_datetime': '2020-12-31_00-00-00'}])

            # should return just the annotations for the matched query , not one per image (one image has no annot)
            self.assertEqual(len(out), len(to_upload))

        finally:
            shutil.rmtree(temp_dir)
    #

    def test_ml_bundle(self):

        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        temp_dir2 = tempfile.mkdtemp(prefix='sticky-pi-')
        try:

            db = LocalClient(temp_dir)
            # db2 = LocalClient(temp_dir2)
            out = db.put_ml_bundle_dir(self._ml_bundle_dir)
            # self.assertEqual(len(out), 8)
            out = db.put_ml_bundle_dir(self._ml_bundle_dir)
            # self.assertEqual(len(out), 0)
            # #
            bundle_dir = os.path.join(temp_dir2, 'ml_bundle')

            out = db.get_ml_bundle_dir(bundle_dir, 'model')

            self.assertEqual(len(out), 3)

            out = db.get_ml_bundle_dir(bundle_dir, 'data')
            self.assertEqual(len(out), 5)

            out = db.get_ml_bundle_dir(bundle_dir, 'all')
            self.assertEqual(len(out), 0)


        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_dir2)
