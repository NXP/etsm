# NXP Event Trigger Software Module (ETSM)

## Introduction

ETSM is a patented mechanism/concept from NXP. It consists of a serial communication through USB between a host PC and a device.
The ETSM receives the traces from the serial port and based on user inputs it can automatically
send backs a command/set of commands to the device, or external events to an external program.
Each received trace is compared with patterns to detect previously declared by the user.

ADD SCHEMATIC

To illustrate such a concept, NXP has developed a python based user-friendly GUI offering many features part of the ETSM mechanism.
The user can modify on live different settings such as the serial port, the baudrate, the patterns to detect, or the commands to send.
Traces can be saved in a file for post processing, patterns detected will be highlighted in the file.

This program works as a standalone program, and can be easily integrated in third party program without any modification.

**Note : For advanced features as triggering event on third party program based on pattern detection, minor modifications on third party program must be done**

## Installation

The following packages must be installed:
 - pyserial
 - pyqtgraph
 - PyQt5

The installation of the packages can be done by:
 - pip3 install -r requirements.txt

______________________________________________________________________________________________

## Run ETSM

To run ETSM, the user must specify the serial port to open.
For example, to use the ETSM with port ttyUSB2:

$ python3 etsm.py -p /dev/ttyUSB2

or

$ python3 etsm.py --port /dev/ttyUSB2

**Note : By default, the baudrate is set to 115200**

## Features

- Change serial port
- Change baudrate
- Detect and highlight patterns
- Modify patterns
- Send external events and/or command if pattern detected
- Send and modify commands (single command or set of commands via script .txt or .sh)
- Save traces as .html

_____________________________________________________________________________________

## License

BSD-3 Clause "New" or "Revised" License.