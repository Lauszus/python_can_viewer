#!/usr/bin/python
# coding: utf-8
#
# Copyright (C) 2018 Kristian Sloth Lauszus. All rights reserved.
#
# Contact information
# -------------------
# Kristian Sloth Lauszus
# Web      :  http://www.lauszus.com
# e-mail   :  lauszus@gmail.com

import argparse
import can
import curses
import os
import six
import struct
import sys
from time import sleep

from curses.ascii import ESC as KEY_ESC, SP as KEY_SPACE
from typing import Dict, List, Tuple, Union

from . import __version__

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

# CANopen function codes, all the messages except the TPDOx and RPDOx message have a fixed length according to the
# specs,  so this is checked as well in order to varify that it is indeed a CANopen message
canopen_function_codes = {
    CANOPEN_NMT:        {2: 'NMT'},        # Network management (NMT) node control. The node id should not be added to this value
    CANOPEN_SYNC_EMCY:  {0: 'SYNC',        # Synchronization (SYNC) protocol. The node id should not be added to this value
                         8: 'EMCY'},       # Emergency (EMCY) protocol
    CANOPEN_TIME:       {6: 'TIME'},       # Time (TIME) protocol. The node id should not be added to this value
    CANOPEN_TPDO1:          'TPDO1',       # 1. Transmit Process Data Object (PDO)
    CANOPEN_RPDO1:          'RPDO1',       # 1. Receive Process Data Object (PDO)
    CANOPEN_TPDO2:          'TPDO2',       # 2. Transmit Process Data Object (PDO)
    CANOPEN_RPDO2:          'RPDO2',       # 2. Receive Process Data Object (PDO)
    CANOPEN_TPDO3:          'TPDO3',       # 3. Transmit Process Data Object (PDO)
    CANOPEN_RPDO3:          'RPDO3',       # 3. Receive Process Data Object (PDO)
    CANOPEN_TPDO4:          'TPDO4',       # 4. Transmit Process Data Object (PDO)
    CANOPEN_RPDO4:          'RPDO4',       # 4. Receive Process Data Object (PDO)
    CANOPEN_SDO_TX:     {8: 'SDO_TX'},     # Synchronization Object (SYNC) transmit
    CANOPEN_SDO_RX:     {8: 'SDO_RX'},     # Synchronization Object (SYNC) receive
    CANOPEN_HEARTBEAT:  {1: 'HEARTBEAT'},  # Network management (NMT) node monitoring
    CANOPEN_LSS_TX:     {8: 'LSS_TX'},     # Layer Setting Services (LSS) transmit
    CANOPEN_LSS_RX:     {8: 'LSS_RX'},     # Layer Setting Services (LSS) receive
}


