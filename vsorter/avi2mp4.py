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
Convert a directory full of AVI movies to MP4 with audio amplification
"""
import os
import time
from multiprocessing import Queue

start_time = time.time()

import argparse
import logging
from pathlib import Path
import re
import subprocess
import sys

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__process_name__ = 'video-sorter'
__version__ = '0.0.0'

logger = None


def mkmp4(inq):
    """
    Convert to movie to mp4 maximizing volume
    :param Queue inq: input movie files
    :return:
    """
    volume_pat = re.compile('.*max_volume: -([\\d.]+) dB')
    while True:
        infile: Path|str = inq.get()
        if infile == 'DONE':
            break
        outfile = infile.parent / (os.path.splitext(infile.name)[0] + '.mp4')

        # get audio volume:
        cmd = ['ffmpeg', '-i', str(infile.absolute()), '-filter:a', 'volumedetect', '-f', 'null', '/dev/null']
        vres = subprocess.run(cmd, capture_output=True)
        if vres.returncode == 0:
            serr = vres.stderr.decode('utf-8')
            novolume = True
            for line in serr.splitlines():
                m = volume_pat.match(line)
                if m:
                    volume = float(m.group(1))
                    novolume = False
                    logger.info(f'{infile.name} input max volume = -{volume:.1f}')
                    cmd = ['ffmpeg', '-i', str(infile.absolute()), '-filter:a', f"volume={volume:.1f}dB",
                           str(outfile.absolute())]
                    cvtres = subprocess.run(cmd, capture_output=True)
                    if cvtres.returncode != 0:
                        logger.info(f'ffmpeg failed to convert {infile.name} to mp4')
            if novolume:
                logger.critical(f'Could not find volume for {infile.name}')
        else:
            logger.critical(f'ffmpg failed to fin volume for {infile.name}')


def main():
    global logger

    logging.basicConfig()
    logger = logging.getLogger(__process_name__)
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description=__doc__, prog=__process_name__,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version',
                        version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('--indir', type=Path, nargs='+', help='Input file or directory')

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

    indirs: list = args.indir
    files = list()

    indir: Path
    for indir in indirs:
        if indir.is_dir():
            files.extend(indir.glob('*AVI'))
            logger.info(f'{len(files)} found in {indir.absolute()}')
        elif indir.is_file() and indir.name.endswith('AVI'):
            files.append(indir)
            logger.info(f'added {indir.absolute()}')

    inq = Queue()
    for f in files:
        inq.put(f)

    inq.put('DONE')
    mkmp4(inq)


if __name__ == "__main__":

    main()
    if logger is None:
        logging.basicConfig()
        logger = logging.getLogger(__process_name__)
        logger.setLevel(logging.DEBUG)
    # report our run time
    logger.info(f'Elapsed time: {time.time() - start_time:.1f}s')
