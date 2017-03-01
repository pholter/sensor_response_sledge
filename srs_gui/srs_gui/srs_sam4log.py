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
import pymqdatastream
import pymqdatastream.connectors.sam4log.pymqds_gui_sam4log as pymqds_gui_sam4log



class srssam4logMainWindow(pymqds_gui_sam4log.sam4logMainWindow):
    def __init__(self,*args,**kwargs):
        super(srssam4logMainWindow, self).__init__(*args,**kwargs)
        print('Init')



# If run from the command line
def main():
    print(sys.version_info)
    app = QtWidgets.QApplication(sys.argv)
    window = srssam4logMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

    
