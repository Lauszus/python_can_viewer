# Python CAN Viewer

#### Developed by Kristian Lauszus, 2018

The code is released under the GNU General Public License.
_________
[![Build Status](https://travis-ci.com/Lauszus/python_can_viewer.svg?branch=master)](https://travis-ci.com/Lauszus/python_can_viewer)
[![codecov](https://codecov.io/gh/Lauszus/python_can_viewer/branch/master/graph/badge.svg)](https://codecov.io/gh/Lauszus/python_can_viewer)

A simple CAN viewer terminal application written in Python. Both Python 2 and Python 3 are supported.

## Usage

The project can be installed by first cloning the repository and then installing it via pip:

```bash
git clone https://github.com/Lauszus/python_can_viewer
pip install -e python_can_viewer
```

To run the script simply execute:

```bash
python -m python_can_viewer
```

By default it will be using the ```can0``` interface. The interface can be specified as the first argument, for instance to use ```can1```:

```bash
python -m python_can_viewer can1
```

A screenshot of the application can be seen below:

<img src="screenshot.png" width=400/>

The first column is the number of times a frame with the particular ID has been received, next is the timestamp of the frame relative to when the script was started. The third column is the time between the current frame relative to the previous one. Next is the length of the frame and then the data.

The last two columns are the decoded CANopen function code and node ID. If CANopen is not used, then they can simply be ignored.

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
