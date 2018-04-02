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
import pymqdatastream
import pymqdatastream.connectors.todl.pymqds_gui_todl as pymqds_gui_todl
#import srs_plotxy
from srs_gui import srs_plotxy
from pymqdatastream.connectors.pyqtgraph import pyqtgraphDataStream

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('srs_todl')
logger.setLevel(logging.DEBUG)

class srstodlMainWindow(pymqds_gui_todl.todlMainWindow):
    def __init__(self,*args,**kwargs):
        super(srstodlMainWindow, self).__init__(*args,**kwargs)
        self._info_plot_bu.clicked.disconnect(self._plot_clicked)
        self._info_plot_bu.clicked.connect(self._srs_plot_clicked)                
        print('Init')

    def _srs_plot_clicked(self):
        """
        
        Starts a pyqtgraph plotting process

        """

        logger.debug('Plotting the streams')
        # http://stackoverflow.com/questions/29556291/multiprocessing-with-qt-works-in-windows-but-not-linux
        # this does not work with python 2.7 
        multiprocessing.set_start_method('spawn',force=True)
        addresses = []
        for stream in self.todl.Streams:
            print(stream.get_family())
            if(stream.get_family() == "todl adc"):
                addresses.append(self.todl.get_stream_address(stream))
                
        self._plotxyprocess = multiprocessing.Process(target =_start_pymqds_srsplotxy,args=(addresses,))
        self._plotxyprocess.start()    



def _start_pymqds_srsplotxy(addresses):
    """
    
    Start a pymqds_plotxy session and plots the streams given in the addresses list
    Args:
        addresses: List of addresses of pymqdatastream Streams
    
    """

    logger.debug("_start_pymqds_plotxy():" + str(addresses))

    logging_level = logging.DEBUG
    datastreams = []
    
    for addr in addresses:
        datastream = pyqtgraphDataStream(name = 'plotxy_cont', logging_level=logging_level)
        stream = datastream.subscribe_stream(addr)
        print('HAllo,stream'+ str(stream))
        if(stream == None): # Could not subscribe
            logger.warning("_start_pymqds_plotxy(): Could not subscribe to:" + str(addr) + ' exiting plotting routine')
            return False
        

        datastream.set_stream_settings(stream, bufsize = 500000, plot_data = True, ind_x = 1, ind_y = 2, plot_nth_point = 1)
        datastream.plot_datastream(True)
        datastream.set_plotting_mode(mode='cont')        
        datastreams.append(datastream)

        if(False):
            datastream_xr = pyqtgraphDataStream(name = 'plotxy_xr', logging_level=logging_level)
            stream_xr = datastream_xr.subscribe_stream(addr)
            datastream_xr.init_stream_settings(stream_xr, bufsize = 5000, plot_data = True, ind_x = 1, ind_y = 2, plot_nth_point = 6)
            datastream_xr.plot_datastream(True)
            datastream_xr.set_plotting_mode(mode='xr',xl=5)        
            datastreams.append(datastream_xr)        


    app = QtWidgets.QApplication([])
    plotxywindow = srs_plotxy.srspyqtgraphMainWindow(datastream=datastreams[0])
    #plotxywindow = pymqds_plotxy.pyqtgraphMainWindow(datastream=datastreams[0])
    if(False):
        for i,datastream in enumerate(datastreams):
            if(i > 0):
                plotxywindow.add_graph(datastream=datastream)
        
    plotxywindow.show()
    sys.exit(app.exec_())    
    logger.debug("_start_pymqds_plotxy(): done")        



# If run from the command line
def main():
    print(sys.version_info)
    app = QtWidgets.QApplication(sys.argv)
    window = srstodlMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

    
