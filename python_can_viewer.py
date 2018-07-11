#!/usr/bin/python
#
# Copyright (C) 2018 Kristian Sloth Lauszus. All rights reserved.
#
# Contact information
# -------------------
# Kristian Sloth Lauszus
# Web      :  http://www.lauszus.com
# e-mail   :  lauszus@gmail.com

import can
import curses
import math
from six import byte2int, binary_type
import struct
import sys
import time
from typing import Union, Dict, List

# Keycodes not defined in curses
KEY_ESC = 27
KEY_SPACE = 32

CANOPEN_NODE_ID_MASK = 0x07F  # Mask for extracting the CANopen node ID
CANOPEN_FUNCTION_CODE_MASK = 0x780  # Mask for extracting the CANopen function code

canopen_function_codes = {
    0x000: {2: 'NMT'},        # Network management (NMT) node control. The node id should not be added to this value
    0x080: {0: 'SYNC',        # Synchronization (SYNC) protocol. The node id should not be added to this value
            8: 'EMCY'},       # Emergency (EMCY) protocol
    0x100: {6: 'TIME'},       # Time (TIME) protocol. The node id should not be added to this value
    0x180: 'TPDO1',           # 1. Transmit Process Data Object (PDO)
    0x200: 'RPDO1',           # 1. Receive Process Data Object (PDO)
    0x280: 'TPDO2',           # 2. Transmit Process Data Object (PDO)
    0x300: 'RPDO2',           # 2. Receive Process Data Object (PDO)
    0x380: 'TPDO3',           # 3. Transmit Process Data Object (PDO)
    0x400: 'RPDO3',           # 3. Receive Process Data Object (PDO)
    0x480: 'TPDO4',           # 4. Transmit Process Data Object (PDO)
    0x500: 'RPDO4',           # 4. Receive Process Data Object (PDO)
    0x580: {8: 'SDO_TX'},     # Synchronization Object (SYNC) transmit
    0x600: {8: 'SDO_RX'},     # Synchronization Object (SYNC) receive
    0x700: {1: 'HEARTBEAT'},  # Network management (NMT) node monitoring
    0x7E4: {8: 'LSS_TX'},     # Layer Setting Services (LSS) transmit
    0x7E5: {8: 'LSS_RX'},     # Layer Setting Services (LSS) receive
}

# Initialize the scroll variable
scroll = 0


# Convert it into raw integer values and then pack the data
def _pack_data(cmd, cmd_to_struct, *args):  # type: (Union(bytes, int), Dict, *float) -> bytes
    if not cmd_to_struct or len(args) == 0:
        # If no arguments are given, then the message do not contain a data package
        return b''

    for key in cmd_to_struct.keys():
        if cmd == key if isinstance(key, int) else cmd in key:
            value = cmd_to_struct[key]
            if isinstance(value, tuple):
                # The struct is given as the fist argument
                struct_t = value[0]  # type: struct.Struct

                # The conversion from SI-units to raw values are given in the rest of the tuple
                fmt = struct_t.format

                # Make sure the endian is given as the first argument
                assert fmt[0] == ord(b'<') or fmt[0] == ord(b'>')

                # Disable rounding if the format is a float
                data = []
                for c, arg, val in zip(fmt[1:], args, value[1:]):
                    if c == ord(b'f'):
                        data.append(arg * val)
                    else:
                        data.append(round(arg * val))
            else:
                # No conversion from SI-units is needed
                struct_t = value  # type: struct.Struct
                data = args

            return struct_t.pack(*data)

    raise ValueError('Unknown command: 0x{:02X}'.format(byte2int(cmd) if isinstance(cmd, binary_type) else cmd))