class CanViewer:

    def __init__(self, stdscr, bus, data_structs, ignore_canopen, testing=False):
        self.stdscr = stdscr
        self.bus = bus
        self.data_structs = data_structs
        self.ignore_canopen = ignore_canopen

        # Initialise the ID dictionary, start timestamp, scroll and variable for pausing the viewer
        self.ids = {}
        self.start_time = None
        self.scroll = 0
        self.paused = False

        # Get the window dimensions - used for resizing the window
        self.y, self.x = self.stdscr.getmaxyx()

        # Do not wait for key inputs and disable the cursor
        self.stdscr.nodelay(True)
        curses.curs_set(0)

        if not testing:  # pragma: no cover
            self.run()

    def run(self):
        # Clear the terminal and draw the header
        self.draw_header()

        while 1:
            # Do not read the CAN-Bus when in paused mode
            if not self.paused:
                # Read the CAN-Bus and draw it in the terminal window
                msg = self.bus.recv(timeout=0)
                if msg is not None:
                    self.draw_can_bus_message(msg)

            # Read the terminal input
            key = self.stdscr.getch()

            # Stop program if the user presses ESC or 'q'
            if key == KEY_ESC or key == ord('q'):
                break

            # Clear by pressing 'c'
            elif key == ord('c'):
                self.ids = {}
                self.start_time = None
                self.scroll = 0
                self.draw_header()

            # Pause by pressing space
            elif key == KEY_SPACE:
                self.paused = not self.paused

            # Scroll by pressing up/down
            elif key == curses.KEY_UP:
                # Limit scrolling, so the user do not scroll passed the header
                if self.scroll > 0:
                    self.scroll -= 1
                    self.redraw_screen()
            elif key == curses.KEY_DOWN:
                # Limit scrolling, so the maximum scrolling position is one below the last line
                if self.scroll <= len(self.ids) - self.y + 1:
                    self.scroll += 1
                    self.redraw_screen()

            # Check if screen was resized
            resized = curses.is_term_resized(self.y, self.x)
            if resized is True:
                self.y, self.x = self.stdscr.getmaxyx()
                if hasattr(curses, 'resizeterm'):  # pragma: no cover
                    curses.resizeterm(self.y, self.x)
                self.redraw_screen()

        # Shutdown the CAN-Bus interface
        self.bus.shutdown()

    # Convert it into raw integer values and then pack the data
    @staticmethod
    def pack_data(cmd, cmd_to_struct, *args):  # type: (int, Dict, Union[*float, *int]) -> bytes
        if not cmd_to_struct or len(args) == 0:
            # If no arguments are given, then the message does not contain a data package
            return b''

        for key in cmd_to_struct.keys():
            if cmd == key if isinstance(key, int) else cmd in key:
                value = cmd_to_struct[key]
                if isinstance(value, tuple):
                    # The struct is given as the fist argument
                    struct_t = value[0]  # type: struct.Struct

                    # The conversion from SI-units to raw values are given in the rest of the tuple
                    fmt = struct_t.format
                    if isinstance(fmt, six.string_types):  # pragma: no cover
                        # Needed for Python 3.7
                        fmt = six.b(fmt)

                    # Make sure the endian is given as the first argument
                    assert six.byte2int(fmt) == ord('<') or six.byte2int(fmt) == ord('>')

                    # Disable rounding if the format is a float
                    data = []
                    for c, arg, val in zip(six.iterbytes(fmt[1:]), args, value[1:]):
                        if c == ord('f'):
                            data.append(arg * val)
                        else:
                            data.append(round(arg * val))
                else:
                    # No conversion from SI-units is needed
                    struct_t = value  # type: struct.Struct
                    data = args

                return struct_t.pack(*data)
        else:
            raise ValueError('Unknown command: 0x{:02X}'.format(cmd))

    # Unpack the data and then convert it into SI-units
    @staticmethod
    def unpack_data(cmd, cmd_to_struct, data):  # type: (int, Dict, bytes) -> List[Union[float, int]]
        if not cmd_to_struct or len(data) == 0:
            # These messages do not contain a data package
            return []

        for key in cmd_to_struct.keys():
            if cmd == key if isinstance(key, int) else cmd in key:
                value = cmd_to_struct[key]
                if isinstance(value, tuple):
                    # The struct is given as the fist argument
                    struct_t = value[0]  # type: struct.Struct

                    # The conversion from raw values to SI-units are given in the rest of the tuple
                    values = [d // val if isinstance(val, int) else float(d) / val
                              for d, val in zip(struct_t.unpack(data), value[1:])]
                else:
                    # No conversion from SI-units is needed
                    struct_t = value  # type: struct.Struct
                    values = list(struct_t.unpack(data))

                return values
        else:
            raise ValueError('Unknown command: 0x{:02X}'.format(cmd))

    @staticmethod
    def parse_canopen_message(msg):
        canopen_function_code_string, canopen_node_id_string = None, None

        if not msg.is_extended_id:
            canopen_function_code = msg.arbitration_id & CANOPEN_FUNCTION_CODE_MASK
            if canopen_function_code in canopen_function_codes:
                canopen_node_id = msg.arbitration_id & CANOPEN_NODE_ID_MASK

                # The SYNC and EMCY uses the same function code, so determine which message it is by checking both the
                # node ID and message length
                if canopen_function_code == 0x080:
                    # Check if the length is valid
                    if msg.dlc in canopen_function_codes[canopen_function_code]:
                        # Make sure the length and node ID combination is valid
                        if (msg.dlc == 0 and canopen_node_id == 0) or (msg.dlc == 8 and 1 <= canopen_node_id <= 127):
                            canopen_function_code_string = canopen_function_codes[canopen_function_code][msg.dlc]
                elif (canopen_function_code == 0x000 or canopen_function_code == 0x100) and \
                        (canopen_node_id != 0 or msg.dlc not in canopen_function_codes[canopen_function_code]):
                    # It is not a CANopen message, as the node ID is not added to these command
                    canopen_function_code_string = None
                else:
                    if isinstance(canopen_function_codes[canopen_function_code], dict):
                        # Make sure the message has the defined length
                        if msg.dlc in canopen_function_codes[canopen_function_code]:
                            canopen_function_code_string = canopen_function_codes[canopen_function_code][msg.dlc]
                    # These IDs do not have a fixed length
                    else:
                        # Make sure the node ID is valid
                        if 1 <= canopen_node_id <= 127:
                            canopen_function_code_string = canopen_function_codes[canopen_function_code]

                # Now determine set the node ID string
                if canopen_function_code_string:
                    if 1 <= canopen_node_id <= 127:  # Make sure the node ID is valid
                        canopen_node_id_string = '0x{0:02X}'.format(canopen_node_id)
                    elif canopen_function_code == 0x000:
                        # The NMT command sends the node ID as the second byte, except when it is 0,
                        # then the command is sent to all nodes
                        if msg.data[1] == 0:
                            canopen_node_id_string = 'ALL'
                        elif 1 <= msg.data[1] <= 127:
                            canopen_node_id_string = '0x{0:02X}'.format(msg.data[1])
                        else:
                            # It not a valid NMT command, as the node ID is not valid
                            canopen_function_code_string = None
            elif (msg.arbitration_id == 0x7E4 or msg.arbitration_id == 0x7E5) and \
                    msg.dlc in canopen_function_codes[msg.arbitration_id]:
                # Check if it is the LSS commands
                canopen_function_code_string = canopen_function_codes[msg.arbitration_id][msg.dlc]

        return canopen_function_code_string, canopen_node_id_string

    def draw_can_bus_message(self, msg, sorting=False):
        # Use the CAN-Bus ID as the key in the dict
        key = msg.arbitration_id

        # Sort the extended IDs at the bottom by setting the 32-bit high
        if msg.is_extended_id:
            key |= (1 << 32)

        new_id_added, length_changed = False, False
        if not sorting:
            # Check if it is a new message or if the length is not the same
            if key not in self.ids:
                new_id_added = True
                # Set the start time when the first message has been received
                if not self.start_time:
                    self.start_time = msg.timestamp
            elif msg.dlc != self.ids[key]['msg'].dlc:
                length_changed = True

            if new_id_added or length_changed:
                # Increment the index if it was just added, but keep it if the length just changed
                row = len(self.ids) + 1 if new_id_added else self.ids[key]['row']

                # It's a new message ID or the length has changed, so add it to the dict
                # The first index is the row index, the second is the frame counter,
                # the third is a copy of the CAN-Bus frame
                # and the forth index is the time since the previous message
                self.ids[key] = {'row': row, 'count': 0, 'msg': msg, 'dt': 0}
            else:
                # Calculate the time since the last message and save the timestamp
                self.ids[key]['dt'] = msg.timestamp - self.ids[key]['msg'].timestamp

                # Copy the CAN-Bus frame - this is used for sorting
                self.ids[key]['msg'] = msg

            # Increment frame counter
            self.ids[key]['count'] += 1

        # Sort frames based on the CAN-Bus ID if a new frame was added
        if new_id_added:
            self.draw_header()
            for i, key in enumerate(sorted(self.ids.keys())):
                # Set the new row index, but skip the header
                self.ids[key]['row'] = i + 1

                # Do a recursive call, so the frames are repositioned
                self.draw_can_bus_message(self.ids[key]['msg'], sorting=True)
        else:
            # Format the CAN-Bus ID as a hex value
            arbitration_id_string = '0x{0:0{1}X}'.format(msg.arbitration_id, 8 if msg.is_extended_id else 3)

            # Generate data string
            data_string = ''
            if msg.dlc > 0:
                data_string = ' '.join('{:02X}'.format(x) for x in msg.data)

            # Check if is a CANopen message
            if self.ignore_canopen:
                canopen_function_code_string, canopen_node_id_string = None, None
            else:
                canopen_function_code_string, canopen_node_id_string = self.parse_canopen_message(msg)

            # Now draw the CAN-Bus message on the terminal window
            self.draw_line(self.ids[key]['row'], 0, str(self.ids[key]['count']))
            self.draw_line(self.ids[key]['row'], 8, '{0:.6f}'.format(self.ids[key]['msg'].timestamp - self.start_time))
            self.draw_line(self.ids[key]['row'], 23, '{0:.6f}'.format(self.ids[key]['dt']))
            self.draw_line(self.ids[key]['row'], 35, arbitration_id_string)
            self.draw_line(self.ids[key]['row'], 47, str(msg.dlc))
            self.draw_line(self.ids[key]['row'], 52, data_string)
            if canopen_function_code_string:
                self.draw_line(self.ids[key]['row'], 77, canopen_function_code_string)
            if canopen_node_id_string:
                self.draw_line(self.ids[key]['row'], 88, canopen_node_id_string)

            if self.data_structs:
                try:
                    values_list = []
                    for x in self.unpack_data(msg.arbitration_id, self.data_structs, msg.data):
                        if isinstance(x, float):
                            values_list.append('{0:.6f}'.format(x))
                        else:
                            values_list.append(str(x))
                    values_string = ' '.join(values_list)
                    self.draw_line(self.ids[key]['row'], 97 - (20 if self.ignore_canopen else 0), values_string)
                except (ValueError, struct.error):
                    pass

        return self.ids[key]

    def draw_line(self, row, col, txt, *args):
        if row - self.scroll < 0:
            # Skip if we have scrolled passed the line
            return
        try:
            self.stdscr.addstr(row - self.scroll, col, txt, *args)
        except curses.error:
            # Ignore if we are trying to write outside the window
            # This happens if the terminal window is too small
            pass

    def draw_header(self):
        self.stdscr.clear()
        self.draw_line(0, 0, 'Count', curses.A_BOLD)
        self.draw_line(0, 8, 'Time', curses.A_BOLD)
        self.draw_line(0, 23, 'dt', curses.A_BOLD)
        self.draw_line(0, 35, 'ID', curses.A_BOLD)
        self.draw_line(0, 47, 'DLC', curses.A_BOLD)
        self.draw_line(0, 52, 'Data', curses.A_BOLD)
        if not self.ignore_canopen:
            self.draw_line(0, 77, 'Func code', curses.A_BOLD)
            self.draw_line(0, 88, 'Node ID', curses.A_BOLD)
        if self.data_structs:  # Only draw if the dictionary is not empty
            self.draw_line(0, 97 - (20 if self.ignore_canopen else 0), 'Parsed values', curses.A_BOLD)

    def redraw_screen(self):
        # Trigger a complete redraw
        self.draw_header()
        for key in self.ids.keys():
            self.draw_can_bus_message(self.ids[key]['msg'])


