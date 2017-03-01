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
import pymqdatastream.connectors.qt.qt_service as datastream_qt_service
import pymqdatastream.connectors.pyqtgraph.pymqds_plotxy as pymqds_plotxy
from pymqdatastream.connectors.pyqtgraph.pymqds_plotxy import pyqtgraphDataStream,pyqtgraphMainWindow,pyqtgraphWidget
# Has to be imported after importing Qt5, otherwise Qt4/Qt5 problems occur
import pyqtgraph as pg


# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

logger = logging.getLogger('srs_plotxy')
logger.setLevel(logging.DEBUG)


class srspyqtgraphWidget(pymqds_plotxy.pyqtgraphWidget):
    def __init__(self,*args,**kwargs):
        super(srspyqtgraphWidget, self).__init__(*args,**kwargs)
        
        self.vlines = []
        # Add a meas button
        self.button_meas = QtWidgets.QPushButton('Measure', self)
        self.button_meas.clicked.connect(self.handle_meas)
        self.button_meas.setCheckable(True)
        self.button_bottom_layout.removeWidget(self.button_layout_stretch)
        self.button_bottom_layout.removeWidget(self.label_meas)
        self.button_bottom_layout.addWidget(self.button_meas)
        self.button_layout_stretch = self.button_bottom_layout.addStretch()
        self.button_bottom_layout.addWidget(self.label_meas)

        self.pyqtgraph_axes.scene().sigMouseClicked.connect(self.srsmouseClicked)
        self.pyqtgraph_axes.scene().sigMouseMoved.connect(self.srsmouseMoved)        

    def srsmouseClicked(self,evt):
        #col = 
        col = pg.mkPen(0.5,width=3)
        colsymbol = pg.mkPen(color=QtGui.QColor(100,255,100),width=4)         
        print('Clicked: ' + str(evt.pos()))
        mousePoint = self.vb.mapSceneToView(evt.scenePos())
        if(self.button_meas.isChecked()):
            if(len(self.vlines) == 2): # A start and end lines is defined
                xlim = (self.vlines[0].value(),self.vlines[1].value())
                #xlim = sort(xlim)
                print('Got two lines, xlim is:' + str(xlim))
                self.vlines[1].setPos(mousePoint.x())
                self.vlines.append(None)
                # Get the data for the first stream
                for i,stream in enumerate(self.Datastream.Streams):

                    if(stream.stream_type == 'substream'):
                        # Get the data
                        ind_start = stream.pyqtgraph_npdata['ind_start']
                        ind_end = stream.pyqtgraph_npdata['ind_end']                        
                        xd = stream.pyqtgraph_npdata['x'][ind_start:ind_end].copy()
                        yd = stream.pyqtgraph_npdata['y'][ind_start:ind_end].copy()
                        ind = (xd > min(xlim)) & (xd < max(xlim))
                        if(sum(ind) > 0):
                            xd = xd[ind]
                            yd = yd[ind]
                            self.xmeas = xd.copy()
                            self.ymeas = yd.copy()
                            self.meas_line = pg.PlotDataItem( pen=col,name = 'measured')
                            li = self.pyqtgraph_axes.addItem(self.meas_line)
                            self.meas_line.setData(x=xd,y=yd, pen=col)
                            # Calculate min, max, time and 63 percent
                            # TODO, this can also be done in an extra function
                            #START
                            self.meas_start = pg.PlotDataItem( pen=None,symbol='+',name = 'measured_start')
                            li_start = self.pyqtgraph_axes.addItem(self.meas_start)                            
                            self.meas_start.setData(x=[xd[0],],y=[yd[0],],pen=None)
                            #STOP
                            self.meas_stop = pg.PlotDataItem( pen=None,symbol='+',name = 'measured_stop')
                            li_stop = self.pyqtgraph_axes.addItem(self.meas_stop)                            
                            self.meas_stop.setData(x=[xd[-1],],y=[yd[-1],],pen=None)
                            # 63.2%
                            dy = yd[-1] - yd[0]
                            fac = 0.632
                            dyfac = dy * fac
                            yfac = yd[0] + dyfac
                            indfaclog = yd > yfac
                            indfac = 0
                            if(sum(indfaclog) > 0):
                                indfac = np.where(indfaclog)[0][0]
                                xfac = xd[indfac]
                                yfac = yd[indfac]
                                tfac = xd[indfac] - xd[0]
                                self.meas_fac = pg.PlotDataItem( pen=None,symbol='+',name = 'measured_fac')
                                li_fac = self.pyqtgraph_axes.addItem(self.meas_fac)                            
                                self.meas_fac.setData(x=[xfac,],y=[yfac,],pen=None)
                                facstr = '63.2 per cent (%.3f of %.3f) in %f s' % (yfac,yd[-1],tfac)
                            else:
                                facstr = 'Did not find data'

                            self.meas_text = pg.TextItem(text=facstr)
                            self.meas_text.setPos(xd[indfac],yd[indfac])
                            text_fac = self.pyqtgraph_axes.addItem(self.meas_text)                            

                
            if(len(self.vlines) == 1): 
                vLine = pg.InfiniteLine(angle=90, movable=False)            
                self.pyqtgraph_axes.addItem(vLine, ignoreBounds=True)
                self.vlines.append(vLine)
                vLine.setPos(mousePoint.x())                
                



    def srsmouseMoved(self,evt):
        pos = (evt.x(),evt.y())
        mousePoint = self.vb.mapSceneToView(evt)
        if(len(self.vlines) > 0):
            vline = self.vlines[-1]            
            if(vline != None):
                vline.setPos(mousePoint.x())
            
        
    def handle_meas(self):
        logger.debug('Handle measure')
        self.button_meas.setCheckable(True)
        if(self.button_meas.isChecked()):
            self.meas_line = None            
            vLine = pg.InfiniteLine(angle=90, movable=False)
            self.vlines.append(vLine)
            self.pyqtgraph_axes.addItem(vLine, ignoreBounds=True)
        else:
            for vLine in self.vlines:
                self.pyqtgraph_axes.removeItem(vLine)

            if(self.meas_line != None):
                self.pyqtgraph_axes.removeItem(self.meas_line)
                self.pyqtgraph_leg.removeItem('measured')
                
            self.vlines = []




class srspyqtgraphMainWindow(QtWidgets.QMainWindow):
    def __init__(self, datastream = None, logging_level = logging.INFO):
        QtWidgets.QMainWindow.__init__(self)
        
        self.statusBar()

        # Add the pyqtgraphWidget
        self.pyqtgraphs = []
        mainwidget = QtWidgets.QWidget(self)        
        self.layout = QtWidgets.QVBoxLayout(mainwidget)
        self.pyqtgraphwidget = srspyqtgraphWidget(datastream = datastream, logging_level = logging_level)
        self.layout.addWidget(self.pyqtgraphwidget)
        self.pyqtgraphs.append(self.pyqtgraphwidget)
        self.logging_level = logging_level
        mainwidget.setFocus()
        self.setCentralWidget(mainwidget)
        #self.show()        


def main():
    logging_level = logging.DEBUG
    print('Hallo!')
    datastream = pyqtgraphDataStream(name = 'srs_plotxy', logging_level=logging_level,bufsize=5000000)


    app = QtWidgets.QApplication(sys.argv)
    window = srspyqtgraphMainWindow(datastream = datastream, logging_level = logging_level)
    window.show()
    sys.exit(app.exec_())



if __name__ == "__main__":
    main()    
