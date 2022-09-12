# Copyright 2022 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice, this
# list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
#
# Neither the name of the NXP Semiconductors nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import argparse
import os
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import serial
from serial.tools import list_ports
import signal
import sys
import time


def find_available_ports():
    """
    Detect, parse and store all the ports detected/connected to the PC.
    :return: array containing all the ports
    """
    ports = []
    raw_ports = list(list_ports.comports())
    for p in raw_ports:
        ports.append(p[0])
    return ports


class Port(QtCore.QObject):
    """
    Class emulating the communication with a given port.
    """
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
        self._conditions = {}
        self.exit = False

        self.open_port()

    def run(self):
        """
        Collects every lines sent trought the port, check if the line matches
        with entered pattern and/or condition and send a event to displays the line.
        """
        while not self.exit:
            try:
                line = self._port.readline().decode("utf-8")
            except (serial.SerialException, TypeError) as e:
                pass
            if line != "":
                if self._pattern or self._conditions:
                    ret = self.detect(line)
                    self.sig_display_port.emit(line, ret)
                else:
                    self.sig_display_port.emit(line, 0)

    def stop(self):
        self.exit = True

    def detect(self, line):
        """
        Check if the line is matches with a pattern/condition and send
        the corresponding event.
        :param line: the line to process
        :return: True if the line matches with pattern/condition, else False.
        """
        res = False
        for pat in self._pattern:
            if pat in line:
                res = True
        for cond in self._conditions.values():
            if cond[0] in line:
                res = True
                if cond[2] == 'Event':
                    self.sig_pattern_detected.emit(cond[1])
                else:
                    self.send_command(cond[1])
        return res

    def open_port(self):
        """
        Open the port with specified name and baudrate.
        """
        try:
            self._port = serial.Serial(self._port_name, self._baudrate, timeout=1)
        except serial.SerialException:
            print("Can't open port " + self._port_name + ".")
            sys.exit()

    def close_port(self):
        self._port.close()

    def send_command(self, command):
        """
        Send the command to the current port.
        :param command: The command to send.
        """
        self._port.write((command+"\r").encode())

    def send_script(self, script, file=False):
        """
        Send a script or a set of command to the current port.
        Parse it and send each command.
        :param script: File or set of command to send.
        :param file: True if the script is a file to read, else False.
        """
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
        """
        Get the command entered by the user, if a script name is detected
        calls the function that handles script, else send the single command.
        :param text: The string entered by the user, can be a command, or a file/script.
        """
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
        """
        Add the pattern entered by the user to the existing pattern array.
        :param text: The new pattern to detect
        """
        if text:
            if text not in self._pattern:
                self._pattern.append(text)

    def change_baudrate(self, new_baudrate):
        """
        Update the baudrate of the current port.
        :param new_baudrate: Baudrate requested by the user.
        :return: 1 if new baudrate is updated, 0 if no update.
        """
        if new_baudrate != self._baudrate:
            self._baudrate = new_baudrate
            self._port.baudrate = self._baudrate
            return 1
        else:
            return 0

    def change_port(self, new_port_name):
        """
        Update the current port.
        :param new_port_name: New port name requested by the user.
        :return: 1 if new port is updated, 0 if no update.
        """
        if new_port_name != self._port_name:
            self._port_name = new_port_name
            self._port.port = self._port_name
            return 1
        else:
            return 0

    def save_traces(self, filename, traces):
        """
        Saves all the traces (within the console area ) of the current port in a file.
        :param filename: The file where to save the traces.
        :param traces: The traces to save.
        """
        with open(filename, 'w') as f:
            f.write(traces)

    def get_pattern(self):
        """
        Gets the patterns of the current port outside the class.
        :return: the patterns of the current port to detect.
        """
        return self._pattern

    def set_pattern(self, pattern):
        """
        Erases and updates the patterns to detect outside the class.
        :param pattern: The new patterns to detect.
        """
        self._pattern = pattern

    def add_pattern(self, pattern):
        """
        Adds a new pattern to detect outside the class.
        :param pattern: The pattern to add.
        """
        self._pattern.append(pattern)

    def del_pattern(self):
        """
        Deletes the patterns to detect.
        """
        self._pattern = []

    def get_command(self):
        """
        Gets the command to send of the current port outside the class.
        :return:
        """
        return self._command

    def set_command(self, command):
        """
        Erases and updates the commands to send outside the class.
        :param command: Commands to send.
        """
        self._command = command

    def add_command(self, command):
        """
        Adds a new command to send outside the class.
        :param command: The command to send.
        """
        self._command.append(command)

    def del_command(self):
        """
        Deletes all the commands to send.
        """
        self._command = []

    def get_port_name(self):
        """
        Gets the current port's name outside the class.
        :return: The name of the port.
        """
        return self._port_name

    def set_port_name(self, port_name):
        """
        Updates the name of the current port outside the class.
        :param port_name: The new name of the port.
        """
        self._port_name = port_name

    def get_port(self):
        """
        Gets the instance of the current port outside the class.
        :return: Port instance.
        """
        return self._port

    def get_baudrate(self):
        """
        Gets the baudrate of the current port outside the class.
        :return: Port baudrate.
        """
        return self._baudrate

    def add_condition(self, cond_id, pattern, action, type):
        """
        Adds new condition for the current port.
        :param cond_id: ID number of the condition.
        :param pattern: Pattern of the condition to detect.
        :param action: Name of the action to trigger.
        :param type: Type of the action to trigger, command or event.
        """
        self._conditions[cond_id] = [pattern, action, type]

    def get_condition(self):
        """
        Gets all the conditions for the current port outside the class.
        :return: Dict of all conditions.
        """
        return self._conditions

    def get_specific_condition(self, cond_id):
        """
        Gets a specific condition for the current port outside the class.
        :param cond_id: ID number of the condition.
        :return: Specific condition.
        """
        return self._conditions.get(cond_id)

    def del_condition(self):
        """
        Deletes all the conditions of the current port.
        """
        self._conditions = {}

    def del_specific_condition(self, cond_id):
        """
        Deletes a specific condition of the condition port.
        :param cond_id: ID number of the condition.
        """
        if cond_id in self._conditions:
            del self._conditions[cond_id]


