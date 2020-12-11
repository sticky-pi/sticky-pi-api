import logging
import os
from sticky_pi_api.client import RemoteClient

import time

# set logging according to productions/devel/testing
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logging.getLogger().setLevel(logging.INFO)

if not(os.getenv('TESTING') and os.getenv('TESTING').lower() == "true"):
    logging.info('No testing to do. TESTING=%' % os.getenv('TESTING') )
    exit(0)

credentials = {'username': 'admin',
               'password': os.getenv('API_ADMIN_PASSWORD'),
               'host': 'spi_nginx',
               'protocol': 'http',
               'port': 80
               }

r = RemoteClient(**credentials)

TEST_USER = {'username':'test',
             'password': 'testpass'}

out = r.put_users([TEST_USER])
print(out)
print('DONE')


