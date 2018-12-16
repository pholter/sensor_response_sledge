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
<<<<<<< HEAD
import pylab as pl

=======
import pyqtgraph.exporters
>>>>>>> 55a2b71765e38a7c8d62a9c2e80a6c09ea7c9d22

# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

logger = logging.getLogger('srs_plotxy')
logger.setLevel(logging.DEBUG)


class srspyqtgraphWidget(pymqds_plotxy.pyqtgraphWidget):
    """This is a specialised pyqtgraphWidget with function needed for the
    sensor response sledge. Namely to choose regions for respone time
    measurements
       Args: srs_windowtype: Either "plot" or "measure"

    """
    def __init__(self,*args, srs_windowtype="plot", srs_plotwidget=None, pipe_to_process=None, pipe_from_process=None, **kwargs):
        super(srspyqtgraphWidget, self).__init__(*args,**kwargs)
<<<<<<< HEAD
        
        self.vlines   = []
        self.tmplines = []        
=======
        self.vlines = []
        self.xmeas = None
        self.ymeas = None
        self.srs_plotwidget = srs_plotwidget
        self.pipe_to_process = pipe_to_process
        self.pipe_from_process = pipe_from_process        
>>>>>>> 55a2b71765e38a7c8d62a9c2e80a6c09ea7c9d22
        # Add a meas button
        if(srs_windowtype=="plot"):
            self.button_meas = QtWidgets.QPushButton('Choose Interval', self)
            self.button_meas.clicked.connect(self.handle_interval)
            self.button_meas.setCheckable(True)
            self.pyqtgraph_axes.scene().sigMouseClicked.connect(self.srsmouseClicked_interval)
            # If we are in plot mode, check if we have external data in the pipe, if there is something simply plot a line
            timer = QtCore.QTimer(self)
            timer.timeout.connect(self.check_pipe)
            timer.start(500)
            self.check_interval_timer = timer            

        else:
            self.button_meas = QtWidgets.QPushButton('Measure', self)
            self.button_meas.clicked.connect(self.handle_meas)
            self.button_meas.setCheckable(True)
            self.pyqtgraph_axes.scene().sigMouseClicked.connect(self.srsmouseClicked_meas)
            # If we are in measure mode, check if the plot widget has data, if yes, check it            
            timer = QtCore.QTimer(self)
            timer.timeout.connect(self.check_interval)
            timer.start(500)
            self.check_interval_timer = timer

            
        self.pyqtgraph_axes.scene().sigMouseMoved.connect(self.srsmouseMoved)                                
        self.button_savefig = QtWidgets.QPushButton('Screenshot', self)
        self.button_savefig.clicked.connect(self.handle_savefig)
        self.button_bottom_layout.removeWidget(self.button_layout_stretch)
        self.button_bottom_layout.removeWidget(self.label_meas)
        self.button_bottom_layout.addWidget(self.button_meas)
        self.button_bottom_layout.addWidget(self.button_savefig)        
        self.button_layout_stretch = self.button_bottom_layout.addStretch()
        self.button_bottom_layout.addWidget(self.label_meas)


    def check_pipe(self):
        if True:
            try:
                ismsg = self.pipe_from_process.poll()    # Read from the output pipe and do nothing
                if(ismsg):
                    msg = self.pipe_from_process.recv()    # Read from the output pipe and do nothing
                    print('Got message from srs sledge:' + str(msg))
                    # Create a line:
                    for i,stream in enumerate(self.Datastream.Streams):
                        if(stream.stream_type == 'substream'):
                            # Get the data
                            ind_start = stream.pyqtgraph_npdata['ind_start']
                            ind_end = stream.pyqtgraph_npdata['ind_end']
                            xl = stream.pyqtgraph_npdata['x'][ind_start:ind_end].max()

                    col = pg.mkPen(color=(200, 20, 20),width=1)                                                
                    vLine = pg.InfiniteLine(angle=90, movable=False, pen=col)            
                    self.pyqtgraph_axes.addItem(vLine, ignoreBounds=True)
                    vLine.setPos(xl)
                            
            except Exception as e:
                print('Exception ' + str(e))


    def check_interval(self):
        """ Checks if the plotting widget has an interval, if yes take it and plot it into this window
        """
        #print(self.srs_plotwidget.xmeas)
        if(self.srs_plotwidget.xmeas is not None):
            print('Found an interval, lets get the data')
            xmin = self.srs_plotwidget.xmeas.min()
            xmax = self.srs_plotwidget.xmeas.max()
            self.srs_plotwidget.xmeas = None
            self.srs_plotwidget.ymeas = None
            # Remove old line, if existent
            try:
                self.pyqtgraph_axes.removeItem(self.meas_line_high)
            except:
                pass
            for i,stream in enumerate(self.Datastream.Streams):
                # The first stream is the stream we want to have
                if(stream.stream_type == 'substream'):
                    ind_start = stream.pyqtgraph_npdata['ind_start']
                    ind_end = stream.pyqtgraph_npdata['ind_end']                    
                    xd_tmp = stream.pyqtgraph_npdata['x'][ind_start:ind_end]
                    ind = (xd_tmp >= xmin) & (xd_tmp <= xmax)                    
                    xd = stream.pyqtgraph_npdata['x'][ind_start:ind_end][ind]
                    yd = stream.pyqtgraph_npdata['y'][ind_start:ind_end][ind]
                    col = pg.mkPen(0.5,width=1)                    
                    self.meas_line_high = pg.PlotDataItem( pen=col,name = 'measured')
                    li = self.pyqtgraph_axes.addItem(self.meas_line_high)
                    self.meas_line_high.setData(x=xd,y=yd, pen=col)

        
    def srsmouseClicked_meas(self,evt):
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
                            self.tmplines.append(self.meas_line)
                            self.tmplines.append(li)
                            # Calculate min, max, time and 63 percent
                            # TODO, this can also be done in an extra function
                            #START
                            self.meas_start = pg.PlotDataItem( pen=None,symbol='+',name = 'measured_start')
                            self.tmplines.append(self.meas_start)
                            li_start = self.pyqtgraph_axes.addItem(self.meas_start)                            
                            self.meas_start.setData(x=[xd[0],],y=[yd[0],],pen=None)
                            self.tmplines.append(li_start)
                            #STOP
                            self.meas_stop = pg.PlotDataItem( pen=None,symbol='+',name = 'measured_stop')
                            li_stop = self.pyqtgraph_axes.addItem(self.meas_stop)                            
                            self.meas_stop.setData(x=[xd[-1],],y=[yd[-1],],pen=None)
                            self.tmplines.append(li_stop)                                                        
                            self.tmplines.append(self.meas_stop)                            
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
                                self.tmplines.append(li_fac)
                                self.tmplines.append(self.meas_fac)
                            else:
                                facstr = 'Did not find data'

                            self.meas_text = pg.TextItem(text=facstr)
                            self.meas_text.setPos(xd[indfac],yd[indfac])
                            text_fac = self.pyqtgraph_axes.addItem(self.meas_text)
