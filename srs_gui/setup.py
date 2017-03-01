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
          entry_points={ 'console_scripts': ['srs_gui=srs_gui.srs_gui:main',\
          'srs_sam4log=srs_gui.srs_sam4log:main'], },
          package_data = {'':['VERSION']},
          zip_safe=False)

else:
    print('srs_gui needs python > 3.4 ... ')
