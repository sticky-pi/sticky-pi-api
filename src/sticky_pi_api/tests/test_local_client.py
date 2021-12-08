import os
import tempfile
import json
import unittest
from sticky_pi_api.client import LocalClient
from sticky_pi_api.utils import string_to_datetime
from sqlalchemy.exc import IntegrityError
from contextlib import redirect_stderr
from io import StringIO
import shutil
import glob
import logging


logging.getLogger().setLevel(logging.INFO)
test_dir = os.path.dirname(__file__)


class LocalAndRemoteTests(object):
    _ml_bundle_dir = os.path.join(test_dir, 'ml_bundle')
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
                         datetime="2020-06-20T21:33:24Z", md5="65e69135d29871e8ee0ac453583effaf")}
    _test_dir = test_dir

    def __init__(self):
        self._test_image_for_annotation = os.path.join(self._test_dir, "raw_images/5c173ff2/5c173ff2.2020-06-20_21-33-24.jpg")
        self._tiled_tuboid_root_dir = os.path.join(self._test_dir,
                                              'tiled_tuboids/08038ade.2020-07-08_20-00-00.2020-07-09_15-00-00.1606980656-91e2199fccf371d3d690b2856613e8f5')
        self._tiled_tuboid_dirs = [os.path.join(self._tiled_tuboid_root_dir, d) for d in os.listdir(self._tiled_tuboid_root_dir)]
        self._test_images = [i for i in sorted(glob.glob(os.path.join(self._test_dir, "raw_images/**/*.jpg")))]

    def _clean_persistent_resources(self, cli):
        todel = [{'device': '%',
                                     'start_datetime': '2020-01-01T00:00:00Z',
                                     'end_datetime': '2020-12-31T00:00:00Z'}]
        out = cli.get_image_series(todel)
        cli.delete_images(out)
        cli.delete_tiled_tuboids(todel)