class Conditions(QtWidgets.QHBoxLayout):
    """
    Class representing a condition.
    """
    sig_remove_condition = QtCore.pyqtSignal(int)
    sig_save_condition = QtCore.pyqtSignal(int, str, str, str)

    def __init__(self, num):
        super().__init__()
        self.condition_number = num
        self.pattern_edit = QtWidgets.QLineEdit()
        self.arrow_icon_label = QtWidgets.QLabel()
        self.arrow_icon = QtGui.QPixmap('right_arrow.png')
        self.action_edit = QtWidgets.QLineEdit()
        self.but_condition_type = QtWidgets.QPushButton("Type")
        self.but_condition_type_menu = QtWidgets.QMenu()
        self.but_condition_remove = QtWidgets.QPushButton("X")

        self.pattern_edit.setToolTip("Pattern ...")
        self.pattern_edit.setPlaceholderText("Pattern ...")
        self.resized_arrow_icon = self.arrow_icon.scaled(30, 30, QtCore.Qt.KeepAspectRatio)
        self.arrow_icon_label.setPixmap(self.resized_arrow_icon)
        self.action_edit.setToolTip("Command or event ...")
        self.action_edit.setPlaceholderText("Command or event ...")
        self.but_condition_type_menu.addAction("Command")
        self.but_condition_type_menu.addAction("Event")
        self.but_condition_type_menu.triggered[QtGui.QAction].connect(self.condition_type_selection)
        self.but_condition_type.setMenu(self.but_condition_type_menu)
        self.but_condition_type.setFixedSize(90, 25)
        self.but_condition_remove.setFixedSize(25, 25)
        self.but_condition_remove.clicked.connect(self.remove_condition)

        self.addWidget(self.pattern_edit)
        self.addWidget(self.arrow_icon_label)
        self.addWidget(self.action_edit)
        self.addWidget(self.but_condition_type)
        self.addWidget(self.but_condition_remove)

    def condition_type_selection(self, action):
        """
        Sets type of condition
        :param action: Type of action, event or command
        """
        self.but_condition_type.setText(action.text())

    def remove_condition(self):
        for i in reversed(range(self.count())):
            self.itemAt(i).widget().setParent(None)
        self.sig_remove_condition.emit(self.condition_number)

    def clear_data(self):
        """
        Clear condition data.
        """
        self.pattern_edit.clear()
        self.action_edit.clear()
        self.but_condition_type.setText("Type")

    def save_data(self):
        """
        Saves informations of a condition.
        """
        pattern = self.pattern_edit.displayText()
        action = self.action_edit.displayText()
        type = self.but_condition_type.text()
        if pattern != '' and action != '' and type != 'Type':
            self.sig_save_condition.emit(self.condition_number, pattern, action, type)
        else:
            self.clear_data()


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
        self.settings_menu = QtWidgets.QMenu("Settings")
        self.port_config_menu = QtWidgets.QMenu("Port Configurator")
        self.select_port_menu = QtWidgets.QMenu("&Port Selector")
        self.refresh_port = QtWidgets.QAction("Refresh ...")
        self.port_checked = None
        self.select_baudrate_menu = QtWidgets.QMenu("&Baudrate selector")
        self.baudrate_checked = None
        self.list_port_action = []
        self.list_baudrate_action = []
        self.file_menu = QtWidgets.QMenu("File")
        self.file_action = QtWidgets.QAction("&Save Traces as ...")
        self.toolbar = self.addToolBar("toolbar")
        self.command_manager_action = QtGui.QAction()
        self.pattern_manager_action = QtGui.QAction()
        self.conditions_manager_action = QtGui.QAction()
        self.command_historic_window = QtWidgets.QDialog()
        self.command_historic_window_lay = QtWidgets.QVBoxLayout()
        self.command_historic_window_edit = QtWidgets.QTextEdit()
        self.command_historic_window_but = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        self.pattern_historic_window = QtWidgets.QDialog()
        self.pattern_historic_window_lay = QtWidgets.QVBoxLayout()
        self.pattern_historic_window_edit = QtWidgets.QTextEdit()
        self.pattern_historic_window_but = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        self.conditions_window_init_cond = Conditions(1)
        self.conditions_window = QtWidgets.QDialog()
        self.conditions_window_toolbar = QtWidgets.QToolBar()
        self.list_conditions = {}
        self.list_conditions_number = 1
        self.conditions_window_toolbar_action_add = QtGui.QAction("Add")
        self.conditions_window_but = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        self.conditions_window_layout = QtWidgets.QVBoxLayout()
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

        self.pattern_manager_action.setIcon(QtGui.QIcon('glass.png'))
        self.pattern_manager_action.setToolTip("Pattern manager")
        self.pattern_manager_action.triggered.connect(self.pattern_manager_window)
        self.toolbar.addAction(self.pattern_manager_action)

        self.conditions_manager_action.setIcon(QtGui.QIcon('light.png'))
        self.conditions_manager_action.setToolTip("Conditions manager")
        self.conditions_manager_action.triggered.connect(self.conditions_manager_window)
        self.toolbar.addAction(self.conditions_manager_action)

        self.command_historic_window.setWindowTitle("Command Manager Window")
        self.pattern_historic_window.setWindowTitle("Pattern Manager Window")

        self.command_historic_window_but.accepted.connect(self.save_command_window)
        self.command_historic_window_but.rejected.connect(self.cancel_command_window)
        self.command_historic_window_but.clicked.connect(self.send_command_window)

        self.pattern_historic_window_but.accepted.connect(self.save_pattern_window)
        self.pattern_historic_window_but.rejected.connect(self.cancel_pattern_window)

        self.command_historic_window_edit.setPlaceholderText("Enter set of commands to send ....\nClick on :"
                                                             "\n'Apply' to send the commands,"
                                                             "\n'Cancel' to exit the command manager,"
                                                             "\n'Save' to save the set of commands without sending it.")
        self.command_historic_window_lay.addWidget(self.command_historic_window_edit)
        self.command_historic_window_lay.addWidget(self.command_historic_window_but)
        self.command_historic_window.setLayout(self.command_historic_window_lay)

        self.pattern_historic_window_edit.setPlaceholderText("Enter the different patterns to detect ...")
        self.pattern_historic_window_lay.addWidget(self.pattern_historic_window_edit)
        self.pattern_historic_window_lay.addWidget(self.pattern_historic_window_but)
        self.pattern_historic_window.setLayout(self.pattern_historic_window_lay)

        self.edit_command.setToolTip("Enter command to send")
        self.edit_command.setPlaceholderText("Enter command to send or script file (.sh or .txt) ...")
        self.but_send_command.setToolTip("Send command")
        self.edit_pattern.setToolTip("Enter pattern to detect")
        self.edit_pattern.setPlaceholderText("Enter pattern to detect ...")
        self.but_accept_pattern.setToolTip("Add pattern")

        self.conditions_window.setWindowTitle("Conditions Manager Window")
        self.list_conditions[1] = self.conditions_window_init_cond
        self.conditions_window_init_cond.sig_remove_condition.connect(self.remove_condition)
        self.conditions_window_init_cond.sig_save_condition.connect(self.save_condition)
        self.conditions_window_toolbar.addAction(self.conditions_window_toolbar_action_add)
        self.conditions_window_toolbar_action_add.triggered.connect(self.create_condition)

        self.conditions_window_toolbar.addWidget(self.conditions_window_but)
        self.conditions_window_but.accepted.connect(self.save_condition_window)
        self.conditions_window_but.rejected.connect(self.cancel_condition_window)

        self.conditions_window_layout.addWidget(self.conditions_window_toolbar)
        self.conditions_window_layout.addLayout(self.conditions_window_init_cond)

        self.conditions_window.setLayout(self.conditions_window_layout)

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
        """
        Hides command manager window.
        """
        self.command_historic_window.hide()

    def cancel_pattern_window(self):
        """
        Hides pattern manager window.
        """
        self.pattern_historic_window.hide()

    def cancel_condition_window(self):
        """
        Hides conditions manager window.
        """
        for key in self.list_conditions:
            if key not in self.worker.get_condition():
                self.list_conditions[key].clear_data()
        self.conditions_window.hide()

    def save_command_window(self):
        """
        Saves all the commands entered in the command window.
        """
        com = []
        commands = self.command_historic_window_edit.toPlainText()
        for p in commands.split('\n'):
            if p == "":
                pass
            else:
                com.append(p)
        self.worker.set_command(com)
        self.command_historic_window.hide()

    def save_pattern_window(self):
        """
        Saves all the patterns entered in the pattern window.
        """
        pat = []
        patterns = self.pattern_historic_window_edit.toPlainText()
        for p in patterns.split('\n'):
            if p == "":
                pass
            else:
                pat.append(p)
        self.worker.set_pattern(pat)
        self.pattern_historic_window.hide()

    def save_condition_window(self):
        """
        Saves all the conditions of the condition window.
        """
        for key in self.list_conditions:
            self.list_conditions[key].save_data()
        self.conditions_window.hide()

    def command_manager_window(self):
        """
        Opens and displays the saved commands in command window.
        """
        self.command_historic_window_edit.clear()
        command = self.worker.get_command()
        for com in command:
            self.command_historic_window_edit.append(com)
        self.command_historic_window.show()

    def pattern_manager_window(self):
        """
        Opens and displays the saved patterns in pattern window.
        """
        self.pattern_historic_window_edit.clear()
        pattern = self.worker.get_pattern()
        for com in pattern:
            self.pattern_historic_window_edit.append(com)
        self.pattern_historic_window.show()

    def conditions_manager_window(self):
        """
        Displays conditions manager window.
        """
        self.conditions_window.show()

    def create_condition(self):
        """
        Creates a new basic empty condition.
        """
        self.list_conditions_number += 1
        new_cond = Conditions(self.list_conditions_number)
        new_cond.sig_remove_condition.connect(self.remove_condition)
        new_cond.sig_save_condition.connect(self.save_condition)
        self.list_conditions[self.list_conditions_number] = new_cond
        self.conditions_window_layout.addLayout(self.list_conditions.get(self.list_conditions_number))

    def save_condition(self, condition_id, pattern, action, type):
        """
        Saves condition with user entries.
        :param condition_id: Automatically assigned ID condition
        :param pattern: Pattern to detect.
        :param action: Name of the action.
        :param type: Type of the action, command or event.
        """
        self.worker.add_condition(condition_id, pattern, action, type)

    def remove_condition(self, condition_id):
        """
        Removes a specific condition.
        :param condition_id: ID condition to remove
        """
        self.conditions_window_layout.removeItem(self.list_conditions.get(condition_id))
        del self.list_conditions[condition_id]
        self.worker.del_specific_condition(condition_id)
        self.conditions_window.adjustSize()

    def send_command_window(self, but):
        """
        Gathers all the commands from command window and send it to the port.
        """
        if self.command_historic_window_but.standardButton(but) == QtGui.QDialogButtonBox.Apply:
            com = []
            commands = self.command_historic_window_edit.toPlainText()
            for p in commands.split('\n'):
                if p == "":
                    pass
                else:
                    com.append(p)
            self.worker.send_script(com)
            self.worker.del_command()
            self.command_historic_window.hide()

    def exit_app(self, event=None, *args):
        """
        Stop the different threads and close the app.
        """
        self.sig_stop_thread.emit()
        self.thread_rx.quit()
        self.thread_rx.wait()
        QtWidgets.QApplication.quit()

    def settings(self, action):
        """
        Manages interactions with settings menu.
        :param action: Action requested by the user.
        """
        if action.text() == "&Exit":
            self.exit_app()
        else:
            print("Help")

    def clean_command_area(self):
        """
        Removes all the commands from the commands window.
        """
        self.edit_command.clear()

    def port_config_changed(self, action):
        """
        Manages changes related to port configuration, i.e refresh, change port, change baudrate.
        :param action: Action requested by the user.
        """
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
        """
        Opens dialog box and saves traces into correct html file.
        """
        name = QtGui.QFileDialog.getSaveFileName(caption='Save traces', filter='html')
        if name[0]:
            filename = os.path.splitext(name[0])[0]
            if filename:
                filename += '.html'
                text= self.zone_console.document()
                self.worker.save_traces(filename, str(text.toHtml()))

    def add_pattern_from_but(self):
        """
        Adds entered pattern for the current port.
        """
        pattern = self.edit_pattern.displayText()
        self.worker.pattern_manager(pattern)
        self.edit_pattern.clear()

    def display_port(self, line, detected):
        """
        Displays line in the console area and highlight it if detected from pattern.
        :param line: The line to displays
        :param detected: The line has been detected as a pattern or not.
        :return:
        """
        if detected:
            self.zone_console.appendHtml(f"<b><span style='background-color: yellow;'>{line}<b>")
        else:
            self.zone_console.appendHtml(f"<span style='background-color: white;'>{line}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ETSM Tool')
    parser.add_argument('-p', '--port', required=False, help='Specify port to open', default='/dev/ttyUSB0', type=str)
    args = parser.parse_args()

    app = QtWidgets.QApplication([])
    etsm = Etsm(port_name=args.port, baudrate=115200)
    etsm.show()
    QtWidgets.QApplication.instance().exec_()
