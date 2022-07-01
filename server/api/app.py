import flask
from flask import Flask, abort, request, g, url_for, Response, Request
from sqlalchemy.exc import OperationalError, IntegrityError
from flask_httpauth import HTTPBasicAuth
# from flask.json import JSONEncoder
from flask import request
from retry import retry
from decimal import Decimal
import datetime
import logging
import json
import os
import io
import orjson

from sticky_pi_api.utils import profiled
from sticky_pi_api.configuration import RemoteAPIConf
from sticky_pi_api.specifications import RemoteAPI
from sticky_pi_api.utils import datetime_to_string


def json_default(o):
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError


def jsonify(obj):
    return app.response_class(
        orjson.dumps(obj, option=orjson.OPT_NAIVE_UTC | orjson.OPT_UTC_Z | orjson.OPT_OMIT_MICROSECONDS,
                     default=json_default) +
        b"\n",
        mimetype=app.config["JSONIFY_MIMETYPE"],
    )


# just wait for database to be ready
@retry(exceptions=OperationalError, delay=2, max_delay=10)
def get_api(config: RemoteAPIConf) -> RemoteAPI:
    return RemoteAPI(config)


#  to create initial admin user if does not exist
def create_initial_user(api, username, password):
    admin_user = {'username': username,
                  'password': password,
                  'is_admin': True}

    assert admin_user['username'], 'Cannot find username in env'
    assert admin_user['password'] and len(admin_user['password']) > 10, \
        f'User {username} password missing or too short'
    try:
        api.put_users([admin_user])
    except IntegrityError as e:
        # fixme, we could actually check that assertion
        logging.debug(f'User {username} already exists?')


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

create_initial_user(api, os.getenv('API_ADMIN_NAME'), os.getenv('API_ADMIN_PASSWORD'))

# user for the universal insect detector BG process
create_initial_user(api, os.getenv('UID_USER'), os.getenv('UID_PASSWORD'))


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



app = Flask(__name__)
# app.json_encoder = CustomJSONEncoder
# app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

template_function_profiled = """
@app.route('/%s%s', methods = ['POST'])
@auth.login_required(%s)
def %s(**kwargs):
    with profiled():
        data = request.get_json()
        client_info = {'username':auth.current_user()}
        out = api.%s(data, client_info=client_info, **kwargs)
        return jsonify(out)
"""

template_function = """
@app.route('/%s%s', methods = ['POST'])
@auth.login_required(%s)
def %s(**kwargs):
    data = request.get_json()
    client_info = {'username':auth.current_user()}
    out = api.%s(data, client_info=client_info, **kwargs)
    return jsonify(out)
"""

if conf.API_PROFILE.lower() in ['true', '1']:
    template_function = template_function_profiled


def make_endpoint(method, role='admin', what=False):
    if not role:
        role = ""
    elif isinstance(role, str):
        role = str([role])

    endpoint = method.__name__
    sub_route = "/<what>" if what else ""
    role_str = "role=%s" % role if role else ""
    assert endpoint in dir(api), "all endpoint must point to api methods. got %s" % endpoint
    exec(template_function % (endpoint, sub_route, role_str, endpoint, endpoint))


@app.route('/get_token', methods=['POST'])
@auth.login_required()
def get_token():
    client_info = {'username': auth.current_user()}
    out = api.get_token(client_info=client_info)
    return jsonify(out)


make_endpoint(api.get_users, role='admin')
make_endpoint(api.put_users, role='admin')

# todo
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


#
# Content-Type: multipart/form-data; boundary=9b2df423359acd7e747678031df5e345
# Content-Length: 1070631
# Host: spi_nginx
# User-Agent: python-requests/2.27.1
# Accept-Encoding: gzip, deflate
# Accept: */*
# Connection: keep-alive
# Authorization: Basic ZXlKcFpDSTZNWDAuWW9oYUJRLk43eG9hUE1MV2xrTV8zZ0dGZUZHWHFXc0NERTo=
#
#
# ImmutableMultiDict([])
# ImmutableMultiDict([('512858f4.2022-05-17_18-46-57.jpg', <FileStorage: '512858f4.2022-05-17_18-46-57.jpg' (None)>)])

@app.route('/_put_new_images', methods=['POST'])
@auth.login_required(role=["admin", "read_write_user"])
def _put_new_images():
    files = request.files
    assert len(files) > 0
    out = []
    for k, f in files.items():
        md5 = None
        if request.form:
            d = request.form.to_dict()
            if f"{k}.md5" in d:
                md5 = d[f"{k}.md5"]

        out += api.put_images({f: md5}, client_info={'username': auth.current_user()})
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
