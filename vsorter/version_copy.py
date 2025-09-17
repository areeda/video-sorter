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

"""
Copy files but do not overwrite. If output exists add a version number keeping suffix.
For example: abc.mp4 would copy to abc-001.mp4 if need be.
"""
import shutil
import time

from vsorter.movie_utils import get_outfile

start_time = time.time()

import argparse
import logging
from pathlib import Path

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
    Set up comand parser
    :param argparse.ArgumentParser parser:
    :return: None but parser object is updated
    """
    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version',
                        version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('--ndigit', type=int, default=2, help='Number of digits in version string')
    parser.add_argument('infiles', type=Path, nargs='+', help='Input files or directories')
    parser.add_argument('outdir', type=Path, nargs=1, help='Output directory or fle if only one input')


def do_cp(infile, outfile):
    """
    copy the input file to the output file
    :param Path infile: source
    :param Path outfile: destination
    :return: None
    """
    logger.info(f'{infile.name} -> {outfile.absolute()}')
    if infile.exists():
        shutil.copy(infile, outfile)
    else:
        logger.critical(f'Input file: {infile.absolute()} does not exist.')


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

    outdir: Path = args.outdir[0]
    infiles: list[Path] = args.infiles

    if outdir.is_file():
        if len(infiles) == 1:
            do_cp(infiles[0], outdir)
        else:
            logger.critical(f'Cannot copy {len(infiles)} files to a single destination file')
            return

    for file in infiles:
        if file.is_file():
            outfile = get_outfile(file, outdir)
            do_cp(file, outfile)
        else:
            logger.critical('Copying a directory has not been implemented, yet.')


if __name__ == "__main__":

    main()
    if logger is None:
        logging.basicConfig()
        logger = logging.getLogger(__process_name__)
        logger.setLevel(logging.DEBUG)
    # report our run time
    logger.info(f'Elapsed time: {time.time() - start_time:.1f}s')
