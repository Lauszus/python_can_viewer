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

if __name__ == '__main__':  # pragma: no cover
    # Catch ctrl+c
    try:
        from .python_can_viewer import main
        main()
    except KeyboardInterrupt:
        pass
