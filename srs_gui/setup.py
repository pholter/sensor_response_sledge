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
          entry_points={ 'console_scripts': ['srs_sledge=srs_gui.srs_sledge:main',\
          'srs_todl=srs_gui.srs_todl:main'], },
          package_data = {'':['VERSION'],'':['srs_gui_config.yaml']},
          zip_safe=False)

else:
    print('srs_gui needs python > 3.4 ... ')
