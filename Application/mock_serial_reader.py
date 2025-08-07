import random
import math
from PyQt5.QtCore import pyqtSignal, QObject
from base_serial_reader import BaseSerialReader

##############################
# Mock Serial Reader (for testing)
##############################
class MockSerialReader(QObject, BaseSerialReader):
    dataReceived = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)
        BaseSerialReader.__init__(self)
        self.i = 0  # a counter to simulate changing data
        # Initialize variables with dummy values.
        self.velocity = 0.0
        self.distance_travelled = 0.0
        self.battery_volt = 140.0
        self.battery_current = 5.0
        self.battery_cell_LOW_volt = 3.2
        self.battery_cell_HIGH_volt = 3.8
        self.battery_cell_AVG_volt = (3.2 + 3.8) / 2
        self.battery_cell_LOW_temp = 25.0
        self.battery_cell_HIGH_temp = 35.0
        self.battery_cell_AVG_temp = (25.0 + 35.0) / 2
        self.battery_cell_ID_HIGH_temp = 33.0
        self.battery_cell_ID_LOW_temp = 27.0
        self.BMS_temp = 28.0
        self.motor_current = 10.0
        self.motor_temp = 50.0
        self.motor_controller_temp = 45.0
        self.MPPT1_watt = 80.0
        self.MPPT2_watt = 90.0
        self.MPPT3_watt = 70.0
        self.MPPT_total_watt = self.MPPT1_watt + self.MPPT2_watt + self.MPPT3_watt

        self.latest_values = {
            "velocity": self.velocity,
            "distance_travelled": self.distance_travelled,
            "battery_volt": self.battery_volt,
            "battery_current": self.battery_current,
            "battery_cell_LOW_volt": self.battery_cell_LOW_volt,
            "battery_cell_HIGH_volt": self.battery_cell_HIGH_volt,
            "battery_cell_AVG_volt": self.battery_cell_AVG_volt,
            "battery_cell_LOW_temp": self.battery_cell_LOW_temp,
            "battery_cell_HIGH_temp": self.battery_cell_HIGH_temp,
            "battery_cell_AVG_temp": self.battery_cell_AVG_temp,
            "battery_cell_ID_HIGH_temp": self.battery_cell_ID_HIGH_temp,
            "battery_cell_ID_LOW_temp": self.battery_cell_ID_LOW_temp,
            "BMS_temp": self.BMS_temp,
            "motor_current": self.motor_current,
            "motor_temp": self.motor_temp,
            "motor_controller_temp": self.motor_controller_temp,
            "MPPT1_watt": self.MPPT1_watt,
            "MPPT2_watt": self.MPPT2_watt,
            "MPPT3_watt": self.MPPT3_watt,
            "MPPT_total_watt": self.MPPT_total_watt
        }
        # Populate the history with the initial values.
        for key, value in self.latest_values.items():
            self.history[key].pop(0)
            self.history[key].append(value)

    def start(self):
        # No action needed for the mock.
        pass

    def stop(self):
        pass

    def update(self):
        # Simulate new readings for each variable.
        if self.velocity < 100:  # Accelerate smoothly from 0 to 100 km/h
            self.velocity = 100 * (1 - math.cos(self.i * math.pi / 100))
        else:  # Maintain velocity around 100 km/h with small variations
            self.velocity = 100 + random.uniform(-5, 5)
        # Increase distance_travelled continuously:
        self.distance_travelled += abs(math.sin(self.i / 10))
        # Simulate battery voltage drop
        initial_voltage = 140.0
        threshold_voltage = initial_voltage * 0.2  # 20% of the initial voltage
        if self.battery_volt > threshold_voltage:
            # Slow drop
            self.battery_volt -= random.uniform(1, 5)
        elif self.battery_volt > 0.0:
            # Fast drop
            self.battery_volt -= random.uniform(5, 10)
        
        self.battery_current = random.uniform(2, 5)
        self.battery_cell_LOW_volt = random.uniform(3.0, 3.4)
        self.battery_cell_HIGH_volt = random.uniform(3.6, 4.0)
        self.battery_cell_AVG_volt = (self.battery_cell_LOW_volt + self.battery_cell_HIGH_volt) / 2
        self.battery_cell_LOW_temp = random.uniform(20, 25)
        self.battery_cell_HIGH_temp = random.uniform(30, 35)
        self.battery_cell_AVG_temp = (self.battery_cell_LOW_temp + self.battery_cell_HIGH_temp) / 2
        self.battery_cell_ID_HIGH_temp = random.randint(1, 8)
        self.battery_cell_ID_LOW_temp = random.randint(11, 42)
        self.BMS_temp = random.uniform(18, 24)
        self.motor_current = random.uniform(0, 15)
        self.motor_temp = random.uniform(40, 60)
        self.motor_controller_temp = random.uniform(40, 60)
        self.MPPT1_watt = random.uniform(300, 400)
        self.MPPT2_watt = random.uniform(0, 400)
        self.MPPT3_watt = random.uniform(300, 400)
        self.MPPT4_watt = random.uniform(200, 400)
        self.MPPT_total_watt = self.MPPT1_watt + self.MPPT2_watt + self.MPPT3_watt
        self.i += 1

        self.latest_values = {
            "velocity": self.velocity,
            "distance_travelled": self.distance_travelled,
            "battery_volt": self.battery_volt,
            "battery_current": self.battery_current,
            "battery_cell_LOW_volt": self.battery_cell_LOW_volt,
            "battery_cell_HIGH_volt": self.battery_cell_HIGH_volt,
            "battery_cell_AVG_volt": self.battery_cell_AVG_volt,
            "battery_cell_LOW_temp": self.battery_cell_LOW_temp,
            "battery_cell_HIGH_temp": self.battery_cell_HIGH_temp,
            "battery_cell_AVG_temp": self.battery_cell_AVG_temp,
            "battery_cell_ID_HIGH_temp": self.battery_cell_ID_HIGH_temp,
            "battery_cell_ID_LOW_temp": self.battery_cell_ID_LOW_temp,
            "BMS_temp": self.BMS_temp,
            "motor_current": self.motor_current,
            "motor_temp": self.motor_temp,
            "motor_controller_temp": self.motor_controller_temp,
            "MPPT1_watt": self.MPPT1_watt,
            "MPPT2_watt": self.MPPT2_watt,
            "MPPT3_watt": self.MPPT3_watt,
            "MPPT_total_watt": self.MPPT_total_watt
        }
        # Update the history arrays for each variable.
        for key, value in self.latest_values.items():
            self.history[key].pop(0)
            self.history[key].append(value)
