#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: nu:ai:ts=4:sw=4

#
#  Copyright (C) 2023 Joseph Areeda <joseph.areeda@ligo.org>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
""""""
import configparser
from pathlib import Path
__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'

m2g_default_config = """
    [movie2gif]
        scale = .25
        tmpdir = None
        delay = 50
        loop = 0
        speedup = 5
"""

vsorter_default_config = """
    [vsorter]
            
"""

def get_config(path):
    """
    Read a configuration file
    :param Path|str path:
    :return:
    """
    config = configparser.ConfigParser()
    config.read_file(path)
    return config

def get_def_config(prog):
    """
    return a configparser object feom defaults
    :param str prog: which default (m2g, )
    :return ConfigParser: object created from internal values
    """
    config = configparser.ConfigParser()
    if prog == 'm2g':
        def_config = m2g_default_config
    config.read_string(def_config)
    return  config