#!/usr/bin/env python3
#
# TODO: Load config, setup device button
# Set enabled buttons according to program state
# 
# Go up button in program
# Small feasability test of program
#
# Check unstable programs
#

import sys
import glob
import serial
import numpy as np
import time
import yaml
import logging
import datetime
import os

# Import qt
try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import QTimer, QElapsedTimer, Qt
    from PyQt5.QtGui import QColor
    print('Using pyqt5')
except:
    try:
        from PyQt4.QtGui import * 
        from PyQt4.QtCore import QTimer, QElapsedTimer, Qt
        print('Using pyqt4')
    except:
        raise Exception('Could not import qt, exting')



logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('srs_sledge')
logger.setLevel(logging.DEBUG)



def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system

        found here: http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    """
    
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            logger.debug("serial_ports(): Testing serial port " + str(port))
            ret = test_serial_lock_file(port,brutal=True)
            if(ret == False):
                logger.debug("serial_ports(): Opening serial port " + str(port))
                s = serial.Serial(port)
                s.close()
                result.append(port)
        #except (OSError, serial.SerialException):
        except Exception as e:
            logger.debug('serial_ports(): Exception:' + str(e))
            pass

    return result


def test_serial_lock_file(port, brutal = False):
    """
    Creates or removes a lock file for a serial port in linux
    Args:
       port: Device string
       brutal: Remove lock file if a nonexisting PID was found or no PID at all within the file
    Return:
       True if port is already in use, False otherwise
    """
    devicename = port.split('/')[-1]
    filename = '/var/lock/LCK..'+devicename
    print('serial_lock_file(): filename:' + str(filename))
    try:
        flock = open(filename,'r')
        pid_str = flock.readline()
        flock.close()
        print('test_serial_lock_file(): PID:' + pid_str)
        PID_EXIST=None
        try:
            pid = int(pid_str)
            PID_EXIST = psutil.pid_exists(pid)
            pid_ex = ' does not exist.'
            if(PID_EXIST):
                pid_ex = ' exists.'
            print('Process with PID:' + pid_str[:-1] + pid_ex)
        except Exception as e:
            print('No valid PID value' + str(e))

            
        if(PID_EXIST == True):
            return True
        elif(PID_EXIST == False):
            if(brutal == False):
                return True
            else: # Lock file with "old" PID
                print('Removing lock file, as it has a not existing PID')
                os.remove(filename)
                return False
        elif(PID_EXIST == None): # No valid PID value
            if(brutal):
                print('Removing lock file, as it no valid PID')
                os.remove(filename)
                return False
            else:
                return True
    except Exception as e:
        print('serial_lock_file():' + str(e))
        return False
    

def serial_lock_file(port,remove=False):
    """
    Creates or removes a lock file for a serial port in linux
    """
    devicename = port.split('/')[-1]
    filename = '/var/lock/LCK..'+devicename
    print('serial_lock_file(): filename:' + str(filename))
        
    if(remove == False):
        try:
            flock = open(filename,'w')
            flock.write(str(os.getpid()) + '\n')
            flock.close()
        except Exception as e:
            print('serial_lock_file():' + str(e))
    else:
        try:
            print('serial_lock_file(): removing filename:' + str(filename))
            flock = open(filename,'r')
            line = flock.readline()
            print('data',line)
            flock.close()
            os.remove(filename)
        except Exception as e:
            print('serial_lock_file():' + str(e))        

        
# Serial baud rates
baud = [300,600,1200,2400,4800,9600,19200,38400,57600,115200,576000,921600]

class srsMain(QMainWindow):
    """

    Sensor response sledge

    """
    def __init__(self):
        funcname = self.__class__.__name__ + '.___init__()'
        self.__version__ = 'v1.00'
        self.set_configuration()
        # Do the rest
        QWidget.__init__(self)

        self.direction = 'X'
        self._go_up = False
        self._doing_program = False
        self.saved_programs = {}
        # The delaytimer
        self.dtimer_int = 200 # ms        
        self.delaytimer = QTimer(self)
        self.delaytimer.setInterval(self.dtimer_int)
        self.delaytimer_connected = [] # Functions connected to the delaytimer        

        self._widgets = [] # All stand-alone widgets
        # Create the menu
        self.file_menu = QMenu('&File',self)

        #self.file_menu.addAction('&Settings',self.fileSettings,Qt.CTRL + Qt.Key_S)
        self.file_menu.addAction('&Show serial data',self._show_serial_data,Qt.CTRL + Qt.Key_D)        
        self.file_menu.addAction('&Quit',self._quit,Qt.CTRL + Qt.Key_Q)
        self.about_menu = QMenu('&About',self)
        self.about_menu.addAction('&About',self._about)        
        self.menuBar().addMenu(self.file_menu)
        self.menuBar().addMenu(self.about_menu)        
        mainwidget = QWidget(self)
        mainlayout = QGridLayout(mainwidget)

        sensorwidget = QWidget(self) # The sensor output
        sensorlayout = QGridLayout(sensorwidget)                
        serialwidget = QWidget(self) # The serial stuff
        seriallayout = QGridLayout(serialwidget)
        manualwidget = QWidget(self) # The manual moving buttons
        manuallayout = QGridLayout(manualwidget)
        progwidget = QWidget(self) # The serial stuff
        proglayout = QGridLayout(progwidget)                

        # Collect all widgets for the main layout
        mainlayout.addWidget(serialwidget,0,0)
        mainlayout.addWidget(manualwidget,1,0)
        mainlayout.addWidget(sensorwidget,0,1,2,1)
        mainlayout.addWidget(progwidget,2,0)        

        # Serial interface stuff
        self.serial_open = False
        self.combo_serial = QComboBox(self)
        self.combo_baud   = QComboBox(self)
        for b in baud:
            self.combo_baud.addItem(str(b))

        self.combo_baud.setCurrentIndex(9) # 115000
        self.serial_open_bu = QPushButton('Open')
        self.serial_open_bu.clicked.connect(self.init_serial)

        self.serial_test_bu = QPushButton('Refresh port list')
        self.serial_test_bu.clicked.connect(self._test_serial_ports)
        self._test_serial_ports()

        self.button_version = QPushButton('Firmware info')
        self.button_version.clicked.connect(self._show_firmware)

        self._stop_check = QCheckBox()
        self._stop_check.setText('Stop when up/down reached')
        self._stop_check.setChecked(True)

        # The serial port polling timer
        logger.debug(funcname + ": Starting polling timer")
        self.sertimer = QTimer(self)
        self.sertimer.setInterval(25)
        self.sertimer.timeout.connect(self.poll_serial)
        self.sertimer.start()        

        # Manual widget 
        # Up/Down buttons
        self.button_down = QPushButton('Down')
        self.button_up = QPushButton('Up')
        self.button_down.pressed.connect(self.buttonPressed)
        self.button_up.pressed.connect(self.buttonPressed)
        self.button_down.released.connect(self.buttonReleased)
        self.button_up.released.connect(self.buttonReleased)
        self.freqlcd = QLCDNumber(self)
        self.speedlcd = QLCDNumber(self)        
        self.freqlcd.display(self._man_freq)
        self.freqlcd_label = QLabel('Motor frequency [Hz]')



        self.freqsld = QSpinBox()
        self.freqsld.setRange(self._man_freq_min, self._man_freq_max)
        self.freqsld.setSingleStep(10)
        self.freqsld.setValue(self._man_freq)
        self.freqsld.valueChanged.connect(self._man_freq_changed)        
        
        self.freqsld2 = QSlider(Qt.Horizontal, self) # Freq Slider
        self.freqsld2.setRange(self._man_freq_min, self._man_freq_max)
        self.freqsld2.setTickInterval(10)
        self.freqsld2.setTickPosition(self._man_freq)
        self.freqsld2.setValue(self._man_freq)
        self.freqsld2.valueChanged.connect(self._man_freq_changed)

        # Calculate sledge speed
        self._man_freq_changed(self._man_freq)

        #
        # Program widget
        #
        # P20,5,300,100,5,20
        # Start freq, freq inc.,const. freq.,counter step const,freq dec,end freg
        # Frequency increase min. counter with 25 Hz: 1 Hz/(1/25.s)

        freq_inc_min = 1/(1/self.freq_prog_counter)
        freq_inc_max = 10000 # [Hz/s]

        self.prog_start_bu = QPushButton('\n Start\n ')
        self.prog_start_bu.clicked.connect(self._do_program)
        self.prog_status_bu = QPushButton('Status')
        self.prog_status_bu.setEnabled(False)        
        self.prog_stop_bu = QPushButton('\n Stop\n ')
        self.prog_stop_bu.clicked.connect(self._do_program)
        # Start freq
        self.prog1_spin = QSpinBox()
        self.prog1_spin.setRange(self._man_freq_min, self._man_freq_max)
        self.prog1_spin.setSingleStep(1)
        self.prog1_spin.setValue(self._man_freq_min)
        self.prog1_spin.valueChanged.connect(self._prog_changed)
        # Freq increase
        self.prog2_spin = QSpinBox()
        self.prog2_spin.setRange(freq_inc_min, freq_inc_max)
        self.prog2_spin.setSingleStep(freq_inc_min)
        self.prog2_spin.setValue(freq_inc_min)
        self.prog2_spin.valueChanged.connect(self._prog_changed)
        # Const freq 
        self.prog3_spin = QSpinBox()
        self.prog3_spin.setRange(self._man_freq_min, self._man_freq_max)
        self.prog3_spin.setSingleStep(1)
        self.prog3_spin.setValue(self._man_freq)
        self.prog3_spin.valueChanged.connect(self._prog_changed)
        # Number steps
        self.prog4_spin = QSpinBox()
        self.prog4_spin.setRange(1, self._total_steps)
        self.prog4_spin.setSingleStep(1)
        self.prog4_spin.setValue(int(self._total_steps/100))
        self.prog4_spin.valueChanged.connect(self._prog_changed)
        # Freq decrease
        self.prog5_spin = QSpinBox()
        self.prog5_spin.setRange(freq_inc_min, freq_inc_max)
        self.prog5_spin.setSingleStep(freq_inc_min)
        self.prog5_spin.setValue(freq_inc_min)
        self.prog5_spin.valueChanged.connect(self._prog_changed)
        # End freq
        self.prog6_spin = QSpinBox()
        self.prog6_spin.setRange(self._man_freq_min, self._man_freq_max)
        self.prog6_spin.setSingleStep(1)
        self.prog6_spin.setValue(self._man_freq_min)
        self.prog6_spin.valueChanged.connect(self._prog_changed)

        self._way_acc_lcd = QLCDNumber(self)
        self._way_const_lcd = QLCDNumber(self)
        self._way_dcc_lcd = QLCDNumber(self)
        self._way_total_lcd = QLCDNumber(self)
        self._speed_const_lcd = QLCDNumber(self)

        self.prog_goup_bu = QPushButton('Go up')
        self.prog_goup_bu.clicked.connect(self._do_program)        

        self._proggoup_check = QCheckBox()
        self._proggoup_check.setText('Go up first')
        self._proggoup_check.setChecked(True)

        self._prog_combo = QComboBox(self)
        self._prog_use_bu = QPushButton('Use program')
        self._prog_use_bu.clicked.connect(self._open_save_program)    
        self._prog_save_bu = QPushButton('Save this prog.')
        self._prog_save_bu.clicked.connect(self._open_save_program)

        proglayout.addWidget(QLabel('Program '),0,0)
        proglayout.addWidget(self.prog_status_bu,1,2)                
        proglayout.addWidget(self.prog_goup_bu,2,2)        
        proglayout.addWidget(self.prog_start_bu,3,2,2,1)
        proglayout.addWidget(self.prog_stop_bu,5,2,2,1)
        proglayout.addWidget(self._proggoup_check,7,2)
        proglayout.addWidget(QLabel('Programs'),8,2)        
        proglayout.addWidget(self._prog_combo,9,2)
        proglayout.addWidget(self._prog_use_bu,10,2)     
        proglayout.addWidget(self._prog_save_bu,11,2)
        
        proglayout.addWidget(QLabel('Start frequency [Hz]'),1,1)
        proglayout.addWidget(self.prog1_spin,1,0)
        proglayout.addWidget(QLabel('Frequency increase [Hz/s]'),2,1)
        proglayout.addWidget(self.prog2_spin,2,0)
        proglayout.addWidget(QLabel('Constant  frequency [Hz]'),3,1)
        proglayout.addWidget(self.prog3_spin,3,0)
        proglayout.addWidget(QLabel('Number steps [steps]'),4,1)        
        proglayout.addWidget(self.prog4_spin,4,0)
        proglayout.addWidget(QLabel('Frequency decrease [Hz/s]'),5,1)        
        proglayout.addWidget(self.prog5_spin,5,0)
        proglayout.addWidget(QLabel('End frequency [Hz/s]'),6,1)
        proglayout.addWidget(self.prog6_spin,6,0)

        proglayout.addWidget(QLabel('Way acc [m]'),7,1)
        proglayout.addWidget(self._way_acc_lcd,7,0)
        proglayout.addWidget(QLabel('Way const [m]'),8,1)
        proglayout.addWidget(self._way_const_lcd,8,0)
        proglayout.addWidget(QLabel('Way dcc [m]'),9,1)
        proglayout.addWidget(self._way_dcc_lcd,9,0)
        proglayout.addWidget(QLabel('Way total [m]'),10,1)
        proglayout.addWidget(self._way_total_lcd,10,0)
        proglayout.addWidget(QLabel('Speed const [m/s]'),11,1)
        proglayout.addWidget(self._speed_const_lcd,11,0)        


        # Sensor widget
        self.stopwatch = QElapsedTimer()
        self.stopwatch.start()
        self.time_stopwatch = 0.0
        self.time_stopwatch_start = None
        self.time_stopwatch_stop = None
        self.avgspeed = 0.0
        self.A_color  = QColor(100,100,100)
        self.Astatus = []
        #self.Aspeed = []
        for i in range(4):
            stri = 'A' + str(5-i)
            if(self.ind_sensor_up == i):
                stri += ' (up)'
            if(self.ind_sensor_down == i):
                stri += ' (down)'

            if(self.ind_sensor_speed[0] == i):
                stri += ' (speed start)'

            if(self.ind_sensor_speed[1] == i):
                stri += ' (speed stop)'                
                
            self.Astatus.append(QLabel(stri))
            self.Astatus[-1].setStyleSheet("QFrame { background-color: %s }" % self.A_color.name())
            self.Astatus[-1].setMinimumWidth(150)
            #if((stri == 'A3') or (stri == 'A4')):
            #    self.Aspeed.append(QLCDNumber(sensorwidget)) 
            #else:
            #    self.Aspeed.append(None)

        self.tstopwatch_lcd = QLCDNumber(sensorwidget)
        self.avgspeed_lcd = QLCDNumber(sensorwidget)
        self.button_meas_speed = QPushButton('Meas. speed')
        self.button_meas_speed.clicked.connect(self.do_speed_meas)

        self._text_speed = QPlainTextEdit()
        self._text_speed.setReadOnly(True) 
        self._text_speed.clear()
        self._text_speed.insertPlainText('Speed records')        

        # Steps done and PWM freq
        self.PWMfreqlcd = QLCDNumber(self)
        self.stepsdonelcd = QLCDNumber(self)
        self.oldstepsdonelcd = QLCDNumber(self)                
        #self.button_meas_speed.clicked.connect(self.enable_stopwatch)

        for i in range(4):
            sensorlayout.addWidget(self.Astatus[i],1,i,2,1)
            
            #if(self.Aspeed[i]):
            #    sensorlayout.addWidget(self.Aspeed[i],1,i)


        sensorlayout.addWidget(QLabel('PWM frequency'),3,0)
        sensorlayout.addWidget(self.PWMfreqlcd,4,0)
        sensorlayout.addWidget(QLabel('Steps done'),3,1)        
        sensorlayout.addWidget(self.stepsdonelcd,4,1)
        sensorlayout.addWidget(QLabel('Last steps done'),3,2)
        sensorlayout.addWidget(self.oldstepsdonelcd,4,2)
        sensorlayout.addWidget(self.button_meas_speed,6,0)            
        sensorlayout.addWidget(self.button_meas_speed,6,0)
        sensorlayout.addWidget(QLabel('Seconds'),5,1)                
        sensorlayout.addWidget(self.tstopwatch_lcd,6,1)
        sensorlayout.addWidget(QLabel('Speed'),5,2)        
        sensorlayout.addWidget(self.avgspeed_lcd,6,2)

        mainlayout.addWidget(self._text_speed,2,1)

        # Set the layout
        seriallayout.addWidget(self.serial_test_bu,0,0)
        seriallayout.addWidget(self.combo_serial,0,1)
        seriallayout.addWidget(self.combo_baud,0,2)
        seriallayout.addWidget(self.serial_open_bu,0,3)
        seriallayout.addWidget(self.button_version,1,0)
        seriallayout.addWidget(self._stop_check,1,1)        
        
        manuallayout.addWidget(self.button_down,1,0)
        manuallayout.addWidget(self.button_up,1,1)
        manuallayout.addWidget(QLabel('Motor frequency [Hz]'),0,3)
        manuallayout.addWidget(self.freqlcd,1,3)
        manuallayout.addWidget(QLabel('Sledge speed [m/s]'),0,4)
        manuallayout.addWidget(self.speedlcd,1,4)
        manuallayout.addWidget(self.freqsld,2,0)        
        manuallayout.addWidget(self.freqsld2,2,1,1,4)

        

        # Focus 
        mainwidget.setFocus()
        self.setCentralWidget(mainwidget)
        #self.resize(800,500)

        # update program
        self._init_open_save_program()        
        self._prog_changed(0)
        
    def set_configuration(self):
        """
        Reads a configuration file 
        """
        funcname = self.__class__.__name__ + '.set_configuration()'        
        self.sensor_rawdata = ''
        self.sensor_data   = [[],[],[],[],[]]
        self.sensor_up     = None # The sensor at the start
        #self.ind_sensor_up = 3
        self.sensor_down   = None # The sensor at the stop
        # The frequency of the prog_counter for the motor program
        self.freq_prog_counter = 25
        # For the speed measurement (self.meas_speed)
        self.speed_meas_state = 0
        
        with open("srs_config.yaml", 'r') as stream:
            try:
                config = yaml.load(stream)
                self._total_steps = config['total_steps']
                self._total_length = config['total_length']
                self._speed_length = config['speed_length']
                self._man_freq = config['freq_init']
                self._man_freq_min = config['freq_set_min']
                self._man_freq_max = config['freq_set_max']
                self.ind_sensor_up = config['ind_sensor_up']
                self.ind_sensor_down = config['ind_sensor_down']
                self.ind_sensor_speed = config['ind_sensor_speed']
                self._invert_sensors = config['invert_sensors']
                self._motor_up_direction = config['motor_up_direction']
                self.programs_filename = config['programs_filename']
                self.chooseDIR(self._motor_up_direction)
            except yaml.YAMLError as exc:
                logger.warning(funcname + ':' + str(exc))


        self.m_per_step = 1.0 * self._total_length/self._total_steps


        
    def _quit(self):
        try:
            self._about_label.close()
        except:
            pass

        try:
            self._serial_textwidget.close()
        except:
            pass

        try:
            serial_lock_file(self.ser.port,remove=True)
        except:
            pass            
        
        self.close()

        
    def _about(self):
        about_str = '\n Sensor Response Sledge (SRS) \n'        
        about_str += '\n This is srs_sledge: ' + self.__version__
        about_str += '\n Copyright Peter Holtermann \n'
        about_str += '\n peter.holtermann@io-warnemuende.de \n'        
        self._about_label = QLabel(about_str)
        self._about_label.show()


    def _prog_changed(self,freq):
        #
        sender = self.sender()
        # Start freq
        self.prog1_spin.setRange(self._man_freq_min, self.prog3_spin.value())
        # End freq
        self.prog6_spin.setRange(self._man_freq_min, self.prog3_spin.value())
        self.calc_program()

        self._way_acc_lcd.display(self._prog_acc_way)
        self._way_const_lcd.display(self._prog_const_way)
        self._way_dcc_lcd.display(self._prog_dcc_way)
        self._way_total_lcd.display(self._prog_dcc_way)
        self._speed_const_lcd.display(self._prog_speed_const)
    
    def calc_program(self):
        freqs = []
        # Total steps
        total_steps = [0]
        total_dist = [0]
        # Get frequency
        freq = self.prog1_spin.value()
        freqs.append(freq)
        # ACC
        while(freq < self.prog3_spin.value()):
            freq += self.prog2_spin.value()/self.freq_prog_counter
            freqs.append(freq)            
            steps = freq * 1.0/self.freq_prog_counter
            total_steps.append(steps + total_steps[-1])
            total_dist.append(total_steps[-1] * self.m_per_step)

        self._prog_acc_way = total_dist[-1]
        # Const
        freq = self.prog3_spin.value()
        # Steps
        steps_const = self.prog4_spin.value()
        total_steps.append(total_steps[-1] + steps_const)
        total_dist.append(total_steps[-1] * self.m_per_step)
        self._prog_const_way = total_dist[-1] - self._prog_acc_way

        # DCC
        while(freq > self.prog6_spin.value()):
            freq -= self.prog5_spin.value()/self.freq_prog_counter
            freqs.append(freq)
            steps = freq * 1.0/self.freq_prog_counter
            total_steps.append(steps + total_steps[-1])
            total_dist.append(total_steps[-1] * self.m_per_step)            

        self._prog_dcc_way = total_dist[-1] - self._prog_const_way - self._prog_acc_way

        #print('Freqs:',freqs)
        #print('Total steps:',total_steps)
        #print('Total dist:',total_dist)
        self._prog_total_way = total_dist[-1]
        self._prog_speed_const = self._freq_to_speed(freq)
        # Create a string of the probram
        self.str_program = ' Freq. start:' + str(self.prog1_spin.value())
        self.str_program += ' Freq. inc.:' + str(self.prog2_spin.value())
        self.str_program += ' Freq. cons.:' + str(self.prog3_spin.value())
        self.str_program += ' Steps: ' + str(self.prog4_spin.value())
        self.str_program += ' Freq. dec:' + str(self.prog5_spin.value())
        self.str_program += ' Freq. stop:' + str(self.prog6_spin.value())
        self.program_list = [self.prog1_spin.value(),self.prog2_spin.value(),self.prog3_spin.value(),self.prog4_spin.value(),self.prog5_spin.value(),self.prog6_spin.value()]


    def _do_program(self):
        """
        Sends the program to the arduino

        """
        funcname = self.__class__.__name__ + '._start_program()'

        sender = self.sender()
        freq1 = self.prog1_spin.value()
        dfreq1 = int(self.prog2_spin.value()/self.freq_prog_counter)
        freq_const = self.prog3_spin.value()
        steps_const = self.prog4_spin.value()
        dfreq2 = int(self.prog5_spin.value()/self.freq_prog_counter)
        freq2 = self.prog6_spin.value()

        self.mode = 'P'


        if(self.sender() == self.prog_goup_bu):
            logger.debug(funcname + ': Go up')
            self.send_freq(self._man_freq)            
            self.send_up()            
            self._go_up = True
            self.delaytimer.timeout.connect(self.send_enable)
            self.delaytimer_connected.append(self.send_enable)
            self.delaytimer.start()            
        
        if(self.sender() == self.prog_start_bu):
            self._doing_program = True
            self.speed_meas_state = 1            
            self.send_down()
            cmd = 'P'
            cmd += str(freq1) + ','
            cmd += str(dfreq1) + ','
            cmd += str(freq_const) + ','
            cmd += str(steps_const) + ','
            cmd += str(dfreq2) + ','
            cmd += str(freq2) + '\n'
            logger.debug(funcname + ': Start; cmd:' + cmd)
            if(self.serial_open):
                self.ser.write(cmd.encode('utf-8'))
                
            #self.sender().setText('Stop')
            self.delaytimer.timeout.connect(self.send_enable)
            self.delaytimer_connected.append(self.send_enable)
            self.delaytimer.start()            
        elif(self.sender() == self.prog_stop_bu):
            self._doing_program = False
            self.prog_status_bu.setText('Done')            
            self.send_stop()
            self.delaytimer.stop()
            try:
                self.delaytimer.timeout.disconnect()
            except Exception as e:
                logger.debug(funcname + ': Disconnect: ' + str(e))

            self.delaytimer_connected = []                
            logger.debug(funcname + ': Stop')            
            #self.sender().setText('Start')


    def _init_open_save_program(self):
        funcname = self.__class__.__name__ + '._init_open_save_program()'
        if True:
            logger.debug(funcname + ': Opening file')
            QF = QFileDialog()
            #fname = QF.getOpenFileName(self, 'Open yaml program file', './',"Yaml files (*.yaml)")
            #fname = fname[0]
            fname = self.programs_filename
            logger.debug(funcname + ': Opening file:' + fname)
            self.program_filename = fname
            if(os.path.exists(fname)):
                self.program_file = open(fname, 'r+')
                try:
                    self.saved_programs = yaml.load(self.program_file)
                    if(self.saved_programs == None):
                        self.saved_programs = {}
                    else:
                        try:
                            self.saved_programs = self.saved_programs['Programs']
                        except:
                            self.saved_programs = {}
                        
                    print(self.saved_programs)
                    for prog in self.saved_programs:
                        print('prog:',prog)
                        self._prog_combo.addItem(prog)
                       
                except Exception as exc:
                    logger.warning(funcname + ': Could not load programs:' + str(exc))

            else:
                logger.warning(funcname + ': File does not exist, creating a new one:' + fname)
                self.program_file = open(fname, 'w')

    def _open_save_program(self):
        funcname = self.__class__.__name__ + '._open_save_program()'
        if(self.sender() == self._prog_save_bu):
            logger.debug(funcname + ': Saving program')
            text, ok = QInputDialog.getText(self, 'Program Name', 
            'Enter the name of the program:')
            if ok:
                print(text)
                prog_dict = self.saved_programs
                prog_dict[text] = self.program_list
                self.saved_programs = prog_dict
                self._prog_combo.addItem(text)
                prog_save = {'Programs':prog_dict}
                print(prog_save)
                print(yaml.dump(prog_save))
                try:
                    self.program_file.seek(0)
                    self.program_file.write(yaml.dump(prog_save))
                    self.program_file.flush()
                    
                except Exception as e:
                    logger.debug(funcname + ': Writing problems:' + str(e))
                    
        if(self.sender() == self._prog_use_bu):
            logger.debug(funcname + ': Using program')
            pr = str(self._prog_combo.currentText())
            prog_data = self.saved_programs[pr]
            self.prog1_spin.setValue(prog_data[0])
            self.prog2_spin.setValue(prog_data[1])
            self.prog3_spin.setValue(prog_data[2])            
            self.prog4_spin.setValue(prog_data[3])
            self.prog5_spin.setValue(prog_data[4])
            self.prog6_spin.setValue(prog_data[5])
            print(prog_data)

    def _man_freq_changed(self,freq):
        """
        Do update stuff when the frequency has been changed
        """
        funcname = self.__class__.__name__ + '._man_freq_changed()'        
        self._man_freq = freq
        self._freq_to_speed_man()
        self.freqsld.setValue(freq)
        self.freqsld2.setValue(freq)
        self.freqlcd.display(self._man_freq)
        self.speedlcd.display(self._man_speed)
        logger.debug(funcname + ':' + str(self._man_freq))
    
    
    def _freq_to_speed_man(self):
        """
        Calculates approximate speed based on the frequency
        """

        self._man_speed = 1.0 * self._total_length / self._total_steps * self._man_freq

    def _freq_to_speed(self,freq):
        """
        Calculates approximate speed based on the frequency
        """

        speed = 1.0 * self._total_length / self._total_steps * freq
        return speed

    def _test_serial_ports(self):
        """
        
        Look for serial ports

        """
        funcname = self.__class__.__name__ + '._test_serial_ports()'        
        ports = serial_ports()
        # This could be used to pretest devices
        #ports_good = self.test_device_at_serial_ports(ports)
        ports_good = ports
        logger.debug(funcname + ': ports:' + str(ports_good))
        self.combo_serial.clear()
        for port in ports_good:
            self.combo_serial.addItem(str(port))


    def init_serial(self):
        """
        Opens a port and tests if expected data comes 
        """
        funcname = self.__class__.__name__ + '._test_serial_ports()'
        port = str(self.combo_serial.currentText())
        b = int(self.combo_baud.currentText())
        if(self.serial_open_bu.text() == 'Open'):
            try:
                logger.debug(funcname + ": Opening Serial port" + port)
                self.ser = serial.Serial(port,b)
                logger.debug(funcname + ": Creating a flock file for Serial port" + port)                
                serial_lock_file(port)
                self.combo_serial.setEnabled(False)
                self.combo_baud.setEnabled(False)                
                time.sleep(1.0)
                self.get_version()
                # Send invert command
                if(self._invert_sensors == 1):
                    cmd = 'I\n'
                else:
                    cmd = 'N\n'                    

                logger.debug(funcname + ": Send invert sensors:" + cmd)
                self.ser.write(cmd.encode('utf-8'))
                self.firmware_version = self.get_version()
                # Show sensor data
                self.ser.write('W'.encode('utf-8'))
                self.serial_open = True
                
            except Exception as e:
                logger.warning(funcname + ':' + str(e))
                print("Could not open", port)
                self.ser = None
                self.serial_open = False                
                return False


            self.serial_open_bu.setText('Close')
            return True
        
        elif(self.serial_open_bu.text() == 'Close'):
            self.sertimer.stop()
            serial_lock_file(self.ser.port,remove=True)            
            self.ser.close()
            self.combo_serial.setEnabled(True)
            self.combo_baud.setEnabled(True)
            self.serial_open = False            
            # GUI
            self.A_color.setRgb(100,100,100)
            for i in range(4):
                self.Astatus[i].setStyleSheet("QFrame { background-color: %s }" % self.A_color.name())
            logger.debug(funcname + ": Closed serial port" + port)
            self.serial_open_bu.setText('Open')
        #self.delaytimesld.disconnect()
        #self.button_goup.disconnect()
        #self.button_stop.disconnect()
        #self.delaytimesld.disconnect()
        #self.button_down.disconnect()
        #self.button_up.disconnect()   
        #self.button_down.disconnect()   
        #self.button_up.disconnect()
        #self.button_program.disconnect()
        #self.button_down.setEnabled(False)
        #self.button_up.setEnabled(False)
        #self.button_stop.setEnabled(False)
        #self.button_goup.setEnabled(False)
        #self.ser.close()

    def get_version(self):
        # Send a V, wait and send a V again
        # The parse the answer to test if its a srs arduino
        num_bytes = self.ser.inWaiting()
        data = self.ser.read(num_bytes)
        print('data00:',data)                        
        self.ser.write('Q\n'.encode('utf-8')) # Quiet
        self.ser.write('V\n'.encode('utf-8'))
        num_bytes = self.ser.inWaiting()
        data = self.ser.read(num_bytes)
        print('data0:',data)                
        time.sleep(.2)
        self.ser.write('V\n'.encode('utf-8'))                
        num_bytes = self.ser.inWaiting()
        data = self.ser.read(num_bytes)
        print('data',data)
        data = data.decode(encoding='utf-8')
        dline = data.split('\n')
        version_str = ''
        for dl in dline:
            ind = dl.find('>>> ---')
            print(ind)
            if(ind >= 0):
                version_str += dl + '\n'
                print('Line:' + dl)
                
        print('Version:' + version_str)
        self.ser.write('W\n'.encode('utf-8')) # Show data again
        return version_str
    

    def _show_firmware(self):
        if(self.serial_open):
            self.firmware_version = self.get_version()        
            self._text_firmware = QPlainTextEdit()
            self._text_firmware.setReadOnly(True) 
            self._text_firmware.clear()
            self._text_firmware.insertPlainText(self.firmware_version)
            self._text_firmware.setWindowTitle('SRS Firmware version')
            self._text_firmware.show()

    def poll_serial(self):
        funcname = self.__class__.__name__ + '.poll_serial()'
        if(self.serial_open):
            #print 'HALLO',self.ser.available()
            num_bytes = self.ser.inWaiting()
            data = self.ser.read(num_bytes)        
            #data = self.ser.read(4096)
            #print('a',data)
            #print(self.ser)
            if(len(data) > 0):
                if(True):
                    try:
                        data = data.decode(encoding='utf-8')
                        self.sensor_rawdata += data
                        # Show the data
                        try:
                            self._serial_textwidget.insertPlainText(data)
                        except:
                            pass
                    except Exception as e:
                        #logger.warning(funcname + ':' + str(e))
                        print(data)
                        data = b''

                    self.parse_sensor_data()


    def _show_serial_data(self):
        funcname = self.__class__.__name__ + '._show_serial_data()'
        self._serial_textwidget = QPlainTextEdit()
        self._serial_textwidget.setReadOnly(True) 
        self._serial_textwidget.clear()
        self._serial_textwidget.insertPlainText('Speed records')
        self._serial_textwidget.setMaximumBlockCount(10000)
        self._serial_textwidget.show()
            


    def parse_sensor_data(self):
        """
        Packets:
        SC: Step counter #06:SC:4,0 
                          06:SC:pwm freq,steps done
        LS: Sensor package
        """
        
        funcname = self.__class__.__name__ + '.parse_sensor_data()'
        lines = self.sensor_rawdata.split('\n')
        if(len(lines[-1])>0):
            self.sensor_rawdata = lines[-1]
            lines = lines[:-1]
        else:
            self.sensor_rawdata = ''
        
        for datastr in lines:
            #logger.debug(funcname + ': Datastr: ' + datastr)
            #if(len(datastr[3:]) == strlen):
            if(len(datastr)>0):
                ind0 = datastr.find("SC:")
                ind1 = datastr.find("LS:")
                ind2 = datastr.find(">>>Program done.")
                ind3 = datastr.find(">>>ACC")
                ind4 = datastr.find(">>>Const")
                ind5 = datastr.find(">>>DCC")
                # A step counter and PWM freq packet
                if(ind0 > 0):
                    #logger.debug(funcname + ': Counter/PWM Freq string: ' + datastr)
                    #06:SC:4,0
                    ind0 = ind0 + 3
                    d = datastr[ind0:].rsplit(',')
                    if(len(d) > 1):
                        try:
                            self.pwm_freq = int(d[0])
                            self.steps_done = int(d[1])
                            
                            # Show the new data
                            self.PWMfreqlcd.display(self.pwm_freq)
                            self.stepsdonelcd.display(self.steps_done)
                            if(self.steps_done > 0 ):
                                self.oldstepsdonelcd.display(self.steps_done)
                        except Exception as e:
                            logger.debug(funcname + ': SC parse:' + str(e) + 'str:' + datastr)   
                            break
                # A sensor packet
                # time,A5,A4,A3,A2
                if(ind1 > 0):
                    ind1 = ind1 + 3
                    d = datastr[ind1:].rsplit(',')
                    if(len(d) > 4):
                        try:
                            t = int(d[0])/500. # 500 Hz
                            self.sensor_data[0].append(t)
                            self.actual_sensor_data = [] # [t,a5,a4,a3,a2]
                            self.actual_sensor_data.append(t)
                            for i in range(4):
                                sen = d[i+1] 
                                if(sen == ':'):
                                    sen = 10
                                else:
                                    #print 'sen',sen
                                    sen = int(sen)

                                self.sensor_data[i+1].append(sen)
                                self.actual_sensor_data.append(sen)

                            # Fill the up/down sensors
                            self.sensor_up = self.actual_sensor_data[self.ind_sensor_up+1]
                            self.sensor_down = self.actual_sensor_data[self.ind_sensor_down+1]
                            # Fill the speed sensors
                            self.sensor_speed_start = self.actual_sensor_data[self.ind_sensor_speed[0]+1]
                            self.sensor_speed_stop = self.actual_sensor_data[self.ind_sensor_speed[1]+1]
                            self.meas_speed() # Call the speed measure function
                            # Interprete and plot the data
                            #self.interprete_sensor_data()
                            # Remove the first part of the list its growing to big
                            if(len(self.sensor_data[0]) > 1000):
                                for i in range(len(self.sensor_data)):
                                    for j in range(100):                        
                                        self.sensor_data[i].pop(0)

                            # Check for sensor status
                            # Check if we have to care about top/bottom
                            if((self._stop_check.isChecked()) or (self._go_up)):
                                if((self.sensor_up > 0) and (self.direction_up == self.direction)):
                                    logger.debug(funcname + ':Reached top!')
                                    self.buttonReleased()
                                    self._go_up = False
                                if((self.sensor_down > 0) and (self.direction_down == self.direction)):
                                    logger.debug(funcname + ':Reached bottom!')
                                    self.buttonReleased()                                    
                            if(self._proggoup_check.isChecked()):
                                if((self.sensor_up > 0)):
                                    self.prog_start_bu.setEnabled(True)
                                else:
                                    self.prog_start_bu.setEnabled(False)
                            else:
                                self.prog_start_bu.setEnabled(True)
                                    
                            # Update the sensor gui
                            for i in range(4):
                                # Check if the sensor sensed something
                                if(self.actual_sensor_data[i+1]>0):
                                    self.A_color.setRgb(0,255,0)
                                else:
                                    self.A_color.setRgb(255,0,0)

                                self.Astatus[i].setStyleSheet("QFrame { background-color: %s }" % self.A_color.name())

                        except Exception as e:
                            logger.warning(funcname + ': LS parsing:' + str(e) + '\nstr:' + datastr)
                            break                                    
                # Program done message
                if(self._doing_program):
                    self.button_meas_speed.setEnabled(False)

                    
                if(ind2 == 0):
                    self.prog_status_bu.setText('Done')
                    self.button_meas_speed.setEnabled(True)
                    self.speed_meas_state = 0
                    self._doing_program = False
                    self.delaytimer.stop()
                    try:
                        self.delaytimer.timeout.disconnect()
                    except Exception as e:
                        logger.debug(funcname + ': Disconnect: ' + str(e))                                                        
                if(ind3 == 0):
                    self.prog_status_bu.setText('ACC')
                if(ind4 == 0):
                    self.prog_status_bu.setText('Const')
                if(ind5 == 0):
                    self.prog_status_bu.setText('DCC')
                    
            else:
                pass
                #logger.debug(funcname + ': string too short:' +datastr)   



    def meas_speed(self):
        """
        Function to measure the speed, depending on the state of the speed measure
        self.speed_meas_state
        """
        funcname = self.__class__.__name__ + '.meas_speed()'
        #self.tstopwatch_lcd = QLCDNumber(sensorwidget)
        #self.avgspeed_lcd = QLCDNumber(sensorwidget)
        dt = -9999
        self.speed = -9999.9

        if(self.speed_meas_state > 0):
            # Start speed measure if sensor start was triggered
            if(self.speed_meas_state == 1):
                if(self.sensor_speed_start > 0): # Start sensor triggered
                    self.speed_meas_state = 2
                    self._t_start = self.actual_sensor_data[0]
                    self.steps_done_start = self.steps_done
                    self.stopwatch.restart()    
                    self.time_stopwatch_start = self.stopwatch.elapsed()
                    self.speed_time_local_start = datetime.datetime.now()

            if(self.speed_meas_state == 2):
                self._t_stop = self.actual_sensor_data[0]
                dt = (self._t_stop - self._t_start) 
                self.speed = self._speed_length / dt
                dt_stopwatch = (self.stopwatch.elapsed() - self.time_stopwatch_start)/1000.0
                #print(self._t_stop,self._t_start,dt,dt_stopwatch)                
                if(self.sensor_speed_stop > 0): # Stop sensor triggered
                    logger.debug(funcname + ': Stop')
                    self.speed_meas_state = 3
                    self.steps_done_stop = self.steps_done
                    self.speed_time_local_stop = datetime.datetime.now()
                    # Update speed info widget
                    self.update_speed_records()
                    self.button_meas_speed.setText('Meas. speed')

                self.tstopwatch_lcd.display(dt)                    
                self.avgspeed_lcd.display(self.speed)

                    

    def do_speed_meas(self):
        if(self.sender().text() == 'Meas. speed'):
            self.sender().setText('Reset meas. speed')
            self.speed_meas_state = 1
        else:
            self.sender().setText('Meas. speed')
            self.speed_meas_state = 0


    def update_speed_records(self):
        showstr = '\n'
        if(self.mode == 'P'):
            showstr += self.str_program
        else:
            showstr += 'Manual '

        start_time = datetime.datetime.strftime(self.speed_time_local_start,'%Y.%m.%d %H:%M:%S')
        stop_time  = datetime.datetime.strftime(self.speed_time_local_stop,'%Y.%m.%d %H:%M:%S')

        showstr += ' ' + start_time + ' -- ' +  stop_time
        showstr += ' Steps: '+ str(self.steps_done)
        showstr += ' Speed: '+ str(self.speed)
        showstr += '\n'
        self._text_speed.insertPlainText(showstr)

        
    def move_up(self):
        #print('Sensor up:' + str(self.sensor_up))
        if(self.sensor_up>0):
            self.statusBar().showMessage('Sensor up said that we reached end')
            print('Sensor up said that we reached end')
            self.full_stop()
        else:
            self.status = LUP
            #self.statusBar().showMessage('Still going up')
            #print('Still going up')
            self.send_up()
            self.send_enable()

    def chooseDIR(self,text):
        t = str(text)
        if(t == 'clockwise'):
            #self.infotext.insertPlainText("Direction 'down' if motor moves clockwise\n")
            #self.sensor_triggered = sensor_low
            self.send_down = self.send_L
            self.send_up = self.send_R
            self.direction_up = 'R'
            self.direction_down = 'L'            

        if(t == 'anticlockwise'):
            #self.infotext.insertPlainText("Direction 'down' if motor moves anticlockwise\n")
            self.send_down = self.send_R
            self.send_up = self.send_L
            self.direction_up = 'L'
            self.direction_down = 'R'                        
            #self.sensor_triggered = sensor_high

    # Arduino commands
    # Send commands to the Arduino
    def send_freq(self,freq):
        funcname = self.__class__.__name__ + '.send_freq()'
        logger.debug(funcname)        
        if(self.serial_open):
            self.freq = freq
            logger.debug(funcname + ':Freq: ' + str(self.freq))            
            com_str = 'F' + str(self.freq) + '\n'
            self.ser.write(com_str.encode('utf-8'))

            
    def send_enable(self):
        """

        Important function to send an enable to the arduino, it will stop
        otherwise

        """
        funcname = self.__class__.__name__ + '.send_enable()'
        logger.debug(funcname)
        
        if(self.serial_open):
            self.ser.write('e'.encode('utf-8'))                    


    def send_stop(self):
        funcname = self.__class__.__name__ + '.send_stop()'
        logger.debug(funcname)        
        if(self.serial_open):
            self.ser.write('s'.encode('utf-8'))
            #self.infotext.insertPlainText('send_stop(): s')
            #self.infotext.insertPlainText('\n')
            #self.infotext.verticalScrollBar().setValue(self.infotext.verticalScrollBar().maximum())

    def send_direction(self,direction):
        funcname = self.__class__.__name__ + '.send_direction()'        
        if(self.serial_open):
            com_str = direction + '\n'
            self.ser.write(com_str.encode('utf-8'))
            self.direction = direction
            logger.debug(funcname + ': DIR:' + direction)


    def send_L(self):
        self.send_direction('L')
        
    def send_R(self):
        self.send_direction('R')


    def buttonPressed(self):
        funcname = self.__class__.__name__ + '.buttonPressed()'
        logger.debug(funcname)                        
        sender = self.sender()
        self.mode = 'M'        
        if(sender.text() == 'Stop'):
            #self.statusBar().showMessage(sender.text() + ' was pressed')
            return

        self.send_freq(self._man_freq)
        if(sender.text() == 'Up'):
            self.send_up()
            self.delaytimer.timeout.connect(self.send_enable)
            self.delaytimer_connected.append(self.send_enable)
            self.delaytimer.start()
        if(sender.text() == 'Down'):
            self.send_down()            
            self.delaytimer.timeout.connect(self.send_enable)
            self.delaytimer_connected.append(self.send_enable)
            self.delaytimer.start()

        #self.statusBar().showMessage(sender.text() + ' was pressed')            


    def buttonReleased(self):
        funcname = self.__class__.__name__ + '.buttonReleased()'
        logger.debug(funcname)
        sender = self.sender()
        self.send_stop()
        if(self.delaytimer.isActive()):
            self.delaytimer.stop()
            try:
                self.delaytimer.timeout.disconnect()
            except Exception as e:
                logger.debug(funcname + ': Disconnect: ' + str(e))                                    

            self.delaytimer_connected = []
        #self.statusBar().showMessage(sender.text() + ' was released')        
        


def main():
    # Open the serial port
    if(len(sys.argv)>1):
        port = sys.argv[1]
    else:
        port = "/dev/ttyACM0"

    app = QApplication(sys.argv)
    myapp = srsMain()
    myapp.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