# noinspection PyUnresolvedReferences,PyProtectedMember,PyMethodMayBeStatic,PyUnusedLocal
class SmartFormatter(argparse.HelpFormatter):  # pragma: no cover

    def _get_default_metavar_for_optional(self, action):
        return action.dest.upper()

    def _format_usage(self, usage, actions, groups, prefix):
        # Use uppercase for "Usage:" text
        return argparse.HelpFormatter._format_usage(self, usage, actions, groups, 'Usage: ')

    def _format_args(self, action, default_metavar):
        if action.nargs != argparse.REMAINDER and action.nargs != argparse.ONE_OR_MORE:
            return argparse.HelpFormatter._format_args(self, action, default_metavar)

        # Use the metavar if "REMAINDER" or "ONE_OR_MORE" is set
        get_metavar = self._metavar_formatter(action, default_metavar)
        return '%s' % get_metavar(1)

    def _format_action_invocation(self, action):
        if not action.option_strings or action.nargs == 0:
            return argparse.HelpFormatter._format_action_invocation(self, action)

        # Modified so "-s ARGS, --long ARGS" is replaced with "-s, --long ARGS"
        else:
            parts = []
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            for i, option_string in enumerate(action.option_strings):
                if i == len(action.option_strings) - 1:
                    parts.append('%s %s' % (option_string, args_string))
                else:
                    parts.append('%s' % option_string)
            return ', '.join(parts)

    def _split_lines(self, text, width):
        # Allow to manually split the lines
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


