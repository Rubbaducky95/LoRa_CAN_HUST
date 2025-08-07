import sys
import os
import csv
import datetime
import serial
from network import insert_into_db  # Assuming this is a custom module for database operations
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QComboBox, QLabel, QHBoxLayout, QTextEdit, QPushButton
)
from PyQt5.QtGui import QMovie, QPixmap, QIcon
from PyQt5.QtCore import QTimer, QThread, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from serial_reader import SerialReader
from mock_serial_reader import MockSerialReader
from connection_worker import ConnectionWorker
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from battery_widget import VerticalBatteryWidget  # Import the custom battery widget
from speedometer_widget import SpeedometerWidget

##############################
# Main Application Class with CSV Logging, Recovery, and Timestamp Rounding
##############################
class PlotApp(QMainWindow):
    def __init__(self, serial_reader):
        super().__init__()
        self.serial_reader = serial_reader

        self.setWindowTitle("HUST - Henry Live Data")
        self.setGeometry(100, 100, 1280, 900)

        # Set the window icon to the logo
        self.setWindowIcon(QIcon('HUST_logo.png'))  # Ensure "logo.png" exists in your folder

        # Apply the style sheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #white;  /* Dark blue background for the main window */
            }
            QLabel {
                color: 1a206c;  /* White text for labels */
            }
            QComboBox {
                background-color: #254c9a;  /* Slightly lighter dark blue for combo boxes */
                color: white;  /* White text */
                border: 2px solid #3e81f0;  /* Border color matching the logo color */
                padding: 5px;
            }
            QPushButton {
                background-color: #3e81f0;  /* Logo color for buttons */
                color: white;  /* White text */
                border: 2px solid #254c9a;  /* Dark blue border */
                padding: 5px;
            }
            QPushButton:pressed {
                background-color: #254c9a;  /* Darker blue when pressed */
                border: 2px solid #3e81f0;  /* Logo color border */
            }
            QPushButton:disabled {
                background-color: #8ab4f8;  /* Lighter blue when disabled */
                color: #cccccc;  /* Light gray text for disabled state */
                border: 2px solid #777777;  /* Gray border for disabled state */
            }
            QTextEdit {
                background-color: #a4aaf3;  /* Light gray background for text areas */
                color: black;  /* Black text for better readability */
                border: 1px solid #3e81f0;  /* Border color matching the logo color */
            }
        """)


        # Main layout: graphs on the left, COM port selection and messages on the right.
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # --- Left layout ---
        self.left_layout = QVBoxLayout()

        # Buttons for graphs
        self.graph_buttons_layout = QHBoxLayout()
        self.graph_buttons_layout.setSpacing(10)
        self.graph_buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Graph Variable Selectors (exclude distance_travelled)
        self.graph_selector_layout = QHBoxLayout()
        self.graph_selector_layout.setSpacing(10)
        self.graph_selector_layout.setContentsMargins(0, 0, 0, 0)

        self.graph_dropdowns = []
        self.figures = []
        self.axes = []
        self.canvases = []

        # Time Interval Selector
        self.time_unit_dropdown = QComboBox()
        self.time_unit_dropdown.addItems(["2 s", "1 min"])
        self.time_unit_dropdown.currentTextChanged.connect(self.update_all_graphs)
        time_unit_and_text = QHBoxLayout()
        time_unit_and_text.addWidget(QLabel("Time Interval:"))
        time_unit_and_text.addWidget(self.time_unit_dropdown)
        self.graph_buttons_layout.addLayout(time_unit_and_text)

        # Add buttons for adding and removing graphs
        self.add_graph_button = QPushButton("Add Graph")
        self.add_graph_button.clicked.connect(self.add_graph)
        self.remove_graph_button = QPushButton("Remove Graph")
        self.remove_graph_button.clicked.connect(self.remove_graph)
        add_remove_buttons_layout = QHBoxLayout()
        add_remove_buttons_layout.addWidget(self.remove_graph_button)
        add_remove_buttons_layout.addWidget(self.add_graph_button)
        self.graph_buttons_layout.addLayout(add_remove_buttons_layout)

        self.graph_buttons_layout.setAlignment(Qt.AlignLeft)
        self.graph_selector_layout.setAlignment(Qt.AlignLeft)

        self.left_layout.addLayout(self.graph_buttons_layout)
        self.left_layout.addLayout(self.graph_selector_layout)

        self.main_layout.addLayout(self.left_layout, 8)

        

        # --- Right layout ---
        self.right_layout = QVBoxLayout()
        self.logo_and_com_port_layout = QHBoxLayout()
        self.battery_and_speedometer_layout = QHBoxLayout()

        # Port Selector
        self.port_selector_layout = QHBoxLayout()
        self.port_selector_layout.setSpacing(5)
        self.port_selector_layout.setContentsMargins(0, 0, 0, 0)
        self.port_label = QLabel("Select COM Port:")
        self.port_dropdown = QComboBox()
        self.populate_com_ports()
        self.port_dropdown.currentTextChanged.connect(self.update_com_port)
        self.port_selector_layout.addWidget(self.port_label)
        self.port_selector_layout.addWidget(self.port_dropdown)
        self.port_selector_layout.setAlignment(Qt.AlignBottom)
        self.logo_and_com_port_layout.addLayout(self.port_selector_layout)

        # Add a logo label to the right layout
        self.logo_label = QLabel(self)
        self.logo_pixmap = QPixmap('HUST_logo.png').scaled(100, 100, Qt.KeepAspectRatio)  # Scale the logo to 100x100 pixels
        self.logo_label.setPixmap(self.logo_pixmap)
        self.logo_label.setFixedSize(100, 100)  # Set the fixed size of the logo label
        self.logo_label.setAlignment(Qt.AlignRight)
        self.logo_and_com_port_layout.addWidget(self.logo_label)

        self.right_layout.addLayout(self.logo_and_com_port_layout)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setText("Application Ready.")
        self.right_layout.addWidget(self.text_box)

        # Add a loading label to indicate data is being received.
        self.loading_label = QLabel(self)
        self.loading_movie = QMovie("loading.gif")  # Ensure "loading.gif" exists in your folder
        self.loading_label.setMovie(self.loading_movie)
        self.loading_label.setVisible(False)
        # Add the loading label next to the COM port dropdown:
        self.port_selector_layout.addWidget(self.loading_label)

        # Speed Gauge Widget
        self.speedometer_widget = SpeedometerWidget()
        self.battery_and_speedometer_layout.addWidget(self.speedometer_widget)

        # Battery Widget
        self.battery_widget = VerticalBatteryWidget()
        self.battery_and_speedometer_layout.addWidget(self.battery_widget)

        self.right_layout.addLayout(self.battery_and_speedometer_layout)

        self.main_layout.addLayout(self.right_layout, 2)

        # Add initial graphs
        self.add_graph()
        self.add_graph()

        # Connect serial data signal to update the graphs.
        if hasattr(self.serial_reader, 'dataReceived'):
            self.serial_reader.dataReceived.connect(self.update_all_graphs)

        
        # --- CSV Logging Setup ---
        self.log_buffer = []  # buffer to accumulate log rows
        self.log_filename = "can_data_log.csv"
        # If the CSV file does not exist, create it and write a header row.
        if not os.path.exists(self.log_filename):
            with open(self.log_filename, "w", newline="") as f:
                writer = csv.writer(f)
                header = ["timestamp"] + self.serial_reader.available_data
                writer.writerow(header)
        # A timer to flush the log buffer to file once per minute.
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.flush_log_buffer)
        self.log_timer.start(60000)  # 60000 ms = 1 minute

        # Log each new CAN message.
        self.serial_reader.dataReceived.connect(self.on_new_data)

        # number of samples in your buffer
        self.max_samples = len(self.serial_reader.history[self.serial_reader.available_data[0]])
        # initialize with “empty” slots
        self.time_history = [None]*self.max_samples

        # Mapping for display names
        self.display_names = {
            "velocity": "Velocity",
            "battery_cell_LOW_temp": "Lowest Cell Temp",
            "battery_cell_HIGH_temp": "Highest Cell Temp",
            "battery_cell_AVG_temp": "Average Cell Temp",
            "BMS_temp": "BMS Temp",
            "battery_volt": "Battery Voltage",
            "battery_current": "Battery Current",
            "motor_temp": "Motor Temp",
            "motor_controller_temp": "Motor Controller Temp",
            "MPPT1_watt": "MPPT 1 Power",
            "MPPT2_watt": "MPPT 2 Power",
            "MPPT3_watt": "MPPT 3 Power",
            "MPPT4_watt": "MPPT 4 Power",
            "MPPT_total_watt": "Total MPPT Power",
            "Battery Power": "Battery Power",
            "Total MPPT Watt": "Total MPPT Power"
        }

        # Recover any saved CAN data from the CSV file.
        self.recover_csv_data()
        self.update_all_graphs()

        # For the mock reader, use a timer to update data every second.
        if isinstance(self.serial_reader, MockSerialReader):
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.mock_update)
            self.timer.start(1000)

    def populate_com_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_dropdown.clear()
        self.port_dropdown.addItems(ports)

    def update_com_port(self, port):
        self.serial_reader.set_port(port)
        if port:
            self.start_loading()
            # Create a QThread and ConnectionWorker.
            self.connection_thread = QThread()
            self.connection_worker = ConnectionWorker(self.serial_reader, port)
            self.connection_worker.moveToThread(self.connection_thread)
            self.connection_thread.started.connect(self.connection_worker.run)
            self.connection_worker.finished.connect(self.on_connection_finished)
            self.connection_worker.finished.connect(self.connection_thread.quit)
            self.connection_worker.finished.connect(self.connection_worker.deleteLater)
            self.connection_thread.finished.connect(self.connection_thread.deleteLater)
            self.connection_thread.start()

    def mock_update(self):
        self.serial_reader.update()
        self.update_all_graphs()

    def get_y_label(self, variable):
        """Return an appropriate unit string based on the variable name."""
        if "watt" in variable:
            return "Watts"
        elif "volt" in variable:
            return "Volt"
        elif "current" in variable:
            return "Ampere"
        elif "temp" in variable:
            return "°C"
        else:
            return ""

    def get_rounded_timestamp(self):
        """
        Get the current timestamp rounded to the nearest second.
        If microseconds are 500,000 or more, round up; otherwise, round down.
        Returns a string in ISO format without decimals.
        """
        now = datetime.datetime.now()
        # Add 500,000 microseconds and then replace microseconds with 0.
        rounded = (now + datetime.timedelta(microseconds=500000)).replace(microsecond=0)
        return rounded.isoformat()

    def update_graph(self, graph_id):
        import matplotlib.dates as mdates
        import matplotlib.ticker as mticker

        # Determine the sample interval in seconds from the dropdown.
        time_option = self.time_unit_dropdown.currentText()
        if time_option == "2 s":
            sample_interval = 2
        elif time_option == "1 min":
            sample_interval = 60
        else:
            sample_interval = 2

        # Get the current time (for graphing, we don't require rounding here).
        now = datetime.datetime.now()

        # Select the appropriate axis and dropdown based on graph_id
        ax = self.axes[graph_id - 1]
        canvas = self.canvases[graph_id - 1]
        selected_var = self.graph_dropdowns[graph_id - 1].currentText()

        ax.clear()

        if selected_var == "Velocity":
            data = self.serial_reader.history.get("velocity", [])
            title = "Velocity"
            ylabel = "Km/h)"

        elif selected_var == "Battery Temps":
            battery_temp_vars = [
                "battery_cell_LOW_temp", "battery_cell_HIGH_temp", "battery_cell_AVG_temp", "BMS_temp"
            ]
            data = {var: self.serial_reader.history.get(var, []) for var in battery_temp_vars}
            title = "Battery Temperatures"
            ylabel = "°C"

            # Annotate cell IDs
            low_temp_id = self.serial_reader.latest_values.get("battery_cell_ID_LOW_temp", "N/A")
            high_temp_id = self.serial_reader.latest_values.get("battery_cell_ID_HIGH_temp", "N/A")
            ax.annotate(f"Low Temp ID: {low_temp_id}", xy=(0.05, 0.95), xycoords='axes fraction', fontsize=10,
                        horizontalalignment='left', verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))
            ax.annotate(f"High Temp ID: {high_temp_id}", xy=(0.05, 0.85), xycoords='axes fraction', fontsize=10,
                        horizontalalignment='left', verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))

        elif selected_var == "Motor Temps":
            motor_temp_vars = ["motor_temp", "motor_controller_temp"]
            data = {var: self.serial_reader.history.get(var, []) for var in motor_temp_vars}
            title = "Motor Temperatures"
            ylabel = "°C"

        elif selected_var == "MPPT power":
            mppt_vars = ["MPPT1_watt", "MPPT2_watt", "MPPT3_watt", "MPPT4_watt", "MPPT_total_watt"]
            data = {var: self.serial_reader.history.get(var, []) for var in mppt_vars}
            title = "MPPT Power"
            ylabel = "Watts"

        elif selected_var == "Power trade-off":
            battery_current = self.serial_reader.history.get("battery_current", [])
            battery_voltage = self.serial_reader.history.get("battery_volt", [])
            total_mppt_watt = self.serial_reader.history.get("MPPT_total_watt", [])

            # Determine the minimum length to avoid index out of range errors
            min_length = min(len(battery_current), len(battery_voltage), len(total_mppt_watt))

            # Calculate battery power for the valid range
            battery_power = [battery_current[i] * battery_voltage[i] for i in range(min_length)]

            data = {
                "Battery Power": battery_power,
                "Total MPPT Watt": total_mppt_watt[:min_length],
            }
            title = "Power Trade-off"
            ylabel = "Watts"

            # Calculate the difference between battery power and MPPT power
            power_difference = -battery_power[-1] + total_mppt_watt[-1]

            # Annotate the power difference
            ax.annotate(f"Power Difference: {power_difference:.2f} W", xy=(0.05, 0.95), xycoords='axes fraction', fontsize=10,
                        horizontalalignment='left', verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))

        else:
            data = self.serial_reader.history.get(selected_var, [])
            title = selected_var
            ylabel = self.get_y_label(selected_var)

        # Plot the data
        if isinstance(data, dict):
            for label, values in data.items():
                times = [now - datetime.timedelta(seconds=(len(values) - 1 - i) * sample_interval)
                        for i in range(len(values))]
                x = mdates.date2num(times)
                ax.plot(x, values, '-', label=self.display_names.get(label, label))
            ax.legend()
        else:
            times = [now - datetime.timedelta(seconds=(len(data) - 1 - i) * sample_interval)
                    for i in range(len(data))]
            x = mdates.date2num(times)
            ax.plot(x, data, '-')

        ax.set_title(title)
        ax.set_xlabel("Time")
        ax.set_ylabel(ylabel)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.xaxis.set_major_locator(mticker.MaxNLocator(4))
        canvas.draw()

    def update_all_graphs(self):
        for i in range(1, len(self.graph_dropdowns) + 1):
            self.update_graph(i)
        self.update_battery_widget()
        self.update_speedometer_widget()

    def update_battery_widget(self):
        battery_volt = self.serial_reader.latest_values.get("battery_volt", 0.0)
        self.battery_widget.setVoltage(battery_volt)

    def update_speedometer_widget(self):
        velocity = self.serial_reader.latest_values.get("velocity", 0.0)
        distance = self.serial_reader.latest_values.get("distance_travelled", 0.0)
        self.speedometer_widget.updateSpeedometer(velocity, distance)

    def on_new_data(self):
        """
        This slot is called every time a new CAN data packet is received.
        It formats the latest values as a CSV row (prefixed with a rounded timestamp)
        and appends it to the logging buffer.
        """
        ts = datetime.datetime.now()
        self.time_history.pop(0)
        self.time_history.append(ts)

        timestamp = self.get_rounded_timestamp()
        data_list = [str(self.serial_reader.latest_values.get(key, "")) for key in self.serial_reader.available_data]
        csv_row = [timestamp] + data_list
        self.log_buffer.append(csv_row)
        # Write the latest values to the database.
        #print(f"[DEBUG] Writing to DB: {self.serial_reader.latest_values}")
        insert_into_db(self.serial_reader.latest_values)
        self.update_all_graphs()

    def flush_log_buffer(self):
        """Write the contents of the log buffer to the CSV file and clear the buffer."""
        if not self.log_buffer:
            return
        try:
            with open(self.log_filename, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(self.log_buffer)
        except Exception as e:
            print(f"[DEBUG] Error writing to log file: {e}")
        self.log_buffer.clear()

    def recover_csv_data(self):
        """Read only the *last* max_samples lines and fill both history *and* time_history."""
        if not os.path.exists(self.log_filename):
            return

        # load rows
        try:
            with open(self.log_filename, "r", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            print(f"[DEBUG] Error reading CSV file: {e}")
            return

        # drop header
        if rows and rows[0][0].lower() == "timestamp":
            rows = rows[1:]

        # take only the tail
        recent = rows[-self.max_samples:]
        start = self.max_samples - len(recent)

        # prepare empty buffers
        recovered = { key: [0.0]*self.max_samples for key in self.serial_reader.available_data }
        times     = [None]*self.max_samples

        for idx, row in enumerate(recent):
            # parse timestamp
            try:
                rt = datetime.datetime.fromisoformat(row[0])
            except:
                rt = None
            times[start+idx] = rt

            # fill each variable
            for j,var in enumerate(self.serial_reader.available_data):
                try:
                    val = float(row[1+j])
                except:
                    val = 0.0
                recovered[var][start+idx] = val

        # commit back into reader + our time buffer
        for var in self.serial_reader.available_data:
            self.serial_reader.history[var]     = recovered[var].copy()
            # latest_values should reflect the last recovered sample
            self.serial_reader.latest_values[var] = recovered[var][-1]

        self.time_history = times
        print("[DEBUG] CSV data recovery complete.")

    def start_loading(self):
        self.loading_label.setVisible(True)
        self.loading_movie.start()

    def stop_loading(self):
        self.loading_movie.stop()
        self.loading_label.setVisible(False)

    def on_connection_finished(self, success):
        self.stop_loading()
        if not success:
            print(f"[DEBUG] Failed to open port {self.serial_reader.selected_port}")

    def add_graph(self):

        if len(self.graph_dropdowns) >= 4:
            return

        # Create a new dropdown, figure, axis, and canvas for the new graph
        graph_dropdown = QComboBox()
        graph_dropdown.addItems(["Velocity", "Battery Temps", "Motor Temps", "MPPT power", "Power trade-off"])
        graph_dropdown.setCurrentText("Velocity")
        graph_dropdown.currentTextChanged.connect(lambda _, id=len(self.graph_dropdowns) + 1: self.update_graph(id))
        self.graph_dropdowns.append(graph_dropdown)

        figure, ax = plt.subplots()
        canvas = FigureCanvas(figure)
        self.figures.append(figure)
        self.axes.append(ax)
        self.canvases.append(canvas)

        # Add the new dropdown and canvas to the layout
        self.graph_selector_layout.addWidget(QLabel(f"Graph {len(self.graph_dropdowns)}:"))
        self.graph_selector_layout.addWidget(graph_dropdown)
        self.left_layout.addWidget(canvas)

        # Update all graphs to reflect the changes
        self.update_all_graphs()

        # Update buttons
        self.remove_graph_button.setDisabled(False)
        if len(self.graph_dropdowns) >= 4:
            self.add_graph_button.setDisabled(True)

    def remove_graph(self):

        if len(self.graph_dropdowns) <= 1:
            return

        # Remove the last dropdown, figure, axis, and canvas
        graph_dropdown = self.graph_dropdowns.pop()
        figure = self.figures.pop()
        ax = self.axes.pop()
        canvas = self.canvases.pop()

        # Remove the dropdown and canvas from the layout
        self.graph_selector_layout.removeWidget(graph_dropdown)
        self.left_layout.removeWidget(canvas)
        graph_dropdown.deleteLater()
        canvas.deleteLater()

        # Update all graphs to reflect the changes
        self.update_all_graphs()

        # Update buttons
        self.add_graph_button.setDisabled(False)
        if len(self.graph_dropdowns) <= 1:
            self.remove_graph_button.setDisabled(True)

