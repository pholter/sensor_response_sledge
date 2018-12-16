from setuptools import setup
import os

import sys

if sys.version_info >= (3,4):

    ROOT_DIR='srs_gui'
    with open(os.path.join(ROOT_DIR, 'VERSION')) as version_file:
        version = version_file.read().strip()

    setup(name='srs_gui',
          version=version,
          description='GUI for the sensor response sledge',
          url='https://github.com/sensor_response_sledge',
          author='Peter Holtermann',
          author_email='peter.holtermann@io-warnemuende.de',
          license='GPLv03',
          packages=['srs_gui'],
          scripts = [],
<<<<<<< HEAD
          entry_points={ 'console_scripts': ['srs_sledge=srs_gui.srs_sledge:main',\
          'srs_todl=srs_gui.srs_todl:main'], },
          package_data = {'':['VERSION']},
=======
          entry_points={ 'console_scripts': ['srs_sledge_control=srs_gui.srs_sledge:main',\
          'srs_logger_control=srs_gui.srs_todl:main'], },
          package_data = {'':['VERSION'],'':['srs_gui_config.yaml']},
>>>>>>> 55a2b71765e38a7c8d62a9c2e80a6c09ea7c9d22
          zip_safe=False)

else:
    print('srs_gui needs python > 3.4 ... ')
