from setuptools import setup, find_packages
exec(open('sticky_pi_client/_version.py').read())

setup(
    name='sticky_pi_client',
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
                      'opencv_python',
                      'psutil',
                      'tqdm',
                      'joblib',
                      'sqlalchemy',
                      'imread',
                      'typeguard'],
    tests_require=['nose'],
    docs_require=['sphinx', 'sphinx_rtd_theme', 'recommonmark', 'mock', 'sphinx-autodoc-typehints'],
    test_suite='nose.collector'
)
