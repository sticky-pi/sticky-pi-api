import unittest
from sticky_pi_api.image_parser import ImageParser
import datetime

import os

test_dir = os.path.dirname(__file__)

class TestImageParser(unittest.TestCase):
    _test_image = os.path.join(test_dir, "raw_images/5c173ff2/5c173ff2.2020-06-20_21-33-24.jpg")
    _test_image_metadata = {'device': '5c173ff2',
                            'datetime': datetime.datetime(2020, 6, 20, 21, 33, 24),
                            'filename': '5c173ff2.2020-06-20_21-33-24.jpg', 'width': 2592, 'height': 1944,
                            'lng': None, 'lat': None, 'alt': None, 'no_flash_exposure_time': 23646/ 1000000,
                            'no_flash_iso': 100, 'no_flash_bv': 236/ 100,
                            'no_flash_shutter_speed': 5402260/ 1000000,
                            'temp': 21.899999618530273, 'hum': 76.80000305175781,
                            'md5': '9e6e908d9c29d332b511f8d5121857f8'}
    def test_parse(self):
        p = ImageParser(self._test_image)
        self.assertEqual(sorted(p.keys()), sorted(self._test_image_metadata.keys()))
        for k in p.keys():
            self.assertEqual(p[k], self._test_image_metadata[k])

    def test_parse_stream(self):
        with open(self._test_image, 'rb') as f:
            p = ImageParser(f)
            self.assertEqual(sorted(p.keys()), sorted(self._test_image_metadata.keys()))
            for k in p.keys():
                self.assertEqual(p[k], self._test_image_metadata[k])

