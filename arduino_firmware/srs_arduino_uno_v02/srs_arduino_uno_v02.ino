/*
  Arduino firmware for the Laufkatze 


  Peter Holtermann (peter.holtermann@io-warnemuende.de)
  
  Pinout:
  
  pinMode(A2,INPUT); // Sensor
  pinMode(A3,INPUT); // Sensor
  pinMode(A4,INPUT); // Sensor
  pinMode(A5,INPUT); // Sensor
  pinMode(2, OUTPUT); // LED
  pinMode(3, OUTPUT); // LED
  pinMode(4, OUTPUT); // LED
  pinMode(5, OUTPUT); // LED
  pinMode(8, OUTPUT); // set pin 8 to output (DIR)
  pinMode(9, OUTPUT); // set pin 9 to output (PUL/CLOCK)
  pinMode(10, OUTPUT); // set pin 10 to output (ENA)
  pinMode(11, OUTPUT); // General purpose output
  digitalWrite(10, LOW);  // Enable
  

*/
 
// Pin 13 has an LED connected on most Arduino boards.
// give it a name:
int led = 13;
uint16_t dutytime = 12500;
uint16_t freq_tmp;
uint16_t frequency_const = 0;
uint16_t frequency_prog = 0;
uint32_t counter_prog = 0;
uint32_t counter_pwm = 0;
uint32_t counter_lastena = 0;
int program_state = 0;
int program_i = 0;
int motor_mode = 3;
int INVERT_SENSORS = 0; // Are sensors triggered when low or high?
int motor_on = 0; // on


#define FREQ_TIMER1 500000

/*

  Gets a frequency in Hz and returns the dutytime for the PWM timer

  Calculates the delaytime based on the frequency 
  Timer1 is defined with a 8 prescaler, it runs thus with
  16e6/8 Hz
  f = 16e6/(8 * delaytime)
  dutytime = 16e6/(8*f) = 2000000/frequency

*/

uint16_t frequency_to_dutytime(uint16_t frequency)
{
  uint16_t delaytime;
  if(frequency > 0)
    delaytime = FREQ_TIMER1/frequency;
  else
    delaytime = 0;
  
  return delaytime;
}

uint16_t dutytime_to_frequency(uint16_t dtime)
{
  uint16_t freq;
  if(dtime > 0)
    freq = FREQ_TIMER1/dtime;
  else
    freq = 0xFFFF;
  
  return freq;
}

void setup_timer2()
{
   // Timer2 8b bit
   TCCR2A = 0;
   TCCR2B = 0;
   OCR2A = 125; // 1000Hz with 16e6/128/OCR2A or 62.5 Hz with 16e6/1024/OCR2A
   //TCCR2B |= (1<<3);// | (1<<WGM12); // CTC Mode
   TCCR2B |= (1<<WGM12); // CTC Mode
   TCCR2B |= (1 << CS12) | (1 << CS10); // 128 prescaler
   //TCCR2B |= (1 << CS12) | (1 << CS11)| (1 << CS10); // 1024 prescaler
   TIMSK2 |= (1 << OCIE2A); // enable timer overflow interrupt
}

void setup_timer1(int dutytime)
{
    TCCR1A &= ~(1<<WGM11); // Phase and frequency correct PWM
    TCCR1A |= (1<<WGM10); // Phase and frequency correct PWM
    TCCR1A |= _BV(COM1A0); // connect pin 9 to timer 1 channel A with %50 dutytime (see pg. 127 of atmega32u4 datasheet.
    TCCR1B |= (1<<WGM13);  // phase and frequency correct mode ... see Table 14-5
   
    TCCR1B &= ~(1<<CS10); // 8 prescaler
    TCCR1B |= (1<<CS11); // 8 prescaler
  //ICR1 |= 0x03FF; // set timers to count to 16383 (hex 3FFF)
  TIMSK1 |= (1 << OCIE1A); // enable timer overflow interrupt
  OCR1A = dutytime;
}

