#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: nu:ai:ts=4:sw=4

#
#  Copyright (C) 2024 Joseph Areeda <joseph.areeda@ligo.org>
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
import shutil
import time
from typing import Any

start_time = time.time()

import argparse
import logging
from pathlib import Path
import sys
import traceback

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

    parser.add_argument('in_dir_files', type=Path, nargs='*',
                        help='Path to directory or files with movies(.avi, mp4, mov) files')
    parser.add_argument('--outdir', type=Path, help='Where to movies, default= same as indir')
    parser.add_argument('--config', type=Path, help='Vsorter configuration file default = ~/.vsorter.ini')


def move_files(day, movie_files, odir, delete_em=False):
    """

    :param str day: day label e.g. 24-06-06
    :param list[Path] movie_files: path to individual files
    :param Path odir: where to put files
    :param bool delete_em: true -> move else copy
    :return:
    """
    action = 'mv' if delete_em else 'cp'
    for movie in movie_files:
        parent_dir = odir / day[0:5] / day
        parent_dir.mkdir(0o775, parents=True, exist_ok=True)
        oname = f'{day}T{movie.name}'
        ofile = parent_dir / oname
        logger.debug(f'{action} {movie.absolute()} -> {ofile.absolute()}')
        if delete_em:
            shutil.move(movie, ofile)
        else:
            shutil.copy(movie, ofile)


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

    config_file: Path | Any = args.config if args.config else Path.home() / ".vsorter.ini"
    if not config_file.exists():
        logger.critical(f'Config file {config_file.absolute()} does not exit')
        exit(2)
    config = configparser.ConfigParser()
    config.read(config_file)

    inpat = Path(config['vsorter']['inpat'])
    indev = inpat.glob('*')
    indir = None

    dev: Path
    for dev in indev:
        if 'blink' in dev.name.lower():
            logger.debug(f'Blink thumb drive {dev}')
            indir = dev / 'blink_backup'
            if not indir.exists():
                logger.info('Possible thumb drive does not have "blink_backup" subdir')
                indir = None
            else:
                break
    if indir is None:
        logger.critical('No thumb drive found')
        exit(4)

    nfiles = 0
    nbytes = 0
    xfer_start = time.time()

    month_dirs = list(indir.glob('*'))
    for month in month_dirs:
        logger.debug(f'Month dir: {month.absolute()}')
        day_dirs = list(month.glob('*'))
        for day in day_dirs:
            movie_files = list(day.glob('*mp4'))
            logger.debug(f'There are {len(movie_files)} from {day.name}')
            for file in movie_files:
                nfiles += 1
                nbytes += Path(file).stat().st_size
            move_files(day.name, movie_files, Path(config['vsorter']['indir']), True)

    xfer_time = time.time() - xfer_start
    xfer_rate = nbytes / xfer_time / 1000
    logger.info(f'{nfiles} transferred in {xfer_time:.1f}s ({xfer_rate:.0f} KB/s')


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, OSError, NameError, ArithmeticError, RuntimeError) as ex:
        print(ex, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    if logger is None:
        logging.basicConfig()
        logger = logging.getLogger(__process_name__)
        logger.setLevel(logging.DEBUG)
    # report our run time
    logger.info(f'Elapsed time: {time.time() - start_time:.1f}s')