# Unpack the data and then convert it into SI-units
def _unpack_data(cmd, cmd_to_struct, data):  # type: (Union(bytes, int), Dict, bytes) -> Union[List[float], bytes]
    if not cmd_to_struct or len(data) == 0:
        # These messages do not contain a data package
        return b''

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
                values = struct_t.unpack(data)

            if len(values) == 1:
                return values[0]  # Extract the value if there is only one element in the tuple
            return values

    raise ValueError('Unknown command: 0x{:02X}'.format(byte2int(cmd) if isinstance(cmd, binary_type) else cmd))


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
                    else:
                        canopen_node_id_string = '0x{0:02X}'.format(msg.data[1])
        elif (msg.arbitration_id == 0x7E4 or msg.arbitration_id == 0x7E5) and \
                msg.dlc in canopen_function_codes[msg.arbitration_id]:
            # Check if it is the LSS commands
            canopen_function_code_string = canopen_function_codes[msg.arbitration_id][msg.dlc]

    return canopen_function_code_string, canopen_node_id_string


def draw_can_bus_message(stdscr, ids, start_time, data_structs, msg, sorting=False):
    # Use the CAN-Bus ID as the key in the dict
    key = msg.arbitration_id

    # Sort the extended IDs at the bottom by setting the 32-bit high
    if msg.is_extended_id:
        key |= (1 << 32)

    # Check if it is a new message or if the length is not the same
    new_id_added, length_changed = False, False
    if key not in ids:
        new_id_added = True
    elif msg.dlc != ids[key][2].dlc:
        length_changed = True

    if not sorting:
        if new_id_added or length_changed:
            # Increment the index if it was just added, but keep it if the length just changed
            row = len(ids) + 1 if new_id_added else ids[key][0]

            # It's a new message ID or the length has changed, so add it to the dict
            # The first index is the row index, the second is the frame counter,
            # the third is a copy of the CAN-Bus frame
            # and the forth index is the time since the previous message
            ids[key] = [row, 0, msg, 0]
        else:
            # Calculate the time since the last message and save the timestamp
            ids[key][3] = msg.timestamp - ids[key][2].timestamp

            # Copy the CAN.Bus frame - this is used for sorting
            ids[key][2] = msg

        # Increment frame counter
        ids[key][1] += 1

    # Sort frames based on the CAN-Bus ID if a new frame was added
    if new_id_added:
        draw_header(stdscr, data_structs)
        for i, key in enumerate(sorted(ids.keys())):
            # Set the new row index, but skip the header
            ids[key][0] = i + 1

            # Do a recursive call, so the frames are repositioned
            draw_can_bus_message(stdscr, ids, start_time, data_structs, ids[key][2], sorting=True)
    else:
        # Format the CAN-Bus ID as a hex value
        arbitration_id_string = '0x{0:0{1}X}'.format(msg.arbitration_id, 8 if msg.is_extended_id else 3)

        # Generate data string
        data_string = ''
        if msg.dlc > 0:
            data_string = ' '.join('{:02X}'.format(x) for x in msg.data)

        # Check if is a CANopen message
        canopen_function_code_string, canopen_node_id_string = parse_canopen_message(msg)

        # Now draw the CAN-Bus message on the terminal window
        draw_line(stdscr, ids[key][0], 0, str(ids[key][1]))
        draw_line(stdscr, ids[key][0], 8, '{0:.6f}'.format(ids[key][2].timestamp - start_time))
        draw_line(stdscr, ids[key][0], 23, '{0:.6f}'.format(ids[key][3]))
        draw_line(stdscr, ids[key][0], 35, arbitration_id_string)
        draw_line(stdscr, ids[key][0], 47, str(msg.dlc))
        draw_line(stdscr, ids[key][0], 52, data_string)
        if canopen_function_code_string:
            draw_line(stdscr, ids[key][0], 77, canopen_function_code_string)
        if canopen_node_id_string:
            draw_line(stdscr, ids[key][0], 88, canopen_node_id_string)

        try:
            data = _unpack_data(msg.arbitration_id, data_structs, msg.data)
            draw_line(stdscr, ids[key][0], 97, ' '.join(str(x) for x in data))
        except (ValueError, struct.error, TypeError):
            pass

    return ids[key][0]


def draw_line(stdscr, row, col, txt, *args):  # pragma: no cover
    if not stdscr:
        return  # Used when testing

    global scroll

    if row - scroll < 0:
        # Skip if we have scrolled passed the line
        return
    try:
        stdscr.addstr(row - scroll, col, txt, *args)
    except curses.error:
        # Ignore if we are trying to write outside the window
        # This happens if the terminal window is too small
        pass


