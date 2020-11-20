from setuptools import setup, find_packages
exec(open('sticky_pi_api/_version.py').read())

setup(
    name='sticky_pi_api',
    version=__version__,
    long_description=__doc__,
    packages=find_packages(),
    scripts=['bin/sync_local_images.py'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['numpy',
                      'pandas',
                      'requests',
                      'futures',
                      'python-dotenv',
                      'boto3',
                      'pillow',
                      'psutil',
                      'tqdm',
                      'joblib',
                      'sqlalchemy',
                      'imread',
                      'typeguard',
                      'passlib',
                      'itsdangerous'],
    extras_require={
        'test': ['nose', 'pytest', 'pytest-cov', 'codecov'],
        'docs': ['mock', 'sphinx-autodoc-typehints', 'sphinx', 'sphinx_rtd_theme', 'recommonmark', 'mock']
    },
    test_suite='nose.collector'
)
