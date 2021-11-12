from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import serial
from serial.tools import list_ports
import sys
import time
import threading


def find_available_ports():
    ports = []
    raw_ports = list(list_ports.comports())
    for p in raw_ports:
        ports.append(p[0])
    return ports


class Worker(QtCore.QObject):
    def __init__(self, port, port_name, baudrate, pattern):
        super(Worker, self).__init__()
        self.port = port
        self.port_name = port_name
        self.baudrate = baudrate
        self.pattern = pattern
    sig = QtCore.pyqtSignal(str)

    def run(self):
        while True:
            try:
                line = self.port.readline().decode("utf-8")
            except serial.SerialException:
                pass
            self.sig.emit(line)
            if self.pattern:
                self.detect_pattern(line)

    def detect_pattern(self, line):
        for pat in self.pattern:
            if pat in line:
                print("success")
                return


class Etsm(QtWidgets.QMainWindow):
    def __init__(self, parent=None, port_name=None, baudrate=115200, displayed=1, pattern=[]):
        super().__init__(parent)
        self._port = None
        self._port_name = port_name
        self._baudrate = str(baudrate)
        self._displayed = displayed
        self._pattern = pattern

        self.window_title = "Event Trigger Software Management"
        self.width = 650
        self.height = 650
        self.menu_bar = self.menuBar()
        self.settings_menu = QtGui.QMenu("Settings")
        self.port_config_menu = QtGui.QMenu("Port Configurator")
        self.select_port_menu = QtGui.QMenu("Port Selector")
        self.port_checked = None
        self.select_baudrate_menu = QtGui.QMenu("Baudrate selector")
        self.baudrate_checked = None
        self.list_port_action = []
        self.list_baudrate_action = []
        self.test_menu = QtGui.QMenu("test")
        self.label_select_port = QtWidgets.QLabel("Select port")
        self.but_select_port = QtWidgets.QComboBox()
        self.available_ports = find_available_ports()
        self.label_connect_port = "Connect port"
        self.but_connect_port = QtWidgets.QPushButton()
        self.label_command = QtWidgets.QLabel("Command")
        self.edit_command = QtWidgets.QLineEdit()
        self.label_send_command = "Send"
        self.but_send_command = QtWidgets.QPushButton()
        self.label_console = QtWidgets.QLabel("Console")
        self.zone_console = QtWidgets.QTextEdit()
        self.status_bar = self.statusBar()
        self.layout = QtWidgets.QGridLayout()
        self.global_layout = QtWidgets.QHBoxLayout()
        self.global_widget = QtWidgets.QWidget()
        self.setup_graphics()

    def setup_graphics(self):
        self.setWindowTitle(self.window_title)
        self.resize(self.width, self.height)

        # Configures buttons
        self.but_select_port.addItems(self.available_ports)
        self.but_select_port.setCurrentIndex(self.but_select_port.findText(self._port_name))
        self.but_connect_port.setText(self.label_connect_port)
        self.but_send_command.setText(self.label_send_command)
        self.zone_console.setReadOnly(True)

        # Configures menu bar
        self.menu_bar.setNativeMenuBar(False)

        self.settings_menu.addAction("Help")
        self.settings_menu.addAction("Exit")

        for i, p in enumerate(self.available_ports):
            self.list_port_action.append(self.select_port_menu.addAction(p))
            self.list_port_action[i].setCheckable(True)
            if p == self._port_name:
                self.list_port_action[i].setChecked(True)
                self.port_checked = self.list_port_action[i]

        for j, b in enumerate(serial.SerialBase.BAUDRATES):
            self.list_baudrate_action.append(self.select_baudrate_menu.addAction(str(b)))
            self.list_baudrate_action[j].setCheckable(True)
            if str(b) == self._baudrate:
                self.list_baudrate_action[j].setChecked(True)
                self.baudrate_checked = self.list_baudrate_action[j]

        self.port_config_menu.addMenu(self.select_port_menu)
        self.port_config_menu.addMenu(self.select_baudrate_menu)

        self.menu_bar.addMenu(self.settings_menu)
        self.menu_bar.addMenu(self.port_config_menu)
        self.menu_bar.addMenu(self.test_menu)

        self.settings_menu.triggered[QtGui.QAction].connect(self.settings)
        self.port_config_menu.triggered[QtGui.QAction].connect(self.port_config_changed)

        # Add buttons to layer
        self.layout.addWidget(self.label_select_port, 0, 0, 1, 1)
        self.layout.addWidget(self.but_select_port, 0, 1, 1, 1)
        self.layout.addWidget(self.but_connect_port, 0, 2, 1, 1)
        self.layout.addWidget(self.label_command, 1, 0, 1, 1)
        self.layout.addWidget(self.edit_command, 1, 1, 1, 1)
        self.layout.addWidget(self.but_send_command, 1, 2, 1, 1)
        self.layout.addWidget(self.label_console, 2, 0, 1, 1)
        self.layout.addWidget(self.zone_console, 3, 1, 1, 1)

        self.global_layout.addLayout(self.layout)

        self.setCentralWidget(self.global_widget)
        self.centralWidget().setLayout(self.global_layout)

        # Connect buttons to functions
        self.but_connect_port.clicked.connect(self.change_port)
        self.but_send_command.clicked.connect(self.command_manager)

        self.open_port()

        self.worker = Worker(self._port, self._port_name, self._baudrate, self._pattern)
        self.thread_rx = QtCore.QThread(self)
        self.worker.sig.connect(self.display_port)
        self.worker.moveToThread(self.thread_rx)
        self.thread_rx.started.connect(self.worker.run)
        self.thread_rx.finished.connect(self.thread_rx.deleteLater)
        self.thread_rx.start()


    def exit_app(self):
        pass

    def settings(self, action):
        if action.text() == "Exit":
            print("Exit")
        else:
            print("Help")

    def port_config_changed(self, action):
        if action.parentWidget() == self.select_port_menu:
            if self.change_port(action.text()):
                self.port_checked.setChecked(False)
                self.port_checked = action
        if action.parentWidget() == self.select_baudrate_menu:
            if self.change_baudrate(action.text()):
                self.baudrate_checked.setChecked(False)
                self.baudrate_checked = action

    def change_baudrate(self, new_baudrate):
        if new_baudrate != self._baudrate:
            self._baudrate = new_baudrate
            self._port.baudrate = self._baudrate
            return 1
        else:
            return 0

    def change_port(self, new_port_name):
        if new_port_name != self._port_name:
            self._port_name = new_port_name
            self._port.port = self._port_name
            return 1
        else:
            return 0

    def command_manager(self):
        text = self.edit_command.displayText()
        if text:
            if len(text.split('.')) > 1:
                if text.split('.')[1] == ('txt' or 'sh'):
                    self.send_script(text)
                else:
                    print('bad extension')
            else:
                self.send_command(text)
            self.edit_command.clear()

    def open_port(self):
        try:
            self._port = serial.Serial(self._port_name, self._baudrate)
            self.status_bar.showMessage("Connected to " + self._port_name + " ; Baudrate " + str(self._baudrate))
        except serial.SerialException:
            print("Can't open port " + self._port_name + ".")
            sys.exit()

    def close_port(self):
        self._port.close()

    def send_command(self, command):
        self._port.write(command.encode())

    def send_script(self, script):
        '''open the script and send each command, if delay put in sleep'''
        try:
            with open(script, mode='r') as f:
                command_lines = f.readlines()
                for command in command_lines:
                    if command.split(' ')[0] == 'delay':
                        time.sleep(int(command.split(' ')[1]))
                    else:
                        self.send_command(command)
        except IOError:
            print("Can't read script " + script + ".")

    def display_port(self, line):
        print(line)
        self.zone_console.append(line)

    def get_pattern(self):
        return self._pattern

    def set_pattern(self, pattern):
        self._pattern = [pattern]

    def add_pattern(self, pattern):
        self._pattern.append(pattern)

    def del_pattern(self):
        self._pattern = []

    def get_displayed(self):
        return self._displayed

    def set_displayed(self, disp):
        self._displayed = disp

    def get_command(self):
        return self._command

    def set_command(self, command):
        self._command = command

    def add_command(self, command):
        self._command.append(command)

    def del_command(self):
        self._command = []

    def get_port_name(self):
        return self._port_name

    def set_port_name(self, port_name):
        self._port_name = port_name

    def get_port(self):
        return self._port


if __name__ == '__main__':
    '''
    try:
        etsm = Etsm('/dev/ttyACM0', 115200, pattern=["Starting kernel ..."])
        etsm.open_port()
        etsm.get_pattern()
        etsm.add_pattern("mmcblk2boot0")
        etsm.get_pattern()
        thread_rx_stop = threading.Event()
        thread_rx = threading.Thread(target=etsm.read_port, args=(thread_rx_stop,))
        thread_rx.start()
        while True:
            time.sleep(1)
        #thread_rx_stop.wait()
        #time.sleep(10)
        #etsm.send_script('script.txt')
    except KeyboardInterrupt:
        thread_rx_stop.set()
        thread_rx.join()
        etsm.close_port()
    '''
    app = QtGui.QApplication([])
    etsm = Etsm(port_name='/dev/ttyACM0', baudrate=115200, pattern=["0.030161"])
    etsm.show()
    QtGui.QApplication.instance().exec_()
