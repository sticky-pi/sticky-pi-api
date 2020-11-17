import tempfile
import requests
import getpass

from sticky_pi.universal_insect_detector.detector import Detector
from sticky_pi.universal_insect_detector.dataset import Dataset, RemoteDataset
from sticky_pi.database import ImageDBRemote

from optparse import OptionParser
import os
from sticky_pi.image import Image
from sticky_pi.api import StickyPiAPI
import logging
from sticky_pi.tools import  md5


if __name__ == '__main__':

    parser = OptionParser()

    parser.add_option("-d", "--directory", dest="directory", help="the sticky pi root directory",
                      )

    parser.add_option("-u", "--username", dest="username", help="username on server",
                      )
    parser.add_option("-w", "--host", dest="host", help="API host e.g. 'my.api.net'",
                      )

    parser.add_option("-k", "--protocol", dest="protocol", default='https', help="http or https",
                      )

    parser.add_option("-p", "--port", dest="port", default='443', help="API port",
                      )
    parser.add_option("-z", "--password", dest="password", default=None,
                      help="Password. if not provided, will be prompted",
                      )

    parser.add_option("-m", "--model-name", dest="model_name", default='sticky_pi_api-universal-insect-detector',
                      help="The name of the model to be run",
                      )

    parser.add_option("-g", "--gpu", dest="gpu", default=False,
                      help="Whether to use GPU/CUDA",
                      action="store_true")

    parser.add_option("-v", "--verbose", dest="verbose", default=False,
                      help="verbose",
                      action="store_true")

    parser.add_option("-D", "--debug", dest="debug", default=False,
                      help="show debug info",
                      action="store_true")

    skip_errors = True
    (options, args) = parser.parse_args()
    option_dict = vars(options)

    if option_dict['verbose']:
        logging.getLogger().setLevel(logging.INFO)

    if option_dict['debug']:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("DEBUG mode ON")

    if not os.path.exists(option_dict['directory']):
        raise Exception('No such directory: %s' % option_dict['directory'])

    if option_dict['password']:
        password = option_dict['password']
    else:
        password = getpass.getpass()

    api = StickyPiAPI(option_dict['host'],
                      option_dict['username'],
                      password,
                      protocol=option_dict['protocol'],
                      port=int(option_dict['port']),
                      sticky_pi_dir=option_dict['directory']
                      )

        # out = api.download_annotations(1, 'my_super_detector', '/tmp/test.json')


    with Dataset(option_dict['directory'], option_dict['model_name']) as ds:
        ds.set_conf(use_cpu = not option_dict['gpu'])
        detector = Detector(ds)
        while True:
            jobs = api.get_annotation_job(detector)
            logging.info("Requested annotation job. got %i images to process with %s" % (len(jobs), option_dict['model_name']))
            logging.info("Images: %s" % str({ j['filename'] for j in jobs }))
            if len(jobs) ==0:
                logging.info('All jobs done!')
                break
            tmp_dir = tempfile.mkdtemp(prefix='sticky_pi_')
            try:
                for j in jobs:
                    try:
                        tmp_file = os.path.join(tmp_dir, j['filename'])
                        logging.info('Getting %s' % j['filename'])

                        dl_url = j['url']
                        r = requests.get(dl_url, stream=True)
                        with open(tmp_file, 'wb') as f:
                            for chunk in r:
                                f.write(chunk)
                        with open(tmp_file, 'rb') as f:
                            md5sum = md5(f)
                        assert md5sum == j['md5sum']
                        im = Image(tmp_file)
                        logging.info('Detecting in  %s' % j['filename'])
                        out_im = detector.detect(im)
                        logging.info('Uploading results of %s' % j['filename'])
                        api.upload_annotations(out_im, md5sum)
                    except Exception as e:
                        logging.error(e)
                        if not skip_errors:
                            raise e
            finally:
                import shutil
                shutil.rmtree(tmp_dir)
    #
    # db = ImageDBRemote('/tmp/some_dir', api, 'sticky_pi_api-universal-insect-detector', n_thread=1)
    # s = db.select_series('7168f343', '2018-01-01_01-01-01', '2021-01-01_01-01-01')
    # print(s)


        # db = ImageDBRemote(configuration["SPI_ROOT"], api, n_thread=4)
        # q = db.select_multiple_series(query)
        #
        # with RemoteDataset(configuration["SPI_ROOT"],
        #                    configuration["S3BUCKET_NAME_UID"],
        #                    cred_env_file=SECRET_CONFIG_FILE) as dataset:
        #     pass
