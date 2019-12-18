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
import pylab as pl
import pyqtgraph.exporters
import datetime

# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

logger = logging.getLogger('srs_plotxy')
logger.setLevel(logging.DEBUG)

def plot_sensorfile(filename):
#if True:
    data = np.loadtxt(filename)
    x = data[0,:]
    y = data[1,:]
    meas_ind = data[2,:].astype(bool)
    ind_start = where(meas_ind)[0][0]
    indfac_abs = where(meas_ind)[0][-1]    
    figname = 'NTC response'
    #tistr = 'Sensor: ' + sensorname + ' Speed: ' + sensorspeed + r'm s$^{-1}$' + ' Response time: ' + ms_str + ' ms'
    dt = 0.3
    XL = [x[meas_ind].min() - dt,x[meas_ind].min() + dt]
    fig = pl.figure(figname)
    fig.set_size_inches(11.7,8.3)
    pl.clf()
    pl.plot(x,y,'-',color='gray')    
    pl.plot(x[meas_ind],y[meas_ind],'-k')
    pl.plot(x[ind_start:indfac_abs],y[ind_start:indfac_abs],'-r')
    pl.xlim(XL)
    #pl.title(tistr)
    pl.ylabel('Voltage')
    pl.xlabel('Time [s]')                            
    pl.draw()
    plotfile = filename + '.pdf'
    print('Saving plot to file:'+ plotfile)
    pl.savefig(plotfile)
    pl.show()        

