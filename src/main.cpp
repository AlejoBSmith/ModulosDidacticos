#include <Arduino.h>
#include <movingAvg.h>
#include <StringSplitter.h>

// Pines control motor
const int pwmPin = 9;   // Enable pin (PWM input)
const int in1Pin = 7;   // IN1 pin
const int in2Pin = 8;   // IN2 pin

// Pines encoder
const int encoderA = 2; // Encoder channel A
const int encoderB = 3; // Encoder channel B

//Controlador
bool inicio = 0;
int sumaPID, a = 0;
int accionProp, accionDeriv, accionInteg, error, tiempo, tiempoinicio, tiempoanterior, referencia, encoderTicksActual, encoderTicksAnterior, deltaencoderTicks, sumerror, time_delay = 0;
float Kp, Ki, Kd, tiempociclo, RPM, RPM1erFilt, RPMPromedio, RPMPromedioanterior = 0;
String DatoSerial;
movingAvg RPM1(8);
movingAvg RPMAvg(8);
movingAvg Derivada(8);

volatile float encoderTicks = 0;
int lastEncoded = 0;
String StringEntrada;

void updateEncoder() {
  // Se leen los encoder A y B para luego combinarlos en un solo número
  // Para más info, ver https://en.wikipedia.org/wiki/Incremental_encoder sección "State transitions"
  int MSB = digitalRead(encoderA);
  int LSB = digitalRead(encoderB);

  int encoded = (MSB << 1) | LSB;
  int sum = (lastEncoded << 2) | encoded;

  if(sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011) encoderTicks++;
  if(sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) encoderTicks--;

  lastEncoded = encoded;
}

void setup() {
  pinMode(pwmPin, OUTPUT);
  pinMode(in1Pin, OUTPUT);
  pinMode(in2Pin, OUTPUT);
  digitalWrite(in1Pin, HIGH);
  digitalWrite(in2Pin, LOW);
  pinMode(encoderA, INPUT);
  pinMode(encoderB, INPUT);
  attachInterrupt(digitalPinToInterrupt(encoderA), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderB), updateEncoder, CHANGE);
  Serial.begin(57600);
  referencia = 80;
  Kp = 1.25;
  Ki = 0.075;
  Kd = 4;
  a = 0; //variable auxiliar para cambio de referencia (setpoint)
  RPM1.begin();
  RPMAvg.begin();
  Derivada.begin();
}

void loop() {
  if (Serial.available() > 0)
  {
    StringEntrada = Serial.readStringUntil('\n');
    StringSplitter *splitter = new StringSplitter(StringEntrada, ',', 40);  // new StringSplitter(string_to_split, delimiter, limit)
    inicio = splitter->getItemAtIndex(0).toInt();
    Kp = splitter->getItemAtIndex(1).toFloat();
    Ki = splitter->getItemAtIndex(2).toFloat();
    Kd = splitter->getItemAtIndex(3).toFloat();
    referencia = splitter->getItemAtIndex(4).toInt();
    time_delay = splitter->getItemAtIndex(5).toInt();
  }
  if (inicio==0){
    error=0;
    accionProp=0;
    accionInteg=0;
    accionDeriv=0;
    sumerror=0;
    sumaPID=0;
    analogWrite(pwmPin, sumaPID);
  }
  if (inicio==1){
    /*if(a==0){  //Genera referencias variables para entrenamiento red neuronal
      referencia=random(15,100);
      tiempoinicio=millis();
      a=1;
    }*/
    tiempoanterior=tiempo;
    tiempo=millis();
    tiempociclo=tiempo-tiempoanterior;
    /*if((tiempo-tiempoinicio>7500) && a==1){ //También requerido para la generación de valores para entrenamiento de red
      a=0;
    }*/
    encoderTicksAnterior=encoderTicksActual;
    encoderTicksActual=encoderTicks;
    deltaencoderTicks=encoderTicksActual-encoderTicksAnterior;
    RPM=deltaencoderTicks/(tiempociclo)*78.125;
    RPMPromedioanterior = RPMPromedio;
    RPM1erFilt=RPM1.reading(RPM);
    RPMPromedio=RPMAvg.reading(RPM1erFilt);
    error=referencia-RPMPromedio;
    accionProp = error*Kp;
    sumerror = (sumerror + error);
    accionInteg = sumerror*Ki;
    accionDeriv = Derivada.reading((RPMPromedio-RPMPromedioanterior)*Kd);
    sumaPID=accionProp+accionDeriv+accionInteg;
    sumaPID = constrain(sumaPID, 0, 255);
    analogWrite(pwmPin, sumaPID);

    Serial.print(int(referencia));
    Serial.print("  ");
    Serial.print(int(RPMPromedio));
    Serial.print("  ");
    Serial.print(int(accionProp));
    Serial.print("  ");
    Serial.print(int(accionInteg));
    Serial.print("  ");
    Serial.print(int(accionDeriv));
    Serial.print("  ");
    Serial.println(int(sumaPID));
    delay(time_delay+10);
  }
}