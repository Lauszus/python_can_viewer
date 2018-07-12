import curses

from python_can_viewer import main

if __name__ == '__main__':  # pragma: no cover
    # Catch ctrl+c
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
