#!/usr/bin/env python3

#
#

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except:
    from qtpy import QtCore, QtGui, QtWidgets


import numpy as np
import logging
import os,sys
import argparse
import multiprocessing
import yaml
import pymqdatastream
import pymqdatastream.connectors.todl.pymqds_gui_todl as pymqds_gui_todl
#import srs_plotxy
from srs_gui import srs_plotxy
from pymqdatastream.connectors.pyqtgraph import pyqtgraphDataStream
# Get a standard configuration
from pkg_resources import Requirement, resource_filename

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('srs_todl')
logger.setLevel(logging.DEBUG)

# Standard configuration file
filename_standard = resource_filename(Requirement.parse('srs_gui'),'srs_gui/srs_gui_config.yaml')
# Local configuration file
filename_local = 'srs_gui_config.yaml'


try:
    logger.info('Opening local config file')    
    config_file = open(filename_local)
except:
    logger.info('Opening standard config file')
    config_file = open(filename_standard)

if True:
    config = yaml.load(config_file)
    print(config)
    print('Overwriting todl config')
    pymqds_gui_todl.config = config

class srsloggerDevice(pymqds_gui_todl.todlDevice):
    """ A Sensor Response Sledge (SRS) logger Device
    """
    def __init__(self,*args,**kwargs):
        logger.debug('srsloggerDevice.__init__()')
        super(srsloggerDevice, self).__init__(*args,**kwargs)

        self._info_plot_bu.clicked.disconnect(self._plot_clicked_adc)
        self._info_plot_bu.clicked.connect(self._srs_plot_clicked)
        self.p_to_process = None
        self.p_from_process = None   
        # Use an modified setup
        self.setup_orig = self.setup
        self.setup = self.setup_local

    def setup_local(self,name=None, mainwindow = None):
        self.setup_orig(name,mainwindow)
        if(mainwindow is not None):
            print('Checking for other devices')
            for d in self.mainwindow.devices:
                print('Device:' + str(d.name))
                # Check if we have a srs logger
                if(d.name == 'srs sledge'):
                    print('Found a srs sledge!')
                    # Interconnect both
                    self.srs_sledge = d
                    d.srs_logger = self
                    d.w.srs_logger = self

    def _srs_plot_clicked(self):
        """
        
        Starts a pyqtgraph plotting process

        """

        logger.debug('Plotting the streams')
        # http://stackoverflow.com/questions/29556291/multiprocessing-with-qt-works-in-windows-but-not-linux
        # this does not work with python 2.7
        self.p_to_process,self.p_from_process = multiprocessing.Pipe()
        multiprocessing.set_start_method('spawn',force=True)
        addresses = []
        for stream in self.todl.Streams:
            print(stream.get_family())
            if(stream.get_family() == "todl adc"):
                addresses.append(self.todl.get_stream_address(stream))
                
        self._plotxyprocess = multiprocessing.Process(target =_start_pymqds_srsplotxy,args=(addresses,self.p_to_process,self.p_from_process))
        self._plotxyprocess.daemon = True # If we are done, it will be killes as well                
        self._plotxyprocess.start()            

        

def _start_pymqds_srsplotxy(addresses,p_to_process,p_from_process):
    """Start a pymqds_plotxy session and plots the streams given in the
    addresses list This function subscribes the stream twice, one for
    raw plotting, the other for response time measurement. Two pipes
    for interconnection with a sensor sledge are available.

    Args:
        addresses: List of addresses of pymqdatastream Streams

    """

    logger.debug("_start_pymqds_plotxy():" + str(addresses))

    logging_level = logging.DEBUG
    datastreams = []

    bufsize = 1000000
    plot_nth_point = 10
    freq = 2000
    tbuf = bufsize/freq
    print('Enough space in buffer for ' + str(tbuf) + ' seconds')
    
    for addr in addresses:
        datastream = pyqtgraphDataStream(name = 'srs_plot', logging_level=logging_level)
        stream = datastream.subscribe_stream(addr)
        print('HAllo,stream'+ str(stream))
        if(stream == None): # Could not subscribe
            logger.warning("_start_pymqds_plotxy(): Could not subscribe to:" + str(addr) + ' exiting plotting routine')
            return False
        

        datastream.set_stream_settings(stream, bufsize = int(bufsize/plot_nth_point), plot_data = True, ind_x = 1, ind_y = 2, plot_nth_point = plot_nth_point)
        datastream.plot_datastream(True)
        datastream.set_plotting_mode(mode='cont')
        datastreams.append(datastream)        
        # Subscribe to the same datastream, but now with a higher resolution
        datastream_meas = pyqtgraphDataStream(name = 'srs_meas', logging_level=logging_level)
        stream_meas = datastream_meas.subscribe_stream(addr)
        datastream_meas.set_stream_settings(stream_meas, bufsize = bufsize, plot_data = False, ind_x = 1, ind_y = 2, plot_nth_point = 1)
        datastream_meas.plot_datastream(True)
        datastreams.append(datastream_meas)



    app = QtWidgets.QApplication([])
    plotxywindow = srs_plotxy.srspyqtgraphMainWindow(datastream=datastreams[0],datastream_meas=datastreams[1],pipe_to_process=p_to_process,pipe_from_process = p_from_process)
    plotxywindow.show()
    sys.exit(app.exec_())    
    logger.debug("_start_pymqds_plotxy(): done")        



# If run from the command line
def main():
    print(sys.version_info)
    app = QtWidgets.QApplication(sys.argv)
    window = pymqds_gui_todl.todlMainWindow()
    #window = srstodlMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

    
