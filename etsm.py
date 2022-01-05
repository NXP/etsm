import argparse
import os
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import serial
from serial.tools import list_ports
import signal
import sys
import time


def find_available_ports():
    ports = []
    raw_ports = list(list_ports.comports())
    for p in raw_ports:
        ports.append(p[0])
    return ports


class Port(QtCore.QObject):
    sig_display_port = QtCore.pyqtSignal(str, int)
    sig_clean_command_area = QtCore.pyqtSignal()
    sig_pattern_detected = QtCore.pyqtSignal(str)

    def __init__(self, port_name, baudrate, pattern, command):
        super(Port, self).__init__()
        self._port = None
        self._port_name = port_name
        self._baudrate = str(baudrate)
        self._pattern = pattern
        self._command = command
        self.exit = False

        self.open_port()

    def run(self):
        while not self.exit:
            try:
                line = self._port.readline().decode("utf-8")
            except (serial.SerialException, TypeError) as e:
                pass
            if line is not "":
                if self._pattern:
                    ret = self.detect_pattern(line)
                    self.sig_display_port.emit(line, ret)
                else:
                    self.sig_display_port.emit(line, 0)

    def stop(self):
        self.exit = True

    def detect_pattern(self, line):
        for pat in self._pattern:
            if pat in line:
                self.sig_pattern_detected.emit(pat)
                return 1
        return 0

    def open_port(self):
        try:
            self._port = serial.Serial(self._port_name, self._baudrate, timeout=1)
        except serial.SerialException:
            print("Can't open port " + self._port_name + ".")
            sys.exit()

    def close_port(self):
        self._port.close()

    def send_command(self, command):
        self._port.write((command+"\r").encode())

    def send_script(self, script, file=False):
        '''open the script or group of command and send each command, if delay put in sleep'''
        if file:
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
        else:
            for command in script:
                if command.split(' ')[0] == 'delay':
                    time.sleep(int(command.split(' ')[1]))
                else:
                    self.send_command(command)

    def command_manager(self, text):
        if text:
            if len(text.split('.')) > 1:
                if text.split('.')[1] == ('txt' or 'sh'):
                    self.send_script(text, file=True)
                else:
                    print('bad extension')
            else:
                self.send_command(text)
            self.sig_clean_command_area.emit()

    def pattern_manager(self, text):
        if text:
            if text not in self._pattern:
                self._pattern.append(text)

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

    def save_traces(self, filename, traces):
        with open(filename, 'w') as f:
            f.write(traces)

    def get_pattern(self):
        return self._pattern

    def set_pattern(self, pattern):
        self._pattern = pattern

    def add_pattern(self, pattern):
        self._pattern.append(pattern)

    def del_pattern(self):
        self._pattern = []

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

    def get_baudrate(self):
        return self._baudrate

    def set_baudrate(self, baudrate):
        self._baudrate = baudrate