// the setup routine runs once when you press reset:
void setup() {
  Serial.begin(115200);
  //while (!Serial) {
  //  ; // wait for serial port to connect. Needed for Leonardo only
  //}
  // initialize the digital pin as an output.
  pinMode(led, OUTPUT);
  // setup timer1 to phase correct pwm
  // from https://code.google.com/p/multiwii/wiki/PWM_Generation
  pinMode(A2,INPUT); // Sensor
  pinMode(A3,INPUT); // Sensor
  pinMode(A4,INPUT); // Sensor
  pinMode(A5,INPUT); // Sensor
  pinMode(2, OUTPUT); // LED
  pinMode(3, OUTPUT); // LED
  pinMode(4, OUTPUT); // LED
  pinMode(5, OUTPUT); // LED
  pinMode(8, OUTPUT); // set pin 8 to output (DIR)
  pinMode(9, OUTPUT); // set pin 9 to output (PUL/CLOCK)
  pinMode(10, OUTPUT); // set pin 10 to output (ENA)
  pinMode(11, OUTPUT); // General purpose output
  digitalWrite(10, LOW);  // Enable
     

   
  //setup_timer1(dutytime);
  TCCR1A = 0; // stop timer one (PWM)
   
   
   // Timer 3
   
   noInterrupts();
   /* Timer 3 does not exist on the uno, workaround timer2 (which is 8bit though)
   TCCR3A = 0;
   TCCR3B = 0;
   OCR3A = 125; // 500Hz // 16e6/256/OCR3A
   TCCR3B |= (1<<WGM32); // CTC Mode
   TCCR3B |= (1 << CS12); // 256 prescaler
   TIMSK3 |= (1 << OCIE3A); // enable timer overflow interrupt
   */
     
  setup_timer2();
  
  interrupts();
   
 }
 
// the loop routine runs over and over again forever:
String inString = "";
int flag = 0;
int LED = 0;
int ena = 1;
int DIR = 0;
int tcount = 0;
int t2Hzcount = 0;
int t100Hzcount = 0;
unsigned int tspeedcount = 0; // For counting
uint8_t flagA3=0;
uint8_t flagA4=0;
uint32_t counterA3 = 0;
uint32_t counterA4 = 0;
uint8_t flagspeedmeasured=0;

uint8_t senA2 = 0;
uint8_t senA3 = 0;
uint8_t senA4 = 0;
uint8_t senA5 = 0;
uint8_t senA2_tmp;
uint8_t senA3_tmp;
uint8_t senA4_tmp;
uint8_t senA5_tmp;
uint8_t senA2_send;
uint8_t senA3_send;
uint8_t senA4_send;
uint8_t senA5_send;

uint32_t counter = 0;
uint16_t step_counter = 0;
uint16_t step_counter_send = 0;
uint16_t step_counter_prog = 0;
uint32_t step_counter_ena = 0;
char txt_buffer[50];         //the ASCII of the integer will be stored in this char array
char txt_buffer2[50];
char send_buffer[32] = {0};         //the ASCII of the integer will be stored in this char array
uint8_t FLAG_SEND_SENSORS = 0;
uint8_t FLAG_SENSORS_OUT = 1;
uint8_t FLAG_AUTO_STOP = 1; // Flag to stop the motor if no enable command has been send
uint8_t tmp;


uint16_t Pcom[6] = {0};         // Array to save the P command
uint16_t *Pcom_ptr = Pcom;


/* Commands

flag = 1: simple dutytime
flag = 2: program command
flag = 3: frequency command#

'V' : Show firmware version
'I' : Invert sensors
'N' : Not invert sensors
'W' : Output sensor data
'Q' : Do not output sensor data (quiet)
'Z' : Switch off auto stop
'Y' : Switch on auto stop (default)
'S','s' : Stops the motor (ena = 1)
'M' : Motor on
'K' : Motor off
'D???' : Dutytime 
'F???' : Frequency
'P???,???,???,???,???,???' : Program

*/

