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
Convert a directory full of movies to MP4 with audio gain control
"""
import os
import time
from multiprocessing import Queue

from vsorter.movie_utils import get_outfile

start_time = time.time()

import argparse
import logging
from pathlib import Path
import re
import subprocess
from ._version import __version__

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__process_name__ = Path(__file__).name

logger = None


def mkmp4(inq, outdir=None, volume=None, noout=False):
    """
    Convert to movie to mp4 maximizing volume
    :param float volume: adjust audo gain to this level if lower
    :param Path outdir: alternate directoryq
    :param Queue inq: input movie files
    :return: None
    """
    volume_max_pat = re.compile('.*max_volume: -([\\d.]+) dB')
    volume_mean_pat = re.compile('.*mean_volume: -([\\d.]+) dB')
    while True:
        infile: Path | str = inq.get()
        if infile == 'DONE':
            break
        infile = Path(infile)
        outfile = get_outfile(infile, outdir, ext='mp4')
        if not outfile.parent.exists():
            outfile.parent.mkdir(0o755, parents=True)

        cmd = ['ffmpeg', '-i', str(infile.absolute()), ]

        if volume is not None:
            # get audio volume:
            cmd = ['ffmpeg', '-i', str(infile.absolute()), '-filter:a', 'volumedetect', '-f', 'null', '/dev/null']
            vres = subprocess.run(cmd, capture_output=True)
            if vres.returncode == 0:
                volume = list()
                serr = vres.stderr.decode('utf-8')
                for line in serr.splitlines():
                    m = volume_max_pat.match(line)
                    if m:
                        volume.append(float(m.group(1)))
                    else:
                        m = volume_mean_pat.match(line)
                        if m:
                            volume.append(float(m.group(1)))
                if len(volume) == 2:
                    logger.info(f'{infile.name} input volume mean: -{volume[0]:.1f} dB, max: -{volume[1]:.1f} dB')

                    if volume[1] >= 11:
                        vol_increase = volume[1] - 10
                        cmd.extend(['-filter:a', f"volume={vol_increase:.1f}dB"])
            else:
                logger.critical(f'ffmpg failed to find volume for {infile.name}')

        if not noout:
            cmd.append(str(outfile.absolute()))
            cvtres = subprocess.run(cmd, capture_output=True)
            if cvtres.returncode != 0:
                logger.info(f'ffmpeg failed to convert {infile.name} to mp4')
            else:
                if outfile.exists():
                    astat = infile.stat()
                    os.utime(outfile, (astat.st_atime, astat.st_mtime))


def parser_add_args(parser):
    """
    Set up the command parser
    :param argparse.ArgumentParser parser:
    :return: None but parser object is updated
    """
    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version', version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('indir', type=Path, nargs='*', default=[Path('.')], help='Input file or directory')
    parser.add_argument('--outdir', type=Path, help='Put new files in this directory, default is use input dir')
    parser.add_argument('--volume', type=float, default=-10.0, help='Adjust audio max gain to this dB')
    parser.add_argument('--novol', action='store_true', help='Disable auto volume control')
    parser.add_argument('--noout', action='store_true', help='Do not create output. Report volume mean and max')


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

    indirs: list = args.indir
    files = list()

    indir: Path
    for indir in indirs:
        if indir.is_dir():
            flist = indir.glob('*')
            for file in flist:
                spl = os.path.splitext(file)
                if spl[1].lower() in ['.avi', '.mov', '.mp4']:
                    files.append(file)
            logger.info(f'{len(files)} found in {indir.absolute()}')
        elif indir.is_file() and indir.suffix.lower() in ['.avi', '.mov', '.mp4']:
            files.append(indir)
            logger.info(f'added {indir.absolute()}')

    inq = Queue()
    for f in files:
        inq.put(f)

    inq.put('DONE')
    mkmp4(inq, args.outdir, args.volume, args.noout)


if __name__ == "__main__":
    main()
    if logger is None:
        logging.basicConfig()
        logger = logging.getLogger(__process_name__)
        logger.setLevel(logging.DEBUG)
    # report our run time
    logger.info(f'Elapsed time: {time.time() - start_time:.1f}s')
