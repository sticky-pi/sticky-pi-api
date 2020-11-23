import os
import logging
import glob
from sticky_pi_api.client import LocalClient

DIR_TO_SYNC = "/home/qgeissma/projects/def-juli/qgeissma/legacy/sticky_pi_root/raw_images"
LOCAL_CLIENT_DIR = "/home/qgeissma/projects/def-juli/qgeissma/sticky_pi_client"
logging.getLogger().setLevel(logging.INFO)

if __name__ == '__main__':
    client = LocalClient(LOCAL_CLIENT_DIR)
    all_images = [f for f in sorted(glob.glob(os.path.join(LOCAL_CLIENT_DIR, '**', "*.jpg")))]
    client.put_images(all_images)