def draw_header(stdscr, data_structs):  # pragma: no cover
    if not stdscr:
        return  # Used when testing

    stdscr.clear()
    draw_line(stdscr, 0, 0, 'Count', curses.A_BOLD)
    draw_line(stdscr, 0, 8, 'Time', curses.A_BOLD)
    draw_line(stdscr, 0, 23, 'dt', curses.A_BOLD)
    draw_line(stdscr, 0, 35, 'ID', curses.A_BOLD)
    draw_line(stdscr, 0, 47, 'DLC', curses.A_BOLD)
    draw_line(stdscr, 0, 52, 'Data', curses.A_BOLD)
    draw_line(stdscr, 0, 77, 'Func code', curses.A_BOLD)
    draw_line(stdscr, 0, 88, 'Node ID', curses.A_BOLD)
    if data_structs:  # Only draw if the dictionary is not empty
        draw_line(stdscr, 0, 97, 'Parsed values', curses.A_BOLD)


def redraw_screen(stdscr, ids, start_time, data_structs):  # pragma: no cover
    # Trigger a complete redraw
    draw_header(stdscr, data_structs)
    for key in ids.keys():
        draw_can_bus_message(stdscr, ids, start_time, data_structs, ids[key][2])


def main(stdscr):  # pragma: no cover
    global scroll

    channel = 'can0'  # Use the first interface by default
    if len(sys.argv) > 1:
        channel = str(sys.argv[1])  # The CAN-Bus channel is given as an argument

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
    # An optional conversion from SI-units to integers can be given as additional arguments.
    # In order to convert from raw integer value the SI-units are multiplied with the values and similarly the values
    # are divided by the value in order to convert from SI-units to raw integer values.
    data_structs = {
    }  # type: Dict[Union[bytes, Tuple[bytes, ...]], Union[struct.Struct, Tuple, None]]

    # Create a CAN-Bus interface
    can_bus = can.interface.Bus(channel=channel, bustype='socketcan')

    # Do not wait for key inputs and disable the cursor
    stdscr.nodelay(True)
    curses.curs_set(0)

    # Get the window dimensions - used for resizing the window
    y, x = stdscr.getmaxyx()

    # Clear the terminal and draw the headers
    draw_header(stdscr, data_structs)

    # Used for pausing the viewer
    paused = False

    # Initialise the ID dictionary and the start timestamp
    ids = {}
    start_time = time.time()

    while 1:
        # Do not read the CAN-Bus when in paused mode
        if not paused:
            # Read the CAN-Bus and draw it in the terminal window
            msg = can_bus.recv(timeout=0)
            if msg is not None:
                draw_can_bus_message(stdscr, ids, start_time, data_structs, msg)

        # Read the terminal input
        key = stdscr.getch()

        # Stop program if the user presses ESC or 'q'
        if key == KEY_ESC or key == ord('q'):
            break

        # Clear by pressing 'c'
        elif key == ord('c'):
            ids = {}
            scroll = 0
            draw_header(stdscr, data_structs)

        # Pause by pressing space
        elif key == KEY_SPACE:
            paused = not paused

        # Scroll by pressing up/down
        elif key == curses.KEY_UP:
            # Limit scrolling, so the user can do scroll passed the header
            if scroll > 0:
                scroll -= 1
                redraw_screen(stdscr, ids, start_time, data_structs)
        elif key == curses.KEY_DOWN:
            # Limit scrolling, so the maximum scrolling position is one below the last line
            if scroll <= len(ids) - y + 1:
                scroll += 1
                redraw_screen(stdscr, ids, start_time, data_structs)

        # Check if screen was resized
        resize = curses.is_term_resized(y, x)
        if resize is True:
            y, x = stdscr.getmaxyx()
            curses.resizeterm(y, x)
            redraw_screen(stdscr, ids, start_time, data_structs)


if __name__ == '__main__':  # pragma: no cover
    # Catch ctrl+c
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
