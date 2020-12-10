import pandas as pd
import logging
from sticky_pi_client.client import LocalClient
import glob
import os

LOCAL_DIR = "/home/quentin/Desktop/sticky_pi_client/"
SRC_IMG_DIR = "/home/quentin/sticky_pi_root/raw_images"


files = [f for f in sorted(glob.glob(os.path.join(SRC_IMG_DIR, "**", "*.jpg")))]
logging.getLogger().setLevel(logging.INFO)
db = LocalClient(LOCAL_DIR)

# db.delete_cache()
# uploaded = db.put_images(files[0:1000])

df = pd.DataFrame(db.get_image_series([{'device':"%", "start_datetime":"2000-01-01_00-00-00", "end_datetime":"2100-01-01_00-00-00"}], what='image'))
print(df, )

# self.assertEqual(len(uploaded), 2)
# uploaded = db.put_images(self._test_images)
# self.assertEqual(len(uploaded), len(self._test_images) - 2)
# should fail to put images that are already there:
