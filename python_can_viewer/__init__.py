#!/usr/bin/python
#
# Copyright (C) 2018 Kristian Sloth Lauszus. All rights reserved.
#
# Contact information
# -------------------
# Kristian Sloth Lauszus
# Web      :  http://www.lauszus.com
# e-mail   :  lauszus@gmail.com

__version__ = '0.1.0'

# CANopen function codes
CANOPEN_NMT = 0x000
CANOPEN_SYNC_EMCY = 0x080
CANOPEN_TIME = 0x100
CANOPEN_TPDO1 = 0x180
CANOPEN_RPDO1 = 0x200
CANOPEN_TPDO2 = 0x280
CANOPEN_RPDO2 = 0x300
CANOPEN_TPDO3 = 0x380
CANOPEN_RPDO3 = 0x400
CANOPEN_TPDO4 = 0x480
CANOPEN_RPDO4 = 0x500
CANOPEN_SDO_TX = 0x580
CANOPEN_SDO_RX = 0x600
CANOPEN_HEARTBEAT = 0x700
CANOPEN_LSS_TX = 0x7E4
CANOPEN_LSS_RX = 0x7E5

# Mask for extracting the CANopen function code
CANOPEN_FUNCTION_CODE_MASK = 0x780

# Mask for extracting the CANopen node ID
CANOPEN_NODE_ID_MASK = 0x07F

# Keycodes not defined in curses
KEY_ESC = 27
KEY_SPACE = 32

from .python_can_viewer import *