<<<<<<< HEAD
                            self.tmplines.append(self.meas_text)
                            self.tmplines.append(text_fac)

                            # Make a matplotlib plot for fancy plot
                            # TODO, create a name
                            figname = 'NTC response'
                            pl.figure(figname)
                            pl.clf()
                            #pl.ion()
                            pl.plot(xd,yd)
                            pl.ylabel('Voltage')
                            pl.xlabel('Time [s]')                            
                            pl.draw()
                            pl.show()
=======
>>>>>>> 55a2b71765e38a7c8d62a9c2e80a6c09ea7c9d22

                
            if(len(self.vlines) == 1): 
                vLine = pg.InfiniteLine(angle=90, movable=False)            
                self.pyqtgraph_axes.addItem(vLine, ignoreBounds=True)
                self.vlines.append(vLine)
                vLine.setPos(mousePoint.x())


    def srsmouseClicked_interval(self,evt):
        """Handle after an interval is choosen
        """
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
                            # This is the data                                                        
                            self.xmeas = xd.copy()
                            self.ymeas = yd.copy()

                            self.meas_line = pg.PlotDataItem( pen=col,name = 'measured')
                            li = self.pyqtgraph_axes.addItem(self.meas_line)
                            self.meas_line.setData(x=xd,y=yd, pen=col)


                
            if(len(self.vlines) == 1): 
                vLine = pg.InfiniteLine(angle=90, movable=False)            
                self.pyqtgraph_axes.addItem(vLine, ignoreBounds=True)
                self.vlines.append(vLine)
                vLine.setPos(mousePoint.x())
                


    def srsmouseMoved(self,evt):
        """Function if mouse has been moved
        """
        pos = (evt.x(),evt.y())
        mousePoint = self.vb.mapSceneToView(evt)
        if(len(self.vlines) > 0):
            vline = self.vlines[-1]            
            if(vline != None):
                vline.setPos(mousePoint.x())
            
        
    def handle_meas(self):
        """Function to handle the interval choosing, here a line is created,
        which is then used for srsmouseClicked_*
        """
        
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

                
            for vLine in self.tmplines:
                self.pyqtgraph_axes.removeItem(vLine)
                

            if(self.meas_line != None):
                self.pyqtgraph_axes.removeItem(self.meas_line)
                self.pyqtgraph_axes.removeItem(self.meas_text)
                self.pyqtgraph_axes.removeItem(self.meas_fac)
                self.pyqtgraph_axes.removeItem(self.meas_start)
                self.pyqtgraph_axes.removeItem(self.meas_stop)                
                self.pyqtgraph_leg.removeItem('measured')
