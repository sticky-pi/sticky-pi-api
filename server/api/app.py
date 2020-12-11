from sticky_pi_api.configuration import RemoteAPIConf
from sticky_pi_api.specifications import RemoteAPI
from sqlalchemy.exc import OperationalError, IntegrityError
from flask import Flask, abort, request, jsonify, g, url_for, Response
from flask_httpauth import HTTPBasicAuth
from flask import request
from retry import retry
import os
import logging

# just wait for database to be ready
@retry(exceptions=OperationalError, delay=2, max_delay=10)
def get_api(config):
    return RemoteAPI(config)


#  to create initial admin user if does not exist
def create_initial_admin(api):
    admin_user = {'username': os.getenv('API_ADMIN_NAME'),
                  'password': os.getenv('API_ADMIN_PASSWORD'),
                  'is_admin': True}

    assert admin_user['username'], 'Cannot find admin username in env (API_ADMIN_NAME)'
    assert admin_user['password'] and len(admin_user['password']) > 10, \
        'Default admin user password missing or too short (API_ADMIN_PASSWORD)'
    try:
        api.put_users([admin_user])
    except IntegrityError as e:
        # fixme, we could actually check that assertion
        logging.debug('Admin user already exists?')


# set logging according to productions/devel/testing
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)


if os.getenv('DEVEL') and os.getenv('DEVEL').lower() == "true":
    logging.getLogger().setLevel(logging.INFO)
    logging.info('Devel mode ON')

if os.getenv('DEBUG') and os.getenv('DEBUG').lower() == "true":
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info('Debug mode ON')



conf = RemoteAPIConf()
auth = HTTPBasicAuth()
api = get_api(conf)
create_initial_admin(api)

# configure authentication
@auth.verify_password
def verify_password(username_or_token, password):
    return api.verify_password(username_or_token, password)

@auth.get_user_roles
def get_user_roles(user):
    users = api.get_users([{'username': user}])
    assert len(users) == 1
    is_admin = users[0]['is_admin']
    return 'admin' if is_admin else 'user'


app = Flask(__name__)

@app.route('/')
# @auth.login_required()
def hello_world():
    return 'Hello, World!'

@app.route('/get_users', methods = ['POST'])
@auth.login_required(role='admin')
def get_users():
    out = api.get_users()
    return jsonify(out)

@app.route('/put_users', methods = ['POST'])
@auth.login_required(role='admin')
def put_users():
    data = request.get_json()
    if not data:
        print(request)
        raise Exception()
    out = api.put_users(data)
    return jsonify(out)
