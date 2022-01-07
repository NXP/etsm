# NXP Event Trigger Software Module (ETSM)

## Introduction

ETSM is a python program providing serial communication interface through USB. The user-friendly GUI offers many features as pattern detection,
the possilibity to send command or set of commands.
The user can modify onlive different settings such as the serial port, the baudrate, the pattern to detect or the command to send.
Traces can be saved in a file for post processing, pattern detected will be highlighted in the file.

ETSM program works as a standalone program, and can be easily integrate in third party program without any modification.

**Note : For advanced features as triggering event on third party based on pattern detection, minor modifications on third party program must be done**

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

TBD