# Pyqtgraph plot widget
class pg_measure(QtWidgets.QWidget):
    def __init__(self,x=[1,2,3],y=[1,2,3],sensorname=''):
        print('Hallohallo')
        self.dpath = './'
        self.vlines = []
        self.tmplines = []
        super(QtWidgets.QWidget, self).__init__()
        self.layout = QtWidgets.QGridLayout(self)        
        self.plot = pg.PlotWidget()
        self.pyqtgraph_axes = self.plot
        # Add a position label
        self.vb = self.pyqtgraph_axes.plotItem.vb                
        self.pyqtgraph_axes.scene().sigMouseMoved.connect(self.srsmouseMoved)
        self.pyqtgraph_axes.scene().sigMouseClicked.connect(self.srsmouseClicked_meas)        
        self.button_meas = QtWidgets.QPushButton('Measure', self)
        self.button_meas.clicked.connect(self.handle_meas)
        self.button_meas.setCheckable(True)
        self.button_save = QtWidgets.QPushButton('Save', self)
        self.button_save.clicked.connect(self.handle_save)
        self.button_invert = QtWidgets.QPushButton('V larger', self)
        self.button_invert.clicked.connect(self.handle_invert)        
        self.line_sensorname     = QtWidgets.QLineEdit()
        self.line_sensorspeed    = QtWidgets.QLineEdit()
        self.line_sensorcomment = QtWidgets.QLineEdit()
        self.line_sensorname.setText(sensorname)

        self.savename     = QtWidgets.QLineEdit() # Lineedit showing the filenames of the saved files
        self.savename.setReadOnly(True)
        #self.savename.setDisabled(True)        
        
        self.layout.addWidget(self.plot,1,1,1,6)
        self.layout.addWidget(QtWidgets.QLabel('Sensorname') ,2,1)
        self.layout.addWidget(self.line_sensorname,2,2)
        self.layout.addWidget(QtWidgets.QLabel('Sensorspeed'),2,3)
        self.layout.addWidget(self.line_sensorspeed,2,4)
        self.layout.addWidget(QtWidgets.QLabel('Comment'),2,5)
        self.layout.addWidget(self.line_sensorcomment,2,6)                
        self.layout.addWidget(self.button_meas,3,1)
        self.layout.addWidget(self.button_invert,3,2)
        self.layout.addWidget(self.button_save,3,3)
        self.layout.addWidget(self.savename,3,4,1,3)        

        td = x.max()-x.min()
        f = len(x)/td
        print('Freq:',str(f))
        self.plot.plot(x,y)
        self.x = x.copy()
        self.y = y.copy()

    def handle_invert(self):
        if(self.button_invert.text() == 'V larger'):
            self.button_invert.setText('V smaller')
        else:
            self.button_invert.setText('V larger')

    def handle_save(self):
        """ Function to save the plot and the underlying data into a pdf and csv file
        """
        print('Save',len(self.vlines))        
        if(len(self.vlines) >= 2): # A start and end lines is defined
            ms_str     = '{:04.1f}'.format(self.tfac*1000)
            ind_start  = np.where(self.meas_ind)[0][0]
            indfac_abs = np.where(self.meas_ind)[0][self.indfac]
        else:
            self.tfac  = 0
            ms_str     = '{:04.1f}'.format(0)
            ind_start  = 0
            indfac_abs = 0
            self.meas_ind = self.x > 0
            self.meas_ind[:] = True
        if True:
            print('Save')
            # Make a matplotlib plot for fancy plot
            # TODO, create a name
            sensorname = self.line_sensorname.text()
            sensorspeed= self.line_sensorspeed.text()
            comment    = self.line_sensorcomment.text()            
            tnow       = datetime.datetime.now()
            tstr       = tnow.strftime('%Y-%m-%d_%H%M%S')
            filename   = self.dpath + tstr + '-' + str(ind_start) + '-' + str(indfac_abs) + '_' + sensorname + '_' + sensorspeed + '_ms-1_' + '_' + comment + '_rp' + ms_str
            print('filename',filename)
            indfac     = self.x * 0
            indfac[self.meas_ind] = 1
            indfac[indfac_abs+1:] = 0
            data       = np.asarray((self.x,self.y,self.meas_ind,indfac))
            datafile   = filename + '.txt'
            print('Saving data to file:' + datafile)
            hdrstr = 'Response time file of sensor ' + str(sensorname) + ' with speed ' + sensorspeed
            np.savetxt(datafile,data,fmt='%010.6f',header=hdrstr)
            print('Plotting data')
            figname = 'NTC response'
            tistr = 'Sensor: ' + sensorname + ' Speed: ' + sensorspeed + r' m s$^{-1}$' + ' Response time: ' + ms_str + ' ms'
            fig = pl.figure(figname)
            dt = 0.1
            XL = [self.x[self.meas_ind].min() - dt,self.x[self.meas_ind].max() + dt]            
            fig.set_size_inches(11.7,8.3)
            pl.clf()
            pl.plot(self.x,self.y,'-',color='gray',lw=1.0)            
            pl.plot(self.x[self.meas_ind],self.y[self.meas_ind],'-k',lw=2.0)
            pl.plot(self.x[ind_start:indfac_abs],self.y[ind_start:indfac_abs],'-r',lw=3.0)
            pl.title(tistr)
            pl.xlim(XL)
            pl.ylabel('Voltage')
            pl.xlabel('Time [s]')
            pl.grid(True)
            pl.draw()
            plotfile = filename + '.pdf'
            print('Saving plot to file:'+ plotfile)
            pl.savefig(plotfile)

            self.savename.setText('Saved data to: ' + filename + '.txt/.pdf')
            #pl.show()        
        

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
                #self.pyqtgraph_leg.removeItem('measured')
                #self.pyqtgraph_leg.removeItem('measured_fac')
                #self.pyqtgraph_leg.removeItem('measured_start')
                #self.pyqtgraph_leg.removeItem('measured_stop')
                
            self.vlines = []        

    def srsmouseClicked_meas(self,evt):
        #col = 
        col = pg.mkPen(0.5,width=3)
        colsymbol = pg.mkPen(color=QtGui.QColor(100,255,100),width=4)         
        #print('Clicked: ' + str(evt.scenePos()))
        mousePoint = self.vb.mapSceneToView(evt.scenePos())
        if(self.button_meas.isChecked()):
            if(len(self.vlines) == 2): # A start and end lines is defined
                xlim = (self.vlines[0].value(),self.vlines[1].value())
                #xlim = sort(xlim)
                print('Got two lines, xlim is:' + str(xlim))
                self.vlines[1].setPos(mousePoint.x())
                self.vlines.append(None)
                # Get the data for the first stream
                if True:
                    if True:
                        xd = self.x.copy()
                        yd = self.y.copy()
                        ind = (xd > min(xlim)) & (xd < max(xlim))
                        self.meas_ind = ind # Save the index of the measuring interval
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
                            # If Voltage is larger than initial voltage
                            if(self.button_invert.text() == 'V larger'):
                                yfac = yd[0] + dyfac                                
                                indfaclog = yd > yfac
                                print('Checking for larger values',yfac)                                
                            else:
                                yfac = yd[0] + dyfac # dy is already negative
                                indfaclog = yd < yfac
                                print('Checking for smaller values',yfac)                                                                
                                
                                
                            indfac = 0
                            if(sum(indfaclog) > 0):
                                indfac = np.where(indfaclog)[0][0]
                                xfac = xd[indfac]
                                yfac = yd[indfac]
                                tfac = xd[indfac] - xd[0]
                                self.tfac = tfac
                                self.indfac = indfac
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
                            self.tmplines.append(self.meas_text)
                            self.tmplines.append(text_fac)


                
            if(len(self.vlines) == 1): 
                vLine = pg.InfiniteLine(angle=90, movable=False)            
                self.pyqtgraph_axes.addItem(vLine, ignoreBounds=True)
                self.vlines.append(vLine)
                vLine.setPos(mousePoint.x())        
        


