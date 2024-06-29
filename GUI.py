import sys
import random
import pyqtgraph as pg
import serial
from datetime import datetime
from collections import deque
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QDialogButtonBox
from PyQt6.QtCore import QTimer

class MyDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(MyDialog, self).__init__(parent)
        uic.loadUi('untitled.ui', self)
        # Initialize the serial connection (change 'COM3' to your serial port and set the appropriate baud rate)
        self.serial_port = serial.Serial('COM5', 57600, timeout=1)
        # Initialize data lists
        self.dataRPM_setpoint = deque(maxlen=400)
        self.dataRPM_measured = deque(maxlen=400)
        self.dataPWM = deque(maxlen=400)

        # Define el botón de start/stop
        self.StartStop.clicked.connect(self.toggleStartStop)
        self.isRunning = False

        # Define botón de update parameters
        self.update_parameters.clicked.connect(self.toggleupdate_parameters)

        # Ensure the placeholder widget is inside a layout
        # El widget para la gráfica había que meterlo dentro de un recipiente (layout)
        # El widget se llama RPM y aquí se asegura que tiene uno asociado
        placeholderLayoutRPM = self.RPM.parentWidget().layout()
        placeholderLayoutPWM = self.PWM.parentWidget().layout()

        # Replace the placeholder widget with the PlotWidget
        # El widget RPM no era un widget de gráfica, sino que se usó uno genérico
        # Pero hay que remplazarlo con uno que sí es para gráfica
        self.graphWidgetRPM = pg.PlotWidget()
        self.graphWidgetRPM.setYRange(0, 120)
        placeholderIndexRPM = placeholderLayoutRPM.indexOf(self.RPM)
        placeholderLayoutRPM.replaceWidget(self.RPM, self.graphWidgetRPM)
        self.RPM.deleteLater()  # Remove the placeholder

        self.graphWidgetPWM = pg.PlotWidget()
        self.graphWidgetPWM.setYRange(0, 255)
        placeholderLayoutPWM.replaceWidget(self.PWM, self.graphWidgetPWM)
        placeholderIndexPWM = placeholderLayoutRPM.indexOf(self.PWM)
        self.PWM.deleteLater()  # Remove the placeholder

        # Disconnect the standard dialog accept/reject slots
        # Esto se hace para quitarle los valores por default que tienen los botones de
        # Ok y cancel (que es cerrar la ventana)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).clicked.disconnect()
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).clicked.disconnect()

        # Connect the buttons to custom slots
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.ok_button_clicked)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.cancel_button_clicked)

        # Setup the QTimer
        # Este es el timer para la rapidez de update de la hora
        self.timerHora = QTimer(self)
        self.timerHora.setInterval(1000)
        self.timerHora.timeout.connect(self.updateDateTime)

        # Este es el timer para la rapidez de update de la gráfica
        self.timer = QTimer(self)
        self.timer.setInterval(10)  # Adjust the interval as needed
        self.timer.timeout.connect(self.update_graph)

        # Se inicializan los valores de Kp, Ki y Kd
        self.Kp.setText("1")
        self.Ki.setText("0.5")
        self.Kd.setText("2")
        self.reference.setText("100")
        self.delay.setText("10")
        
        # Comienza todos los timers
        self.timer.start()
        self.timerHora.start()

    def toggleupdate_parameters(self):
        # Collect the current values from UI elements or class variables
        StartStop = '0' if self.StartStop.text()=="Start" else '1'
        kp = self.Kp.text()
        ki = self.Ki.text()
        kd = self.Kd.text()
        reference = self.reference.text()
        delay =  self.delay.text()
        # Send the data
        self.SendData(StartStop, kp, ki, kd, reference, delay)

    def toggleStartStop(self):
            if self.isRunning:
                self.StartStop.setText("Start")
                self.StopAction()
            else:
                self.StartStop.setText("Stop")
                self.StartAction()
            self.isRunning = not self.isRunning

    def update_graph(self):
        try:
            # Continuously read lines from the serial port while there is data
            while self.serial_port.in_waiting:
                serial_data = self.serial_port.readline().decode('utf-8').strip()

                # Process the data
                values = list(map(float, serial_data.split()))
                if len(values) >= 3:  # Check if all required values are present
                    setpoint_rpm = values[0]
                    measured_rpm = values[1]
                    pwm_value = values[-1]

                    # Append new data to deques
                    self.dataRPM_setpoint.append(setpoint_rpm)
                    self.dataRPM_measured.append(measured_rpm)
                    self.dataPWM.append(pwm_value)

                    # Update the plots with lines
                    self.graphWidgetRPM.plot(list(self.dataRPM_setpoint), pen='b', clear=True)  # blue line for setpoint
                    self.graphWidgetRPM.plot(list(self.dataRPM_measured), pen='r', clear=False)  # red line for measured RPM
                    self.graphWidgetPWM.plot(list(self.dataPWM), pen='g', clear=True)  # green line for PWM

            # Save data if the checkbox is checked
            if self.saveValuesCheckBox.isChecked():
                with open('datos.txt', 'a') as file:
                    file.write(f"{setpoint_rpm},{measured_rpm},{pwm_value}\n")
        except Exception as e:
            print(f"Error: {e}")

    def ok_button_clicked(self):
        self.textBrowser.setText("Ok button pressed")

    def cancel_button_clicked(self):
        self.textBrowser.setText("Cancel button pressed")

    def updateDateTime(self):
        now = datetime.now()
        dateTimeString = now.strftime("%H:%M:%S\n%d-%m-%Y")
        self.dateTimeLabel.setText(dateTimeString)

    def StartAction(self):
        print("Inicio control motor")
        StartStop=b'1'
        self.toggleupdate_parameters()

    def StopAction(self):
        print("Paro de control de motor")
        StartStop=b'0'
        self.toggleupdate_parameters()

    def SendData(self, StartStop, Kp, Ki, Kd, reference, delay):
        data_string=f"{StartStop},{Kp},{Ki},{Kd},{reference},{delay}"
        data_bytes = data_string.encode('utf-8')
        self.serial_port.write(data_bytes)


app = QtWidgets.QApplication(sys.argv)
dialog = MyDialog()
dialog.show()
sys.exit(app.exec())