###########################################################################################################

    def test_init(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = self._make_client(temp_dir)
        finally:
            shutil.rmtree(temp_dir)

    def test_users(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            users = [
                {'username': 'ada', 'password': 'lovelace', 'email': 'mymail@computer.com'},
                {'username': 'grace', 'password': 'hopper', 'is_admin': True},
                    ]
            cli = self._make_client(temp_dir)
            self._clean_persistent_resources(cli)
            cli.put_users(users)
            cli.get_token({'username':'ada'})

            # cannot add same users twice
            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises(self._server_error) as context:
                    cli.put_users(users)

            out = cli.get_users()
            self.assertEqual(len(out), 2 + self._initial_n_users)

            out = cli.get_users(info=[{'username': '%'}])
            self.assertEqual(len(out), 2 + self._initial_n_users)

            out = cli.get_users(info=[{'username': 'ada'}])
            self.assertEqual(len(out), 1)

        finally:
            shutil.rmtree(temp_dir)
        # #

    def test_put_images(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = self._make_client(temp_dir)
            self._clean_persistent_resources(db)
            uploaded = db.put_images(self._test_images[0:2])

            self.assertEqual(len(uploaded), 2)

            uploaded = db.put_images(self._test_images)
            self.assertEqual(len(uploaded), len(self._test_images) - 2)

            uploaded = db.put_images(self._test_images)

            # should fail to put images that are already there:
            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises(self._server_error) as context:
                    db._put_new_images(self._test_images[0:1])

        finally:
            shutil.rmtree(temp_dir)


    def test_get_images(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = self._make_client(temp_dir)
            self._clean_persistent_resources(db)
            db.put_images(self._test_images)

            #the input dates of the client can be dates or string
            out = db.get_images([{'device': "1b74105a", 'datetime': "2020-07-05T10:07:16Z"}])
            self.assertEqual(len(out), 1)
            # the output of the client should be a date, always
            self.assertEqual(out[0]['datetime'], string_to_datetime("2020-07-05T10:07:16Z"))

            # Client should should parse datetime to string internally
            out = db.get_images([{'device': "1b74105a", 'datetime': string_to_datetime("2020-07-05T10:07:16Z")}])
            self.assertEqual(out[0]['datetime'], string_to_datetime("2020-07-05T10:07:16Z"))

            out = db.get_images([{'device': "1b74105a", 'datetime': "2020-07-05T10:07:16Z"}], what='image')
            self.assertEqual(len(out), 1)
            # second image should ba cached
            out = db.get_images([{'device': "1b74105a", 'datetime': "2020-07-05T10:07:16Z"}], what='image')
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
            db = self._make_client(temp_dir)
            self._clean_persistent_resources(db)
            db.put_images(self._test_images)
            out = db.get_image_series([{'device': "0a5bb6f4",
                                        'start_datetime': "2020-06-20T00:00:00Z",
                                        'end_datetime': "2020-06-22T00:00:00Z"}], what='image')
            logging.warning(out)
            self.assertEqual(len(out), 5)
            out2 = db.get_image_series([{'device': "0a5bb6f4",
                                        'start_datetime': "2020-06-20T00:00:00Z",
                                        'end_datetime': "2020-06-22T00:00:00Z"}], what='image')

            self.assertEqual(len(out2), 5)
            for o, o2 in zip(out, out2):
                self.assertDictEqual(o, o2)
#
#
        finally:
            shutil.rmtree(temp_dir)

    def test_put_image_uid_annotations(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            import copy
            db = self._make_client(temp_dir)
            self._clean_persistent_resources(db)
            im = db.put_images([self._test_image_for_annotation])
            db.put_uid_annotations([self._test_annotation])

            # update algo version should allow reupload of annotation
            test_annotation2 = copy.deepcopy(self._test_annotation)
            test_annotation2['metadata']['algo_version'] = '9000000000-ad2cd78dfaca12821046dfb8994724d5'
            db.put_uid_annotations([test_annotation2])
            #
            # should fail to upload twice the same annotations (save version/image)
            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises(self._server_error) as context:
                    db.put_uid_annotations([test_annotation2])

            # should fail to upload orphan annotations
            #
            test_annotation2['metadata']['device'] = '01234567'
            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises((ValueError, self._server_error)) as context:
                    db.put_uid_annotations([test_annotation2])
            #
            # # should clean both images AND annotations, in cascade

            self._clean_persistent_resources(db)
            # print(db.get_images(im, what='image'))
            db.put_images([self._test_image_for_annotation])
            db.put_uid_annotations([self._test_annotation])

        finally:
            shutil.rmtree(temp_dir)
    #
    def test_get_image_uid_annotations(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:

            db = self._make_client(temp_dir)
            self._clean_persistent_resources(db)

            # get annotation of non-existing parent image return an empty list
            out = db.get_uid_annotations([{'device': '5c173ff2', 'datetime': '2020-06-20T21:33:24Z'}])
            self.assertEqual(out, [])

            db.put_images([self._test_image_for_annotation])
            # parent image exists, but no annotation for it. empty list expected
            out = db.get_uid_annotations([{'device': '5c173ff2', 'datetime': '2020-06-20T21:33:24Z'}])
            self.assertEqual(out, [])
            db.put_uid_annotations([self._test_annotation])

            # we put two random images without annotation just to  make it harder
            db.put_images(self._test_images[0:2])

            # now we should have only one annotation out
            out = db.get_uid_annotations([{'device':'5c173ff2', 'datetime':'2020-06-20T21:33:24Z'}])
            self.assertEqual(len(out), 1)

            out = db.get_uid_annotations([{'device': '5c173ff2', 'datetime': '2020-06-20T21:33:24Z'}], what='data')
            print(out)
            self.assertDictEqual(json.loads(out[0]['json']), self._test_annotation)

        finally:
            shutil.rmtree(temp_dir)
    #
    def test_get_uid_annotations_series(self):
        import copy
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = self._make_client(temp_dir)
            from sticky_pi_api.image_parser import ImageParser
            from sticky_pi_api.utils import datetime_to_string
            self._clean_persistent_resources(db)
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
                                                        'start_datetime': '2020-01-01T00:00:00Z',
                                                        'end_datetime': '2020-12-31T00:00:00Z'}])
            # should return just the annotations for the matched query , not one per image (one image has no annot)
            self.assertEqual(len(out), len(to_upload[:-1]))


            out = db.get_uid_annotations_series([{'device': '0a5bb6f4',
                                                        'start_datetime': '2020-01-01T00:00:00Z:',
                                                        'end_datetime': '2020-12-31T00:00:00Z'}], what="metadata")
            # should return just the annotations for the matched query , not one per image (one image has no annot)
            self.assertEqual(len(out), len(to_upload[:-1]))


        finally:
            shutil.rmtree(temp_dir)

    def test_get_image_with_uid_annotations_series(self):
        import copy
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:
            db = self._make_client(temp_dir)
            from sticky_pi_api.image_parser import ImageParser
            from sticky_pi_api.utils import datetime_to_string
            self._clean_persistent_resources(db)
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
                                                            'start_datetime': '2020-01-01T00:00:00Z',
                                                            'end_datetime': '2020-12-31T00:00:00Z'}])

            # should return just the annotations for the matched query , not one per image (one image has no annot)
            self.assertEqual(len(out), len(to_upload))

        finally:
            shutil.rmtree(temp_dir)


    def test_ml_bundle(self):

        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        temp_dir2 = tempfile.mkdtemp(prefix='sticky-pi-')
        dummy_bundle_name = os.path.basename(self._ml_bundle_dir)
        try:

            db = self._make_client(temp_dir)
            self._clean_persistent_resources(db)

            out = db.put_ml_bundle_dir(dummy_bundle_name, self._ml_bundle_dir)
            self.assertEqual(len(out), 8)
            out = db.put_ml_bundle_dir(dummy_bundle_name, self._ml_bundle_dir)
            self.assertEqual(len(out), 0)

            bundle_dir = os.path.join(temp_dir2, dummy_bundle_name)

            out = db.get_ml_bundle_dir(dummy_bundle_name, bundle_dir, 'model')
            self.assertEqual(len(out), 3)

            out = db.get_ml_bundle_dir(dummy_bundle_name, bundle_dir, 'data')

            self.assertEqual(len(out), 5)

            out = db.get_ml_bundle_dir(dummy_bundle_name, bundle_dir, 'all')
            self.assertEqual(len(out), 0)


        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(temp_dir2)

    def test_tiled_tuboids(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:

            db = self._make_client(temp_dir)
            self._clean_persistent_resources(db)

            series = [{'device': '08038ade',
                       'start_datetime': '2020-07-08T20:00:00Z',
                       'end_datetime': '2020-07-09T15:00:00Z',
                       'n_tuboids': 6,
                       'n_images': 10,
                       'algo_name': 'test',
                       'algo_version':'11111111-19191919'}]

            db.put_tiled_tuboids(self._tiled_tuboid_dirs, series[0])
            self.assertEqual(len(db.get_tiled_tuboid_series(series, what='data')), 6)
            # get possibly cached url
            self.assertEqual(len(db.get_tiled_tuboid_series(series, what='data')), 6)
            import pandas as pd
            res = pd.DataFrame(db.get_tiled_tuboid_series(series))

            self.assertTrue(len(res) == res.iloc[0].n_tuboids_series)
            #
            self._clean_persistent_resources(db)
            series = [{'device': '08038ade',
                       'start_datetime': '2020-07-08T20:00:00Z',
                       'end_datetime': '2020-07-09T15:00:00Z',
                       'n_tuboids': 6,
                       'n_images': 10,
                       'algo_name': 'test',
                       'algo_version':'11111111-19191919'}]

            db.put_tiled_tuboids(self._tiled_tuboid_dirs, series[0])
            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises(self._server_error) as context:
                    db.put_tiled_tuboids(self._tiled_tuboid_dirs, series[0])


        finally:
            shutil.rmtree(temp_dir)



    def test_itc_labels(self):
        temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
        try:

            series = [{'device': '%',
                       'start_datetime': '2020-01-01T00:00:00Z',
                       'end_datetime': '2020-12-31T00:00:00Z',
                       'n_tuboids': 6,
                       'n_images': 10,
                       'algo_name': 'test',
                       'algo_version':'11111111-19191919'}]

            db = self._make_client(temp_dir)
            self._clean_persistent_resources(db)
            # emp[ty dt should be returned if no series exist
            db.get_tiled_tuboid_series_itc_labels(series)
            db.put_tiled_tuboids(self._tiled_tuboid_dirs, series[0])
            # should be missing the itc fields
            db.get_tiled_tuboid_series_itc_labels(series)
            info = [{
                'tuboid_id': '08038ade.2020-07-08_20-00-00.2020-07-09_15-00-00.1606980656-91e2199fccf371d3d690b2856613e8f5.0000',
                'algo_version': '1111-abce',
                'algo_name': 'insect_tuboid_classifier',
                'label': 1,
                'pattern': 'Insecta.*',
                'type':'Insecta',
                'order': 'test',
                'family':'test',
                'genus': 'test'
            }
            ]
            #
            out = db.put_itc_labels(info)
            self.assertEqual(len(out), 1)
            # cannot add same label twice

            with redirect_stderr(StringIO()) as stdout:
                with self.assertRaises(self._server_error) as context:
                    info[0]['label'] = 2
                    db.put_itc_labels(info)
            #
            info[0]['algo_name'] = 'another_algo'
            out = db.put_itc_labels(info)
            self.assertEqual(len(out), 1)
            #
            import pandas as pd
            pd.set_option('display.max_rows', 500)
            pd.set_option('display.max_columns', 500)
            out = pd.DataFrame(db.get_tiled_tuboid_series_itc_labels(series))
            # print(info[0]['tuboid_id'])
            print(out)
            # for i in range(len(out)):
            #     print(out.tuboid_id[i])
            # self.assertEqual(len(out[out.tuboid_id == info[0]['tuboid_id']]), 2)

        finally:
            shutil.rmtree(temp_dir)


class TestLocalClient(unittest.TestCase, LocalAndRemoteTests):
    _server_error = IntegrityError
    _initial_n_users = 0

    def __init__(self, method):
        LocalAndRemoteTests.__init__(self)
        unittest.TestCase.__init__(self, method)

    def _make_client(self, directory):
        return LocalClient(directory)


