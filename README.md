# Python CAN Viewer

#### Developed by Kristian Lauszus, 2018

The code is released under the GNU General Public License.
_________
[![PyPI](https://img.shields.io/pypi/v/python_can_viewer.svg)](https://pypi.org/project/Python-CAN-Viewer)
[![Build Status](https://travis-ci.com/Lauszus/python_can_viewer.svg?branch=master)](https://travis-ci.com/Lauszus/python_can_viewer)
[![Build status](https://ci.appveyor.com/api/projects/status/r4xl2v4aeh350fpd/branch/master?svg=true)](https://ci.appveyor.com/project/Lauszus/python-can-viewer/branch/master)
[![codecov](https://codecov.io/gh/Lauszus/python_can_viewer/branch/master/graph/badge.svg)](https://codecov.io/gh/Lauszus/python_can_viewer)

A simple CAN viewer terminal application written in Python. Python 2, Python 3, pypy and pypy3 are supported.

## Usage

The program can be installed via pip:

```bash
pip install python_can_viewer
```

To run the script simply execute:

```bash
python -m python_can_viewer
```

A screenshot of the application can be seen below:

<img src="https://github.com/Lauszus/python_can_viewer/raw/master/screenshot.png" width=400/>

The first column is the number of times a frame with the particular ID has been received, next is the timestamp of the frame relative to the first received message. The third column is the time between the current frame relative to the previous one. Next is the length of the frame and then the data.

The last two columns are the decoded CANopen function code and node ID. If CANopen is not used, then they can simply be ignored.

### Command line arguments

By default it will be using the ```socketcan``` interface. All interfaces supported by [python-can](https://github.com/hardbyte/python-can) are supported and can be specified using the ```-i``` argument.

The full usage page can be seen below:

```
Usage: python -m python_can_viewer [-h] [--version] [-b BITRATE] [-c CHANNEL]
                                   [-d {<id>:<format>,<id>:<format>:<scaling1>:...:<scalingN>,file.txt}]
                                   [-f {<can_id>:<can_mask>,<can_id>~<can_mask>}]
                                   [-i {iscan,ixxat,kvaser,neovi,nican,pcan,serial,slcan,socketcan,socketcan_ctypes,socketcan_native,usb2can,vector,virtual}]
                                   [--ignore-canopen]

A simple CAN viewer terminal application written in Python

Optional arguments:
  -h, --help            Show this help message and exit
  --version             Show program's version number and exit
  -b, --bitrate BITRATE
                        Bitrate to use for the given CAN interface
  -c, --channel CHANNEL
                        Most backend interfaces require some sort of channel.
                        for example with the serial interface the channel
                        might be a rfcomm device: "/dev/rfcomm0" with the
                        socketcan interfaces valid channel examples include:
                        "can0", "vcan0". (default: use default for the
                        specified interface)
  -d, --decode {<id>:<format>,<id>:<format>:<scaling1>:...:<scalingN>,file.txt}
                        Specify how to convert the raw bytes into real values.
                        The ID of the frame is given as the first argument and the format as the second.
                        The Python struct package is used to unpack the received data
                        where the format characters have the following meaning:
                              < = little-endian, > = big-endian
                              x = pad byte
                              c = char
                              ? = bool
                              b = int8_t, B = uint8_t
                              h = int16, H = uint16
                              l = int32_t, L = uint32_t
                              q = int64_t, Q = uint64_t
                              f = float (32-bits), d = double (64-bits)
                        Fx to convert six bytes with ID 0x100 into uint8_t, uint16 and uint32_t:
                          $ python -m python_can_viewer -d "100:<BHL"
                        Note that the IDs are always interpreted as hex values.
                        An optional conversion from integers to real units can be given
                        as additional arguments. In order to convert from raw integer
                        values the values are multiplied with the corresponding scaling value,
                        similarly the values are divided by the scaling value in order
                        to convert from real units to raw integer values.
                        Fx lets say the uint8_t needs no conversion, but the uint16 and the uint32_t
                        needs to be divided by 10 and 100 respectively:
                          $ python -m python_can_viewer -d "101:<BHL:1:10.0:100.0"
                        Be aware that integer division is performed if the scaling value is an integer.
                        Multiple arguments are separated by spaces:
                          $ python -m python_can_viewer -d "100:<BHL" "101:<BHL:1:10.0:100.0"
                        Alternatively a file containing the conversion strings separated by new lines
                        can be given as input:
                          $ cat file.txt
                              100:<BHL
                              101:<BHL:1:10.0:100.0
                          $ python -m python_can_viewer -d file.txt
  -f, --filter {<can_id>:<can_mask>,<can_id>~<can_mask>}
                        Comma separated CAN filters for the given CAN interface:
                              <can_id>:<can_mask> (matches when <received_can_id> & mask == can_id & mask)
                              <can_id>~<can_mask> (matches when <received_can_id> & mask != can_id & mask)
                        Fx to show only frames with ID 0x100 to 0x103:
                              python -m python_can_viewer -f 100:7FC
                        Note that the ID and mask are alway interpreted as hex values
  -i, --interface {iscan,ixxat,kvaser,neovi,nican,pcan,serial,slcan,socketcan,socketcan_ctypes,socketcan_native,usb2can,vector,virtual}
                        Specify the backend CAN interface to use. (default: "socketcan")
  --ignore-canopen      Do not print CANopen information
```

### Shortcuts

| Key      | Description             |
|:--------:|:-----------------------:|
| ESC/q    | Exit the viewer         |
| c        | Clear the stored frames |
| SPACE    | Pause the viewer        |
| UP/DOWN  | Scroll the viewer       |

### Misc

I would recommend the following board for testing on a Raspberry Pi: <http://skpang.co.uk/catalog/pican2-canbus-board-for-raspberry-pi-23-p-1475.html>.

The CAN interface can be setup like so:

```bash
sudo apt-get -y install can-utils
sudo raspi-config nonint do_spi 0
sudo sh -c 'echo "dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25" >> /boot/config.txt'
sudo sh -c 'echo "dtoverlay=spi0-hw-cs" >> /boot/config.txt'
```

For more information send me an email at <lauszus@gmail.com>.
