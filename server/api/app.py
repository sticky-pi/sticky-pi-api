from flask import Flask
from flask import jsonify
from sticky_pi_api.configuration import RemoteAPIConf
from sticky_pi_api.specifications import RemoteAPI

# request from environment a set of configuration variables as listed in the class attributes
import logging
import os

logging.error(os.environ)
conf = RemoteAPIConf()
api = RemoteAPI(conf)
app = Flask(__name__)



@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('get_users')
def get_users():
    out = api.get_users()
    return jsonify(out)