void loop() {
  
  // Did we get command data?
  // Program P3,
  while (Serial.available() > 0) {
    int inChar = Serial.read();
    //Serial.print(inChar);
    
    
    // Verbose
    if (inChar == 'V') {
        Serial.print(">>> --- --- <<<\n");
        Serial.print(">>> --- --- <<<\n");
        Serial.print(">>> --- SRS firmware v2.0 (Peter Holtermann peter.holtermann@io-warnemuende.de) ---\n");
        Serial.print(">>> --- Invert sensors: ");
        Serial.println(INVERT_SENSORS);
        Serial.print(">>> --- Auto stop: ");
        Serial.println(FLAG_AUTO_STOP);
        Serial.print(">>> --- Sensors out: ");
        Serial.println(FLAG_SENSORS_OUT);
        Serial.print(">>> --- --- <<<\n");
        Serial.print(">>> --- --- <<<\n");
        delay(100);
    }
    
    // right
    if (inChar == 'Z') {
      FLAG_AUTO_STOP = 0;
      ena = 0;
      Serial.print(">>>Auto stop off\n");
    }
    
    if (inChar == 'Y') {
      FLAG_AUTO_STOP = 1;
      Serial.print(">>>Auto stop on\n");
    }

    // right
    if (inChar == 'R') {
      DIR = 1;
      digitalWrite(8, DIR);   // Direction
      Serial.print(">>>DIR R\n");
    }

    // left
    if (inChar == 'L') {
      DIR = 0;
      digitalWrite(8, DIR);   // Direction
      Serial.print(">>>DIR L\n");
    }
    
    if (inChar == 'E') {
      ena = 0;
      counter_lastena = counter;
      Serial.print(">>>Enable E\n");
    }
    
    if (inChar == 'e') {
      ena = 0;
      counter_lastena = counter;
      Serial.print(">>>Enable e\n");
    }

    // Enable on (motor power off)
    if (inChar == 'K') {
      motor_on = 1;
      digitalWrite(10, motor_on);  
      Serial.print(">>>Motor enable on (Motor off)\n");
    }

    // Enable off (motor power on)
    if (inChar == 'M') {
      motor_on = 0;
      digitalWrite(10, motor_on);
      Serial.print(">>>Motor enable off (Motor on)\n");
    }

    if (inChar == 's') {
      ena = 1;
      TCCR1A = 0; // stop timer one (PWM) (stops motor)
      Serial.print(">>>Stop s\n");
    }

    if (inChar == 'S') {
      ena = 1;
      TCCR1A = 0; // stop timer one (PWM) (stops motor)
      Serial.print(">>>Stop S\n");
    }
    

    // Dutytime 
    if (inChar == 'D') {
      flag = 1;
      Serial.print(">>>Dutytime ...\n");
    }

    // Frequency
    if (inChar == 'F') {
      flag = 3;
      Serial.print(">>>Frequency ...\n");
    }
    
    if (inChar == 'I') {
      INVERT_SENSORS = 1;
      Serial.print(">>>Invert sensors\n");
    }
    if (inChar == 'N') {
      INVERT_SENSORS = 0;
      Serial.print(">>>No invert sensors\n");
    }
    
    if (inChar == 'W') {
      FLAG_SENSORS_OUT = 1;
      Serial.print(">>>Sensor data out\n");
    }
    
    if (inChar == 'Q') {
      FLAG_SENSORS_OUT = 0;
      Serial.print(">>>No sensor data out\n");
    }

    // Program P
    // P20,5,300,500,5,20
    // start with 20 Hz, increase every time by 5 up to 300, do 500 steps and decrease again by 5 to 20
    if (inChar == 'P') {
      flag = 2;
      Pcom_ptr = Pcom;
      Serial.print(">>>Program ...\n");
    }

    

    /*
      Dutytime command
    */
    if((flag == 1) & isDigit(inChar))
    { 
      // convert the incoming byte to a char
      // and add it to the string:
      inString += (char)inChar;
    }
    // if you get a newline, print the string,
    // then the string's value:
    if ((inChar == '\n') & (flag == 1)) {
      dutytime = inString.toInt();
      if(dutytime < 10)
        dutytime = 5000;
      //Serial.print("Dutytime: ");
      //Serial.println(dutytime);
      OCR1A = dutytime;
      motor_mode = 1;
      // clear the string for new input:
      inString = "";
      flag = 0;
    }


    /* 
       Frequency command
     */
    if((flag == 3) & isDigit(inChar))
    { 
      // convert the incoming byte to a char
      // and add it to the string:
      inString += (char)inChar;
    }
    // if you get a newline, print the string,
    // then the string's value:
    if ((inChar == '\n') & (flag == 3)) {
      frequency_const = inString.toInt();
      Serial.print(">>>Frequency: ");
      Serial.println(frequency_const);
      dutytime = frequency_to_dutytime(frequency_const);
      Serial.print(">>>Dutytime: ");
      Serial.println(dutytime);      
      OCR1A = dutytime;
      motor_mode = 3;      
      // clear the string for new input:
      inString = "";
      flag = 0;
    }    

    // P program command
    if(flag == 2)
    {
      // newline command done
      if(inChar == '\n')
    	{
	  flag = 0;	
    	}
      // convert the incoming byte to a char
      // and add it to the string:
      
      if(isDigit(inChar))
	{
	  inString += (char)inChar;
	}
      // parse the number
      if((inChar == ',') | (inChar == '\n'))
	{
	  *Pcom_ptr = inString.toInt();
	  inString = "";
	  Pcom_ptr ++;

	  motor_mode = 2;
	  program_state = 0;
	  frequency_prog = Pcom[0];
	  counter_prog = counter;
	  if(inChar == '\n')
	    {
	      sprintf(txt_buffer2,"\n>>>Program:%d,%d,%d,%d,%d,%d\n",Pcom[0],Pcom[1],Pcom[2],Pcom[3],Pcom[4],Pcom[5]);	      
	      Serial.print(txt_buffer2);
        delay(100);
        counter_lastena = counter;
        ena = 0;
        step_counter_ena = 0;
        // Reset speed counting variables
        tspeedcount = 0; // For counting
        flagA3=0;
        flagA4=0;
        flagspeedmeasured=0;
	    }
	}
    }
    // Reset all stuff
    if(inChar == '\n')
      {
	inString = "";
	flag = 0;
      }
  }

  switch(motor_mode) {
  case 1: // dutytime defined
    break; // doing nothing dutytime was defined in command parsing
  case 2: // program mode
    // P20,5,300,10,5,20
    // start with 20 Hz, increase every time by 5 up to 300 stay at 300 for 10 counter steps and decrease again by 5 to 20
    // Counter has 500 Hz
    //dutytime = 20000;
    //ena = 0;
    if((counter - counter_prog) > 20) // 25 Hz
      {
        if(ena == 0)
        {
	  counter_prog = counter;
	  if(program_state == 0) // acceleration
	    {
              Serial.print(">>>ACC\n");
	      if(frequency_prog < Pcom[2])
	        {
		  frequency_prog = frequency_prog + Pcom[1];
	        }
	      else
	        {
		  frequency_prog = Pcom[2];
		  program_state = 1;
		  program_i = 0;
                  step_counter_prog = step_counter_ena;
	        }
	    }
	  if(program_state == 1) // constant velocity
	    {
              Serial.print(">>>Const\n");
	      //if(program_i < Pcom[3])
              if((step_counter_ena - step_counter_prog) < Pcom[3])
	        {
		  program_i ++;
	        }
	      else
	        {
		  program_state = 2;
	        }
	    }
	  if(program_state == 2) // deceleration
	    {
              Serial.print(">>>DCC\n");
	      if(frequency_prog > Pcom[5])
	        {
                  // We have uint16_t so check if its positive
                  if((frequency_prog - Pcom[4]) > 0)
		    frequency_prog = frequency_prog - Pcom[4];
                  else
                    frequency_prog = Pcom[5];
	        }
	      else
	        {
		  frequency_prog = Pcom[5];
		  program_state = 3;	
	        }
	    }

          if(program_state < 3)
          {
	    dutytime = frequency_to_dutytime(frequency_prog);
            freq_tmp = dutytime_to_frequency(dutytime);
            sprintf(txt_buffer2,">>>Dty: %u,freq %u,freq prog: %u\n",dutytime,freq_tmp,frequency_prog);	
            setup_timer1(dutytime);      
	    Serial.print(txt_buffer2);
          }
          if(program_state == 3)
          {
            Serial.print(">>>Program done.\n");
            ena = 1;
            TCCR1A = 0;
            program_state = 4;
          }
          }
        else
          {
            program_state = 3;
            ena = 1;
            TCCR1A = 0;
          }	
      }
    break; 
  case 3: // frequency mode
    break; // doing nothing dutytime was defined in command parsing
  }


  digitalWrite(5, senA5_tmp); //   
  digitalWrite(4, senA4_tmp); // 
  digitalWrite(3, senA3_tmp); // 
  digitalWrite(2, senA2_tmp); //   
  // Do we have a speed measurement?
  if(flagspeedmeasured)
  {
    sprintf(txt_buffer2,">>>Speed: cnt A3, %u, cnt A4, %u, flg A3, %d, flg A4 %d\n",counterA3,counterA4,flagA3,flagA4); 
    flagspeedmeasured = 0;       
    Serial.print(txt_buffer2);
  }
  
  if(FLAG_SEND_SENSORS & FLAG_SENSORS_OUT)
  //if(0)
    {
      send_buffer[0] = '\0';
      // Send the sensor data
      ultoa(counter,txt_buffer,10); //(integer, yourBuffer, base)
      strcat(send_buffer,"XX:LS:");
      strcat(send_buffer,txt_buffer);
      tmp = strlen(send_buffer);
      send_buffer[tmp] = ',';
      tmp ++;
      send_buffer[tmp] = senA5_send;
      tmp ++;
      send_buffer[tmp] = ',';
      tmp ++;
      send_buffer[tmp] = senA4_send;
      tmp ++;
      send_buffer[tmp] = ',';
      tmp ++;
      send_buffer[tmp] = senA3_send;
      tmp ++;
      send_buffer[tmp] = ',';
      tmp ++;
      send_buffer[tmp] = senA2_send;
      tmp ++;
      send_buffer[tmp] = '\0';
      // Add the stringlen
      tmp = strlen(send_buffer);
      tmp = tmp - 3;
      itoa(tmp,txt_buffer,10); 
      send_buffer[0] = txt_buffer[0];
      send_buffer[1] = txt_buffer[1];
      strcat(send_buffer,"\n");
      Serial.print(send_buffer);
      // Send the step counter
      send_buffer[0] = '\0';
      utoa(dutytime_to_frequency(dutytime),txt_buffer,10); //Convert the PWM dutytime to frequency
      strcat(send_buffer,"XX:SC:");
      strcat(send_buffer,txt_buffer); // Send PWM Frequency
      strcat(send_buffer,",");
      utoa(step_counter_ena,txt_buffer,10); // Send Step counter
      strcat(send_buffer,txt_buffer);
      // Add the stringlen
      tmp = strlen(send_buffer);
      tmp = tmp - 3;
      itoa(tmp,txt_buffer,10);
      if(tmp > 10)
	{
	  send_buffer[0] = txt_buffer[0];
	  send_buffer[1] = txt_buffer[1];
	}
      else
	{
	  send_buffer[0] = '0';
	  send_buffer[1] = txt_buffer[0];
	}
      strcat(send_buffer,"\n");
      Serial.print(send_buffer);
      FLAG_SEND_SENSORS = 0;
    }
}