<<<<<<< HEAD
                self.pyqtgraph_leg.removeItem('measured_stop')
                self.pyqtgraph_leg.removeItem('measured_start')
                self.pyqtgraph_leg.removeItem('measured_fac')                
=======
                self.pyqtgraph_leg.removeItem('measured_fac')
                self.pyqtgraph_leg.removeItem('measured_start')
                self.pyqtgraph_leg.removeItem('measured_stop')

>>>>>>> 55a2b71765e38a7c8d62a9c2e80a6c09ea7c9d22
                
            self.vlines = []


    def handle_interval(self):
        """Function to handle the interval choosing, here a line is created,
        which is then used for srsmouseClicked_*

        """
        logger.debug('Handle interval')
        # Create a new line
        if(self.button_meas.isChecked()):
            self.meas_line = None            
            vLine = pg.InfiniteLine(angle=90, movable=False)
            self.vlines.append(vLine)
            self.pyqtgraph_axes.addItem(vLine, ignoreBounds=True)
        # Remove all lines
        else:
            for vLine in self.vlines:
                self.pyqtgraph_axes.removeItem(vLine)

            if(self.meas_line != None):
                self.pyqtgraph_axes.removeItem(self.meas_line)
                self.pyqtgraph_leg.removeItem('measured')


            self.xmeas = None
            self.ymeas = None           
            self.vlines = []                

            
    def handle_savefig(self):
        exporter = pg.exporters.ImageExporter(self.pyqtgraph_axes.plotItem)
        # TODO, add a proper filename here
        exporter.export('filename.png')
        



class srspyqtgraphMainWindow(QtWidgets.QMainWindow):
    def __init__(self, datastream = None, datastream_meas = None, logging_level = logging.INFO, pipe_to_process=None, pipe_from_process = None):
        QtWidgets.QMainWindow.__init__(self)
        
        self.statusBar()
        # Add the pyqtgraphWidget
        self.pyqtgraphs = []
        mainwidget = QtWidgets.QWidget(self)        
        self.layout = QtWidgets.QVBoxLayout(mainwidget)
        # Create a pyqtgraphwidget for realtime data
        self.pyqtgraphwidget = srspyqtgraphWidget(datastream = datastream, logging_level = logging_level, srs_windowtype="plot", pipe_to_process=pipe_to_process, pipe_from_process = pipe_from_process)
        self.layout.addWidget(self.pyqtgraphwidget)
        # Create a seond pyqtgraphwidget for the data to be measured for response time
        self.pyqtgraphwidget_meas = srspyqtgraphWidget(datastream = datastream_meas, logging_level = logging_level, srs_windowtype="measure",srs_plotwidget=self.pyqtgraphwidget)
        self.layout.addWidget(self.pyqtgraphwidget_meas)        
        #
        self.pyqtgraphs.append(self.pyqtgraphwidget)
        self.pyqtgraphs.append(self.pyqtgraphwidget_meas)        
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
