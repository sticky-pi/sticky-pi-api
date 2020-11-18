import os
import dotenv
import logging


class RequiredConfVar(object):
    pass


class BaseAPIConf(dict):
    _config_vars={
        'SECRET_API_KEY': RequiredConfVar(),
        'MYSQL_HOST': None
    }

    def __init__(self, env_file: str = None, **kwargs):
        super().__init__()
        if env_file:
            if not os.path.isfile(env_file):
                raise FileExistsError("No such file: %s", env_file)
            dotenv.load_dotenv(env_file)

        for var_name, default_value in self._config_vars.items():
            # keyword arguments > ENV > ENV FILE
            if var_name in kwargs.keys():
                self[var_name] = kwargs[var_name]
            else:
                self[var_name] = os.getenv(var_name)

            if not self[var_name]:
                if isinstance(default_value, RequiredConfVar):
                    raise ValueError("No value provided for MANDATORY environment variable `%s'" % var_name)
                else:
                    logging.info("No value provided for OPTIONAL environment variable `%s'. "
                                 "Using internal default value" % var_name)
                    self[var_name] = default_value

                # self[var] = os.getenv(var)

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


class LocalAPIConf(BaseAPIConf):
    _config_vars = {
        'SECRET_API_KEY': "endjlwenmfkwe",
        'LOCAL_DIR': RequiredConfVar()
    }
