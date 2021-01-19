
import os
from sticky_pi_api.client import RemoteClient
from sticky_pi_ml.insect_tuboid_classifier.ml_bundle import ClientMLBundle
from sticky_pi_ml.insect_tuboid_classifier.predictor import Predictor


BUNDLE_NAME = 'insect-tuboid-classifier'
if __name__ == '__main__':

    client = RemoteClient(os.path.join(os.environ["LOCAL_CLIENT_DIR"], 'client'),
                       "spi_nginx",
                       os.environ["UID_USER"],
                       os.environ["UID_PASSWORD"], protocol='http', port=80)

    ml_bundle = ClientMLBundle(os.environ["BUNDLE_ROOT_DIR"],
                               client,
                               device="cpu",
                               cache_dir=os.path.join(os.environ["BUNDLE_ROOT_DIR"], "/.cache"))
    ml_bundle.sync_remote_to_local()
    predictor = Predictor(ml_bundle)
    predictor.predict_client(device="%", start_datetime="2020-01-01_00-00-00", end_datetime="2100-01-01_00-00-00")

