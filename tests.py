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
import datetime
import struct
import sys
import time

from python_can_viewer import KEY_ESC, draw_can_bus_message


def _send_messages(can_bus):
    # NMT
    data = [2, 1]  # cmd = stop node, node ID = 1
    msg = can.Message(arbitration_id=0x000, data=data, extended_id=False)
    can_bus.send(msg)

    data = [1, 0]  # cmd = start node, node ID = all
    msg = can.Message(arbitration_id=0x000, data=data, extended_id=False)
    can_bus.send(msg)

    # SYNC
    msg = can.Message(arbitration_id=0x080, data=None, extended_id=False)
    can_bus.send(msg)

    # EMCY
    data = [1, 2, 3, 4, 5, 6, 7, 8]
    msg = can.Message(arbitration_id=0x080 + 1, data=data, extended_id=False)
    can_bus.send(msg)

    # TIME
    one_day_seconds = 24 * 60 * 60
    offset = datetime.datetime(year=1984, month=1, day=1)
    now = datetime.datetime.now()
    delta = (now - offset).total_seconds()
    days, seconds = divmod(delta, one_day_seconds)
    time_struct = struct.Struct('<LH')
    data = time_struct.pack(round(seconds * 1000), int(days))
    msg = can.Message(arbitration_id=0x100, data=data, extended_id=False)
    can_bus.send(msg)

    # milliseconds, days = time_struct.unpack(data)
    # seconds = days * one_day_seconds + milliseconds / 1000.
    # now_unpacked = datetime.datetime.utcfromtimestamp(
    #     seconds + (offset - datetime.datetime.utcfromtimestamp(0)).total_seconds())

    # TPDO1, RPDO1, TPDO2, RPDO2, TPDO3, RPDO3, TPDO4, RPDO4
    data = [1, 2, 3, 4, 5, 6, 7, 8]
    for i, func_code in enumerate([0x180, 0x200, 0x280, 0x300, 0x380, 0x400, 0x480, 0x500]):
        node_id = i + 1
        msg = can.Message(arbitration_id=func_code + node_id, data=data, extended_id=False)
        can_bus.send(msg)

    # SDO_TX
    data = [1, 2, 3, 4, 5, 6, 7, 8]
    msg = can.Message(arbitration_id=0x580 + 1, data=data, extended_id=False)
    can_bus.send(msg)

    # SDO_RX
    msg = can.Message(arbitration_id=0x600 + 1, data=data, extended_id=False)
    can_bus.send(msg)

    # HEARTBEAT
    data = [0x05]  # Operational
    msg = can.Message(arbitration_id=0x700 + 1, data=data, extended_id=False)
    can_bus.send(msg)

    # LSS_TX
    data = [1, 2, 3, 4, 5, 6, 7, 8]
    msg = can.Message(arbitration_id=0x7E4, data=data, extended_id=False)
    can_bus.send(msg)

    # LSS_RX
    msg = can.Message(arbitration_id=0x7E5, data=data, extended_id=False)
    can_bus.send(msg)

    # Send non-CANopen message
    msg = can.Message(arbitration_id=0x101, data=data, extended_id=False)
    can_bus.send(msg)

    # Send the same command, but with another data length
    data = [1, 2, 3, 4, 5, 6]
    msg = can.Message(arbitration_id=0x101, data=data, extended_id=False)
    can_bus.send(msg)

    # Message with extended id
    data = [1, 2, 3, 4, 5, 6, 7, 8]
    msg = can.Message(arbitration_id=0x123456, data=data, extended_id=True)
    can_bus.send(msg)

    # Send the same message again to make sure that resending works
    time.sleep(.1)
    can_bus.send(msg)


def main(stdscr):
    # Used to automatically break out after the messages has been sent
    wait_for_quit = True
    if len(sys.argv) > 1:
        wait_for_quit = sys.argv[1].lower() != 'false' and sys.argv[1] != '0'

    # Create a CAN-Bus interface
    can_bus = can.interface.Bus(channel='can0', bustype='virtual', receive_own_messages=True)

    # Do not wait for key inputs and disable the cursor
    stdscr.nodelay(True)
    curses.curs_set(0)

    # Initialise the ID dictionary and the start timestamp
    ids = {}
    start_time = time.time()

    # Send test messages
    _send_messages(can_bus)

    while 1:
        # Receive the messages we just sent
        msg = can_bus.recv(timeout=0)
        if msg is not None:
            draw_can_bus_message(stdscr, ids, start_time, msg)
        elif not wait_for_quit:
            # Automatically exit when we are finished reading
            break
        else:  # pragma: no cover
            # Read the terminal input
            key = stdscr.getch()

            # Stop program if the user presses ESC or 'q'
            if key == KEY_ESC or key == ord('q'):
                break


if __name__ == '__main__':  # pragma: no cover
    # Catch ctrl+c
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
