import os
import tempfile
import shutil
import sys
from sqlalchemy import create_engine
from sticky_pi_api.database.utils import Base
from sticky_pi_api.database.images_table import Images
from sticky_pi_api.database.users_tables import Users
from sticky_pi_api.database.uid_annotations_table import UIDAnnotations


# try:
# out = sys.argv[1]
# engine = create_engine('mysql+mysqlconnector', echo=True, )
temp_dir = tempfile.mkdtemp(prefix='sticky-pi-')
try:
    path = os.path.join(temp_dir, 'db.db')
    path_sql = os.path.join(temp_dir, 'db.sql')

    engine = create_engine('sqlite:///' + path)
    Base.metadata.create_all(engine, Base.metadata.tables.values())
    import subprocess
    import re
    process = subprocess.Popen(['sqlite3', path, '.dump'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    sql_code = stdout.decode('UTF8')
    sql_code = re.sub('^.*PRAGMA.*', '', sql_code)
    sql_code = re.sub('\"', '', sql_code)
    sql_code = re.sub('\sCONSTRAINT.*', '', sql_code)
    with open(path_sql, 'w') as f:
        f.write(sql_code)
    
    process = subprocess.Popen(['sql2dbml', path_sql, '--mysql'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    print(stdout.decode('UTF8'))


finally:
    shutil.rmtree(temp_dir)
    # engine = create_engine('sqlite:///' + path, echo=True)
    # Base.metadata.create_all(engine, Base.metadata.tables.values())
#
# except IndexError as e:
#     raise IndexError('Must provide a path for t file')