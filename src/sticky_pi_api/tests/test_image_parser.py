import unittest
from sticky_pi_api.image_parser import ImageParser
import datetime
import os
import logging

test_dir = os.path.dirname(__file__)

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)


class TestImageParser(unittest.TestCase):
    _test_image = os.path.join(test_dir, "raw_images/5c173ff2/5c173ff2.2020-06-20_21-33-24.jpg")
    _test_image_2022 = os.path.join(test_dir, "raw_images/2022/512858f4.2022-05-17_18-46-57.jpg")

    _test_image_metadata = {'device': '5c173ff2',
                            'datetime': datetime.datetime(2020, 6, 20, 21, 33, 24),
                            'filename': '5c173ff2.2020-06-20_21-33-24.jpg', 'width': 2592, 'height': 1944,
                            'lng': None, 'lat': None, 'alt': None, 'no_flash_exposure_time': 23646 / 1000000,
                            'no_flash_analog_gain': 100, 'no_flash_digital_gain': 236/ 100,
                            'temp': 21.899999618530273, 'hum': 76.80000305175781,
                            'md5': '65e69135d29871e8ee0ac453583effaf'}

    _test_image_metadata_2022 = {'device': '512858f4',
                            'datetime': datetime.datetime(2022, 5, 17, 18, 46, 57),
                            'filename': '512858f4.2022-05-17_18-46-57.jpg', 'width': 4056, 'height': 3040,
                            'device_version': '3.1.0',
                            # v,T,H,B,L,lat,lng,a,l,b.
                             # 3.1.0,,.6,72,1.20,,,1652813182,1
                            'lng': -123.25088, 'lat': 49.26142, 'alt': 97.3,
                            "bat": 72, "but": True,
                             "lum": 1.20,
                            'temp': 20.6, 'hum': 42.6,
                            'md5': 'e737e84d18e778cf367ca050fb96a841'}

    def test_parse(self):
        p = ImageParser(self._test_image)
        self.assertEqual(sorted(p.keys()), sorted(self._test_image_metadata.keys()))
        for k in p.keys():
            self.assertEqual(p[k], self._test_image_metadata[k])


    def test_parse_2022(self):
        p = ImageParser(self._test_image_2022)
        self.assertEqual(sorted(p.keys()), sorted(self._test_image_metadata_2022.keys()))
        for k in p.keys():
            self.assertEqual(p[k], self._test_image_metadata_2022[k])
    #

    def test_parse_stream(self):
        with open(self._test_image, 'rb') as f:
            p = ImageParser(f)
            self.assertEqual(sorted(p.keys()), sorted(self._test_image_metadata.keys()))
            for k in p.keys():
                self.assertEqual(p[k], self._test_image_metadata[k])
    #
    # def test_parse_stream_2022(self):
    #     with open(self._test_image_2022, 'rb') as f:
    #         p = ImageParser(f)
    #         self.assertEqual(sorted(p.keys()), sorted(self._test_image_metadata_2022.keys()))
    #         for k in p.keys():
    #             self.assertEqual(p[k], self._test_image_metadata_2022[k])

