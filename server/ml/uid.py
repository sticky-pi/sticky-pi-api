import os
from sticky_pi_api.client import RemoteClient
from sticky_pi_ml.universal_insect_detector.ml_bundle import ClientMLBundle
from sticky_pi_ml.universal_insect_detector.predictor import Predictor

BUNDLE_NAME = 'universal-insect-detector'

bundle_dir = os.path.join(os.environ["BUNDLE_ROOT_DIR"], BUNDLE_NAME)

if __name__ == '__main__':
    client = RemoteClient(os.path.join(os.environ["LOCAL_CLIENT_DIR"], 'client'),
                          os.environ["RSHINY_UPSTREAM_ROOT_URL"],
                          os.environ["UID_USER"],
                          os.environ["UID_PASSWORD"], protocol=os.environ["RSHINY_UPSTREAM_PROTOCOL"],
                          port=int(os.environ["RSHINY_UPSTREAM_PORT"]))

    ml_bundle = ClientMLBundle(bundle_dir,
                               client,
                               device="cpu",
                               cache_dir=os.path.join(bundle_dir, "/.cache"))
    ml_bundle.sync_remote_to_local()
    predictor = Predictor(ml_bundle)
    predictor.detect_client(info=[{"device": "%",
                                   "start_datetime": "2021-01-01_00-00-00",
                                   "end_datetime": "2100-01-01_00-00-00"}])
