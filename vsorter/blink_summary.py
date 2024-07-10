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
import os
import time

start_time = time.time()

import argparse
import logging
from pathlib import Path
import re

try:
    from ._version import __version__
except ImportError:
    __version__ = '0.0.0'

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__process_name__ = Path(__file__).name

logger = None


def parser_add_args(parser):
    """
    Set up command parser
    :param argparse.ArgumentParser parser:
    :return: None but parser object is updated
    """
    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version',
                        version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('infiles', type=Path, nargs='*', default=[Path('.')], help='Files, directories to scan')


file_pattern = re.compile('^.+_([a-zA-Z0-9]+)_.*mp4')


def get_camera(cameras, path):
    """
    check if file matche blink name, coun it if it does
    :param  dict cameras: dict of camera name: count
    :param Path path: file to check
    :return: None, cameras is updated
    """
    m = file_pattern.match(path.name)
    if m:
        camera = m.group(1)
        if camera in cameras.keys():
            cameras[camera] += 1
        else:
            cameras[camera] = 1


def main():
    global logger

    logging.basicConfig()
    logger = logging.getLogger(__process_name__)
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description=__doc__, prog=__process_name__,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_add_args(parser)
    args = parser.parse_args()
    verbosity = 0 if args.quiet else args.verbose

    if verbosity < 1:
        logger.setLevel(logging.CRITICAL)
    elif verbosity < 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    # debugging?
    logger.debug(f'{__process_name__} version: {__version__} called with arguments:')
    for k, v in args.__dict__.items():
        logger.debug('    {} = {}'.format(k, v))

    cameras = dict()
    file_or_dir: Path
    for file_or_dir in args.infiles:
        if file_or_dir.is_file():
            get_camera(cameras, file_or_dir)
        else:
            for (root, dirs, files) in os.walk(file_or_dir, topdown=True):
                for file in files:
                    get_camera(cameras, Path(file))
    total = 0
    maxlen = 0

    for k in cameras.keys():
        maxlen = max(maxlen, len(k))

    skeys = list(cameras.keys())
    skeys.sort()
    for camera in cameras.keys():
        count = cameras[camera]
        print(f'{camera:{maxlen}s}: {count}')
        total += count

    print(f'============\n{"Total":{maxlen}s}: {total}')


if __name__ == "__main__":

    main()
    if logger is None:
        logging.basicConfig()
        logger = logging.getLogger(__process_name__)
        logger.setLevel(logging.DEBUG)
    # report our run time
    logger.info(f'Elapsed time: {time.time() - start_time:.1f}s')
