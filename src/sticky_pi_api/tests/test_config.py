import unittest
from sticky_pi_api.configuration import BaseAPIConf
import datetime
import pytz


class TestConfig(unittest.TestCase):

    def test_parse(self):
        conf = BaseAPIConf(SECRET_API_KEY="abcs", MYSQL_HOST=1, RANDOM_CONF=2)
        self.assertEqual(conf.SECRET_API_KEY, 'abcs')
