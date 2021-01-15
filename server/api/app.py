from flask import Flask, abort, request, jsonify, g, url_for, Response
from sqlalchemy.exc import OperationalError, IntegrityError
from flask_httpauth import HTTPBasicAuth
from flask.json import JSONEncoder
from flask import request
from retry import retry
from decimal import Decimal
import datetime
import logging
import json
import os
import io

from sticky_pi_api.configuration import RemoteAPIConf
from sticky_pi_api.specifications import RemoteAPI
from sticky_pi_api.utils import datetime_to_string


# just wait for database to be ready
@retry(exceptions=OperationalError, delay=2, max_delay=10)
def get_api(config: RemoteAPIConf) -> RemoteAPI:
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

if os.getenv('DEVEL') and os.getenv('DEVEL').lower() == "true":
    log_lev = logging.INFO
    logging.info('Devel mode ON')

elif os.getenv('DEBUG') and os.getenv('DEBUG').lower() == "true":
    log_lev = logging.DEBUG
    logging.info('Debug mode ON')
else:
    log_lev = logging.WARNING

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=log_lev)


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
    if not users[0]['can_write']:
        return "read_only_user"
    is_admin = users[0]['is_admin']
    return 'admin' if is_admin else 'read_write_user'


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        try:
            if isinstance(o, datetime.datetime):
                return datetime_to_string(o)
            elif isinstance(o, Decimal):
                return float(o)
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, o)


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder


# fixme. an attempt to programatically define entrypoints
# def add_entry_point(name, role='admin', methods=['POST']):
#     @app.route('/' + name, endpoint=name,  methods=methods)
#
#     @auth.login_required(role=role)
#     def foo():
#         data = request.get_json()
#         out = api.get_users(data)
#         return jsonify(out)
#
#     app.add_url_rule('/' + name,
#                      endpoint=name,
#                      view_func=foo)
#
#
# add_entry_point('get_users')
# add_entry_point('put_users')
template_function = \
"""
@app.route('/%s%s', methods = ['POST'])
@auth.login_required(%s)
def %s(**kwargs):
    data = request.get_json()
    client_info = {'username':auth.current_user()}
    out = api.%s(data, client_info=client_info, **kwargs)
    return jsonify(out)
"""


def make_endpoint(method, role = 'admin', what=False):
    if not role:
        role = ""
    elif isinstance(role, str):
        role = str([role])

    endpoint = method.__name__
    sub_route = "/<what>" if what else ""
    role_str = "role=%s" % role if role else ""
    assert endpoint in dir(api), "all endpoint must point to api methods. got %s" % endpoint
    # print(template_function % (endpoint, sub_route, role_str, endpoint, endpoint))
    exec(template_function % (endpoint, sub_route, role_str, endpoint, endpoint))


@app.route('/get_token', methods=['POST'])
@auth.login_required()
def get_token():
    client_info = {'username': auth.current_user()}
    out = api.get_token(client_info=client_info)
    return jsonify(out)



make_endpoint(api.get_users, role='admin')
make_endpoint(api.put_users, role='admin')

#todo
# make_endpoint(api.delete_users, role="admin")

make_endpoint(api.get_images, role="", what=True)
make_endpoint(api.get_image_series, role="", what=True)
make_endpoint(api.delete_images, role="admin")
make_endpoint(api.delete_tiled_tuboids, role="admin")
make_endpoint(api.put_uid_annotations, role=['admin', 'read_write_user'])
make_endpoint(api.get_uid_annotations, role="", what=True)
make_endpoint(api.get_uid_annotations_series, role="", what=True)

# see below
# make_endpoint(api._put_tiled_tuboids, role="", what=True)

make_endpoint(api.get_tiled_tuboid_series, role="", what=True)
make_endpoint(api._get_ml_bundle_upload_links, role="")
make_endpoint(api._get_ml_bundle_file_list, role="", what=True)

make_endpoint(api.put_itc_labels, role=['admin', 'read_write_user'])
make_endpoint(api._get_itc_labels, role="")



@app.route('/_put_new_images', methods=['POST'])
@auth.login_required(role=["admin", "read_write_user"])
def _put_new_images():
    files = request.files
    assert len(files) > 0
    out = []
    for k, f in files.items():
        out += api.put_images([f],client_info = {'username': auth.current_user()})
    return jsonify(out)

@app.route('/_put_tiled_tuboids', methods=['POST'])
@auth.login_required(role=["admin", "read_write_user"])
def _put_tiled_tuboids():
    files = request.files
    assert len(files) > 0
    data = {}
    for k, f in files.items():
        if k == 'tuboid_id' or k == 'series_info':
            f = json.load(f)
        data[k] = f
    out = [api._put_tiled_tuboids([data], client_info={'username': auth.current_user()})]
    return jsonify(out)

