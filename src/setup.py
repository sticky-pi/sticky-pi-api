from setuptools import setup, find_packages
exec(open('sticky_pi_api/_version.py').read())

setup(
    name='sticky_pi_api',
    version=__version__,
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['pandas',
                      'requests',
                      'python-dotenv',
                      'pillow',
                      'psutil',
                      'tqdm',
                      'joblib',
                      'sqlalchemy',
                      'imread',
                      'typeguard',
                      'passlib',
                      'itsdangerous',
                      'decorate_all_methods',
                      "requests_toolbelt",
                      'boto3'],
    extras_require={
        'remote_api': ['orjson', 'pymysql', 'mysqlclient', 'PyMySQL', 'Flask-HTTPAuth', 'retry'],
        'test': ['nose', 'pytest', 'pytest-cov', 'codecov', 'coverage'],
        'docs': ['mock', 'sphinx-autodoc-typehints', 'sphinx', 'sphinx_rtd_theme', 'recommonmark', 'mock']
    },
    test_suite='nose.collector'
)