class srspyqtgraphWidget(pymqds_plotxy.pyqtgraphWidget):
    """This is a specialised pyqtgraphWidget with function needed for the
    sensor response sledge. Namely to choose regions for respone time
    measurements
       Args: srs_windowtype: Either "plot" or "measure"

    """
    def __init__(self,*args, srs_windowtype="plot", srs_plotwidget=None, pipe_to_process=None, pipe_from_process=None, **kwargs):
        super(srspyqtgraphWidget, self).__init__(*args,**kwargs)
        self.vlines   = []
        self.tmplines = []        
        self.xmeas = None
        self.ymeas = None
        self.srs_plotwidget = srs_plotwidget
        self.pipe_to_process = pipe_to_process
        self.pipe_from_process = pipe_from_process
        
        # Add a meas button
        # This differentiation is obsolete, will remove it soon, using pg_measure for measurement
        if(srs_windowtype=="plot"):
            self.button_meas = QtWidgets.QPushButton('Choose Interval', self)
            self.button_meas.clicked.connect(self.handle_interval)
            self.button_meas.setCheckable(True)
            self.pyqtgraph_axes.scene().sigMouseClicked.connect(self.srsmouseClicked_interval)

            
        self.pyqtgraph_axes.scene().sigMouseMoved.connect(self.srsmouseMoved)                                
        self.line_sensorname = QtWidgets.QLineEdit()        
        self.button_bottom_layout.removeWidget(self.button_layout_stretch)
        self.button_bottom_layout.removeWidget(self.label_meas)
        self.button_bottom_layout.addWidget(self.button_meas)
        self.button_bottom_layout.addWidget(QtWidgets.QLabel('Sensorname'))
        self.button_bottom_layout.addWidget(self.line_sensorname)
        self.button_layout_stretch = self.button_bottom_layout.addStretch()
        self.button_bottom_layout.addWidget(self.label_meas)


    # Can be removed, is now in pg_measure
    def srsmouseClicked_meas(self,evt):
        #col = 
        col = pg.mkPen(0.5,width=3)
        colsymbol = pg.mkPen(color=QtGui.QColor(100,255,100),width=4)         
        #print('Clicked: ' + str(evt.scenePos()))
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
                            self.tmplines.append(self.meas_text)
                            self.tmplines.append(text_fac)



                
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
        #print('event',evt,evt.scenePos())
        #print('Clicked: ' + str(evt.scenePos()))
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
                            print('Opening widget for measuring')
                            self.pg_measure = pg_measure(xd,yd,self.line_sensorname.text())
                            self.pg_measure.show()


                
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
            
    # can be removed, is now in pg_measure
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
                self.pyqtgraph_leg.removeItem('measured_fac')
                self.pyqtgraph_leg.removeItem('measured_start')
                self.pyqtgraph_leg.removeItem('measured_stop')
                
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
        ## Create a seond pyqtgraphwidget for the data to be measured for response time
        #self.pyqtgraphwidget_meas = srspyqtgraphWidget(datastream = datastream_meas, logging_level = logging_level, srs_windowtype="measure",srs_plotwidget=self.pyqtgraphwidget)
        #self.layout.addWidget(self.pyqtgraphwidget_meas)        
        #
        self.pyqtgraphs.append(self.pyqtgraphwidget)
        #self.pyqtgraphs.append(self.pyqtgraphwidget_meas)        
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
