
import unittest
from sticky_pi_client.client import LocalClient
import datetime
import pytz

import glob

class TestImageParser(unittest.TestCase):
    _test_images = [i for i in sorted(glob.glob("raw_images/**/*.jpg"))]
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
            print(out)

        finally:
            import shutil
            shutil.rmtree(temp_dir)