class Etsm(QtWidgets.QMainWindow):
    sig_stop_thread = QtCore.pyqtSignal()

    def __init__(self, parent=None, port_name=None, baudrate=115200, displayed=1, pattern=[], command=[]):
        super().__init__(parent)
        self.port_name = port_name
        self.baudrate = str(baudrate)
        self.displayed = displayed
        self.pattern = pattern
        self.command = command
        self.window_title = "Event Trigger Software Management"
        self.width = 650
        self.height = 650
        self.menu_bar = self.menuBar()
        self.settings_menu = QtGui.QMenu("Settings")
        self.port_config_menu = QtGui.QMenu("Port Configurator")
        self.select_port_menu = QtGui.QMenu("&Port Selector")
        self.refresh_port = QtGui.QAction("Refresh ...")
        self.port_checked = None
        self.select_baudrate_menu = QtGui.QMenu("&Baudrate selector")
        self.baudrate_checked = None
        self.list_port_action = []
        self.list_baudrate_action = []
        self.file_menu = QtGui.QMenu("File")
        self.file_action = QtWidgets.QAction("&Save Traces as ...")
        self.toolbar = self.addToolBar("toolbar")
        self.command_manager_action = QtGui.QAction()
        self.pattern_manager_action = QtGui.QAction()
        self.command_historic_window = QtWidgets.QDialog()
        self.command_historic_window_lay = QtWidgets.QVBoxLayout()
        self.command_historic_window_edit = QtWidgets.QTextEdit()
        self.command_historic_window_but = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        self.pattern_historic_window = QtWidgets.QDialog()
        self.pattern_historic_window_lay = QtWidgets.QVBoxLayout()
        self.pattern_historic_window_edit = QtWidgets.QTextEdit()
        self.pattern_historic_window_but = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        self.available_ports = find_available_ports()
        self.label_command = QtWidgets.QLabel("Command")
        self.edit_command = QtWidgets.QLineEdit()
        self.label_send_command = "Send"
        self.but_send_command = QtWidgets.QPushButton()
        self.label_pattern = QtWidgets.QLabel("Pattern")
        self.edit_pattern = QtWidgets.QLineEdit()
        self.label_accept_pattern = "OK"
        self.but_accept_pattern = QtWidgets.QPushButton()
        self.label_console = QtWidgets.QLabel("Console")
        self.zone_console = QtWidgets.QPlainTextEdit()
        self.status_bar = self.statusBar()
        self.status_bar_label = QtWidgets.QLabel()
        self.layout = QtWidgets.QGridLayout()
        self.global_layout = QtWidgets.QHBoxLayout()
        self.global_widget = QtWidgets.QWidget()

        signal.signal(signal.SIGINT, self.exit_app)
        self.setup_graphics()

    def setup_graphics(self):
        self.worker = Port(self.port_name, self.baudrate, self.pattern, self.command)
        self.thread_rx = QtCore.QThread(self)

        self.worker.sig_display_port.connect(self.display_port)
        self.worker.sig_clean_command_area.connect(self.clean_command_area)
        self.sig_stop_thread.connect(self.worker.stop)

        self.worker.moveToThread(self.thread_rx)
        self.thread_rx.started.connect(self.worker.run)
        self.thread_rx.finished.connect(self.thread_rx.deleteLater)

        self.setWindowTitle(self.window_title)
        self.resize(self.width, self.height)

        # Configures buttons
        self.but_send_command.setText(self.label_send_command)
        self.but_accept_pattern.setText(self.label_accept_pattern)
        self.zone_console.setReadOnly(True)

        # Configures menu bar
        self.menu_bar.setNativeMenuBar(False)

        self.settings_menu.addAction("&Help ...")
        self.settings_menu.addAction("&Exit")

        self.select_port_menu.addAction(self.refresh_port)

        for i, p in enumerate(self.available_ports):
            self.list_port_action.append(self.select_port_menu.addAction(p))
            self.list_port_action[i].setCheckable(True)
            if p == self.port_name:
                self.list_port_action[i].setChecked(True)
                self.port_checked = self.list_port_action[i]

        for j, b in enumerate(serial.SerialBase.BAUDRATES):
            self.list_baudrate_action.append(self.select_baudrate_menu.addAction(str(b)))
            self.list_baudrate_action[j].setCheckable(True)
            if str(b) == self.baudrate:
                self.list_baudrate_action[j].setChecked(True)
                self.baudrate_checked = self.list_baudrate_action[j]

        self.port_config_menu.addMenu(self.select_port_menu)
        self.port_config_menu.addMenu(self.select_baudrate_menu)

        self.file_menu.addAction(self.file_action)

        self.menu_bar.addMenu(self.settings_menu)
        self.menu_bar.addMenu(self.port_config_menu)
        self.menu_bar.addMenu(self.file_menu)

        self.settings_menu.triggered[QtGui.QAction].connect(self.settings)
        self.port_config_menu.triggered[QtGui.QAction].connect(self.port_config_changed)
        self.file_menu.triggered[QtGui.QAction].connect(self.save_into_file)

        self.command_manager_action.setIcon(QtGui.QIcon('upload.png'))
        self.command_manager_action.setToolTip("Command manager")
        self.command_manager_action.triggered.connect(self.command_manager_window)
        self.toolbar.addAction(self.command_manager_action)

        self.pattern_manager_action.setIcon(QtGui.QIcon('loupe.jpg'))
        self.pattern_manager_action.setToolTip("Pattern manager")
        self.pattern_manager_action.triggered.connect(self.pattern_manager_window)
        self.toolbar.addAction(self.pattern_manager_action)

        self.command_historic_window.setWindowTitle("Command Manager Window")
        self.pattern_historic_window.setWindowTitle("Pattern Manager Window")

        self.command_historic_window_but.accepted.connect(self.save_command_window)
        self.command_historic_window_but.rejected.connect(self.cancel_command_window)
        self.command_historic_window_but.clicked.connect(self.send_command_window)

        self.pattern_historic_window_but.accepted.connect(self.save_pattern_window)
        self.pattern_historic_window_but.rejected.connect(self.cancel_pattern_window)

        self.command_historic_window_lay.addWidget(self.command_historic_window_edit)
        self.command_historic_window_lay.addWidget(self.command_historic_window_but)
        self.command_historic_window.setLayout(self.command_historic_window_lay)

        self.pattern_historic_window_lay.addWidget(self.pattern_historic_window_edit)
        self.pattern_historic_window_lay.addWidget(self.pattern_historic_window_but)
        self.pattern_historic_window.setLayout(self.pattern_historic_window_lay)

        self.edit_command.setToolTip("Enter command to send")
        self.but_send_command.setToolTip("Send command")
        self.edit_pattern.setToolTip("Enter pattern to detect")
        self.but_accept_pattern.setToolTip("Add pattern")


        # Add buttons to layer
        self.layout.addWidget(self.label_command, 0, 0, 1, 1)
        self.layout.addWidget(self.edit_command, 0, 1, 1, 1)
        self.layout.addWidget(self.but_send_command, 0, 2, 1, 1)
        self.layout.addWidget(self.label_pattern, 1, 0, 1, 1)
        self.layout.addWidget(self.edit_pattern, 1, 1, 1, 1)
        self.layout.addWidget(self.but_accept_pattern, 1, 2, 1, 1)
        self.layout.addWidget(self.label_console, 2, 0, 1, 1)
        self.layout.addWidget(self.zone_console, 3, 1, 1, 1)

        self.global_layout.addLayout(self.layout)

        self.setCentralWidget(self.global_widget)
        self.centralWidget().setLayout(self.global_layout)

        # Connect buttons to functions
        self.but_send_command.clicked.connect(lambda: self.worker.command_manager(self.edit_command.displayText()))
        self.but_accept_pattern.clicked.connect(self.add_pattern_from_but)

        self.status_bar_label.setText("Connected to " + self.port_name + " ; Baudrate " + str(self.baudrate))
        self.status_bar.addPermanentWidget(self.status_bar_label)

        self.thread_rx.start()

        app.aboutToQuit.connect(self.exit_app)

    def cancel_command_window(self):
        self.command_historic_window.hide()

    def cancel_pattern_window(self):
        self.pattern_historic_window.hide()

    def save_command_window(self):
        com = []
        commands = self.command_historic_window_edit.toPlainText()
        for p in commands.split('\n'):
            if p is "":
                pass
            else:
                com.append(p)
        self.worker.set_command(com)
        self.command_historic_window.hide()

    def save_pattern_window(self):
        pat = []
        patterns = self.pattern_historic_window_edit.toPlainText()
        for p in patterns.split('\n'):
            if p is "":
                pass
            else:
                pat.append(p)
        self.worker.set_pattern(pat)
        self.pattern_historic_window.hide()

    def command_manager_window(self):
        self.command_historic_window_edit.clear()
        command = self.worker.get_command()
        for com in command:
            self.command_historic_window_edit.append(com)
        self.command_historic_window.show()

    def pattern_manager_window(self):
        self.pattern_historic_window_edit.clear()
        pattern = self.worker.get_pattern()
        for com in pattern:
            self.pattern_historic_window_edit.append(com)
        self.pattern_historic_window.show()

    def send_command_window(self, but):
        if self.command_historic_window_but.standardButton(but) == QtGui.QDialogButtonBox.Apply:
            com = []
            commands = self.command_historic_window_edit.toPlainText()
            for p in commands.split('\n'):
                if p is "":
                    pass
                else:
                    com.append(p)
            self.worker.send_script(com)
            self.worker.del_command()
            self.command_historic_window.hide()

    def exit_app(self, event=None, *args):
        self.sig_stop_thread.emit()
        self.thread_rx.quit()
        self.thread_rx.wait()
        QtGui.QApplication.quit()

    def settings(self, action):
        if action.text() == "&Exit":
            self.exit_app()
        else:
            print("Help")

    def clean_command_area(self):
        self.edit_command.clear()

    def port_config_changed(self, action):
        if action.text() == "Refresh ...":
            self.list_port_action.clear()
            self.select_port_menu.clear()
            self.available_ports = find_available_ports()
            self.select_port_menu.addAction(self.refresh_port)
            for i, p in enumerate(self.available_ports):
                self.list_port_action.append(self.select_port_menu.addAction(p))
                self.list_port_action[i].setCheckable(True)
                if p == self.worker.get_port_name():
                    self.list_port_action[i].setChecked(True)
                    self.port_checked = self.list_port_action[i]
        else:
            if action.parentWidget() == self.select_port_menu:
                if self.worker.change_port(action.text()):
                    self.port_checked.setChecked(False)
                    self.port_checked = action
            if action.parentWidget() == self.select_baudrate_menu:
                if self.worker.change_baudrate(action.text()):
                    self.baudrate_checked.setChecked(False)
                    self.baudrate_checked = action
            self.status_bar_label.setText(
                "Connected to " + self.worker.get_port_name() + " ; Baudrate " + self.worker.get_baudrate())

    def save_into_file(self, action):
        name = QtGui.QFileDialog.getSaveFileName(caption='Save traces', filter='html')
        if name[0]:
            filename = os.path.splitext(name[0])[0]
            if filename:
                filename += '.html'
                text= self.zone_console.document()
                self.worker.save_traces(filename, str(text.toHtml()))

    def add_pattern_from_but(self):
        pattern = self.edit_pattern.displayText()
        self.worker.pattern_manager(pattern)
        self.edit_pattern.clear()

    def display_port(self, line, detected):
        if detected:
            self.zone_console.appendHtml(f"<b><span style='background-color: yellow;'>{line}<b>")
        else:
            self.zone_console.appendHtml(f"<span style='background-color: white;'>{line}")

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
    parser = argparse.ArgumentParser(description='ETSM Tool')
    parser.add_argument('-p', '--port', required=False, help='Specify port to open', default='/dev/ttyUSB0', type=str)
    args = parser.parse_args()

    app = QtGui.QApplication([])
    etsm = Etsm(port_name=args.port, baudrate=115200)
    #etsm = Port(port= port_name='/dev/ttyACM0', baudrate=115200, pattern=["0.030161"])
    #etsm.run()
    etsm.show()
    QtGui.QApplication.instance().exec_()