def parse_args(args):
    # Python versions >= 3.5
    kwargs = {}
    if sys.version_info[0] * 10 + sys.version_info[1] >= 35:  # pragma: no cover
        kwargs = {'allow_abbrev': False}

    # Parse command line arguments
    parser = argparse.ArgumentParser('python -m python_can_viewer',
                                     description='A simple CAN viewer terminal application written in Python',
                                     formatter_class=SmartFormatter, add_help=False, **kwargs)

    optional = parser.add_argument_group('Optional arguments')

    optional.add_argument('-h', '--help', action='help', help='Show this help message and exit')

    optional.add_argument('--version', action='version', help="Show program's version number and exit",
                          version='%(prog)s (version {version})'.format(version=__version__))

    # Copied from: https://github.com/hardbyte/python-can/blob/develop/can/logger.py
    optional.add_argument('-b', '--bitrate', type=int, help='''Bitrate to use for the given CAN interface''')

    optional.add_argument('-c', '--channel', help='''Most backend interfaces require some sort of channel.
                          for example with the serial interface the channel might be a rfcomm device: "/dev/rfcomm0"
                          with the socketcan interfaces valid channel examples include: "can0", "vcan0".
                          (default: use default for the specified interface)''', default=None)
    
    optional.add_argument('-s', '--serial_number', help='''specify SN''', default=None)

    optional.add_argument('-d', '--decode', dest='decode',
                          help='''R|Specify how to convert the raw bytes into real values. \
                          \nThe ID of the frame is given as the first argument and the format as the second. \
                          \nThe Python struct package is used to unpack the received data \
                          \nwhere the format characters have the following meaning: \
                          \n      < = little-endian, > = big-endian \
                          \n      x = pad byte \
                          \n      c = char \
                          \n      ? = bool \
                          \n      b = int8_t, B = uint8_t \
                          \n      h = int16, H = uint16 \
                          \n      l = int32_t, L = uint32_t \
                          \n      q = int64_t, Q = uint64_t \
                          \n      f = float (32-bits), d = double (64-bits) \
                          \nFx to convert six bytes with ID 0x100 into uint8_t, uint16 and uint32_t: \
                          \n  $ python -m python_can_viewer -d "100:<BHL" \
                          \nNote that the IDs are always interpreted as hex values. \
                          \nAn optional conversion from integers to real units can be given \
                          \nas additional arguments. In order to convert from raw integer \
                          \nvalues the values are multiplied with the corresponding scaling value, \
                          \nsimilarly the values are divided by the scaling value in order \
                          \nto convert from real units to raw integer values. \
                          \nFx lets say the uint8_t needs no conversion, but the uint16 and the uint32_t \
                          \nneeds to be divided by 10 and 100 respectively: \
                          \n  $ python -m python_can_viewer -d "101:<BHL:1:10.0:100.0" \
                          \nBe aware that integer division is performed if the scaling value is an integer. \
                          \nMultiple arguments are separated by spaces: \
                          \n  $ python -m python_can_viewer -d "100:<BHL" "101:<BHL:1:10.0:100.0" \
                          \nAlternatively a file containing the conversion strings separated by new lines \
                          \ncan be given as input: \
                          \n  $ cat file.txt \
                          \n      100:<BHL \
                          \n      101:<BHL:1:10.0:100.0 \
                          \n  $ python -m python_can_viewer -d file.txt''',
                          metavar='{<id>:<format>,<id>:<format>:<scaling1>:...:<scalingN>,file.txt}',
                          nargs=argparse.ONE_OR_MORE, default='')

    optional.add_argument('-f', '--filter', help='''R|Comma separated CAN filters for the given CAN interface: \
                          \n      <can_id>:<can_mask> (matches when <received_can_id> & mask == can_id & mask) \
                          \n      <can_id>~<can_mask> (matches when <received_can_id> & mask != can_id & mask) \
                          \nFx to show only frames with ID 0x100 to 0x103: \
                          \n      python -m python_can_viewer -f 100:7FC \
                          \nNote that the ID and mask are alway interpreted as hex values''',
                          metavar='{<can_id>:<can_mask>,<can_id>~<can_mask>}', nargs=argparse.ONE_OR_MORE, default='')

    optional.add_argument('-i', '--interface', dest='interface',
                          help='''R|Specify the backend CAN interface to use. (default: "socketcan")''',
                          choices=sorted(can.VALID_INTERFACES), default='socketcan')

    optional.add_argument('--ignore-canopen', dest='ignore_canopen', help='''Do not print CANopen information''',
                          action='store_true')

    parsed_args = parser.parse_args(args)

    can_filters = []
    if len(parsed_args.filter) > 0:
        # print('Adding filter/s', parsed_args.filter)
        for flt in parsed_args.filter:
            # print(filter)
            if ':' in flt:
                _ = flt.split(':')
                can_id, can_mask = int(_[0], base=16), int(_[1], base=16)
            elif '~' in flt:
                can_id, can_mask = flt.split('~')
                can_id = int(can_id, base=16) | 0x20000000  # CAN_INV_FILTER
                can_mask = int(can_mask, base=16) & 0x20000000  # socket.CAN_ERR_FLAG
            else:
                raise argparse.ArgumentError(None, 'Invalid filter argument')
            can_filters.append({'can_id': can_id, 'can_mask': can_mask})

    # Dictionary used to convert between Python values and C structs represented as Python strings.
    # If the value is 'None' then the message does not contain any data package.
    #
    # The struct package is used to unpack the received data.
    # Note the data is assumed to be in little-endian byte order.
    # < = little-endian, > = big-endian
    # x = pad byte
    # c = char
    # ? = bool
    # b = int8_t, B = uint8_t
    # h = int16, H = uint16
    # l = int32_t, L = uint32_t
    # q = int64_t, Q = uint64_t
    # f = float (32-bits), d = double (64-bits)
    #
    # An optional conversion from real units to integers can be given as additional arguments.
    # In order to convert from raw integer value the real units are multiplied with the values and similarly the values
    # are divided by the value in order to convert from real units to raw integer values.
    data_structs = {}  # type: Dict[Union[int, Tuple[int, ...]], Union[struct.Struct, Tuple, None]]
    if len(parsed_args.decode) > 0:
        if os.path.isfile(parsed_args.decode[0]):
            with open(parsed_args.decode[0], 'r') as f:
                structs = f.readlines()
        else:
            structs = parsed_args.decode

        for s in structs:
            tmp = s.rstrip('\n').split(':')

            # The ID is given as a hex value, the format needs no conversion
            key, fmt = int(tmp[0], base=16), tmp[1]

            # The scaling
            scaling = []  # type: list
            for t in tmp[2:]:
                # First try to convert to int, if that fails, then convert to a float
                try:
                    scaling.append(int(t))
                except ValueError:
                    scaling.append(float(t))

            if scaling:
                data_structs[key] = (struct.Struct(fmt),) + tuple(scaling)
            else:
                data_structs[key] = struct.Struct(fmt)
            # print(data_structs[key])

    ignore_canopen = parsed_args.ignore_canopen

    return parsed_args, can_filters, data_structs, ignore_canopen


def main():  # pragma: no cover
    parsed_args, can_filters, data_structs, ignore_canopen = parse_args(sys.argv[1:])
    print(parsed_args)
    sleep(1)
    config = {}
    if can_filters:
        config['can_filters'] = can_filters
    if parsed_args.interface:
        config['interface'] = parsed_args.interface
    if parsed_args.bitrate:
        config['bitrate'] = parsed_args.bitrate
    if parsed_args.serial_number:
        config['UniqueHardwareId'] = parsed_args.serial_number

    # Create a CAN-Bus interface
    bus = can.interface.Bus(parsed_args.channel, **config)
    # print('Connected to {}: {}'.format(bus.__class__.__name__, bus.channel_info))

    curses.wrapper(CanViewer, bus, data_structs, ignore_canopen)


if __name__ == '__main__':  # pragma: no cover
    # Catch ctrl+c
    try:
        main()
    except KeyboardInterrupt:
        pass