// Timer for the pwm counter
ISR(TIMER1_COMPA_vect)
{
  counter_pwm ++;
  //digitalWrite(11,counter_pwm & 0x01);
  if((counter_pwm & 0x01) == 1)
  {
    step_counter ++;
    if(ena == 0)
      step_counter_ena ++;
  }
}

// the general purpose timer
// With a frequency of 1000 Hz

ISR(TIMER2_COMPA_vect)
{
  t2Hzcount ++;
  t100Hzcount ++;
  counter ++;

  if(INVERT_SENSORS == 1)
  {
    senA5_tmp = !digitalRead(A5);   //
    senA4_tmp = !digitalRead(A4);   //
    senA3_tmp = !digitalRead(A3);   //
    senA2_tmp = !digitalRead(A2);   //
  }
  else
  {
    senA5_tmp = digitalRead(A5);   //
    senA4_tmp = digitalRead(A4);   //
    senA3_tmp = digitalRead(A3);   //
    senA2_tmp = digitalRead(A2);   //
  }
  
  senA2 = senA2 + senA2_tmp;
  senA3 = senA3 + senA3_tmp;
  senA4 = senA4 + senA4_tmp;
  senA5 = senA5 + senA5_tmp;
  // Check if we have a program running, if yes save the counter of the 
  //unsigned int tspeedcount = 0; // For counting
  //uint8_t flagA3=0;
  //uint8_t flagA4=0;
  //uint8_t flagspeedmeasured=0;
  if(flagspeedmeasured==0)
  {
    if((program_state > 0) && (program_state < 4))
    {
      if((flagA3 == 0) && (senA3_tmp > 0)) // Sledge reached A3 the first time
      {
        flagA3 = program_state;
        counterA3 = counter;
      }
      if((flagA4 == 0) && (senA4_tmp > 0)) // Sledge reached A3 the first time
      {
        flagA4 = program_state;
        counterA4 = counter;
      }
      if((flagA4 > 0) && (flagA4>0))
      {
        flagspeedmeasured=1;
      }
    }
  }
  
  if(t100Hzcount >= 10) // 100 Hz
    {
      senA5_send = senA5;
      senA4_send = senA4;
      senA3_send = senA3;
      senA2_send = senA2;
      senA5 = '0';
      senA4 = '0';
      senA3 = '0';
      senA2 = '0';
      FLAG_SEND_SENSORS=1;
      t100Hzcount = 0;
      step_counter_send = step_counter ;
      step_counter = 0 ;
      
      
      if(  ( (counter - counter_lastena) > 1000 ) && ( FLAG_AUTO_STOP == 1 ) )
      {
        ena = 1;
      }
      if(ena == 1)
      {
        TCCR1A = 0; // stop timer one (PWM) (stops motor)
	      step_counter_ena = 0 ;
      }
      else
      {
        //digitalWrite(10, LOW);  // Enable
        if(motor_mode == 3)
        {
	  if(dutytime > 0)
	    setup_timer1(dutytime);
	  else
	    TCCR1A = 0; // stops motor
        }
      }
    }
    
  
    
  if(t2Hzcount >= 500) // 2 Hz
  {
    
    LED = LED ^1;
    digitalWrite(led, LED);   // turn the LED on (HIGH is the voltage level)
    
    t2Hzcount = 0;
  }

}


