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
import tempfile
import time

from vsorter.movie_utils import get_config, get_def_config

start_time = time.time()

import argparse
import logging
from pathlib import Path
import subprocess

import cv2
from ._version import __version__

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__process_name__ = 'video-sorter'

logger = None


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
    parser.add_argument('video', type=Path, help='video input file')
    parser.add_argument('out', type=Path, nargs='?', help='path to output, default is "<input file>-thumb.gif"')
    parser.add_argument('--tmpdir', type=Path, help='Location to store our intermediate files')
    parser.add_argument('--config', type=Path, help='Our .ini file')
    parser.add_argument('--delay', type=int, help='time between frames in thumbnail, overrides config')
    parser.add_argument('--scale', type=float,
                        help='Scale factor for movie to thumbnale 0< scale < 1, overrides config')
    parser.add_argument('--speedup', type=int, help='Number of frames to skip in movie to thumbnail, overrides config')

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

    if args.config:
        config = get_config(args.config)
    else:
        config = get_def_config('m2g')

    tmp_cleanup = False
    if args.tmpdir:
        tmpd = Path(args.tmpdir)
    elif str(config['movie2gif']['tmpdir']) != 'None':
        tmpd = Path(config['movie2gif']['tmpdir'])
    else:
        tmpfd = tempfile.TemporaryDirectory(prefix='movie2gif-')
        tmpd = Path(tmpfd.name)
        tmp_cleanup = True
    video = Path(args.video)
    if args.out:
        thumb_name = str(args.out)
    else:
        thumb_name = video.parent / (os.path.splitext(video.name)[0] + '-thumb.gif')

    scale = float(config['movie2gif']['scale'])
    delay = str(config['movie2gif']['delay'])
    loop = str(config['movie2gif']['loop'])
    speedup = int(config['movie2gif']['speedup'])

    logger.debug(f'Input: {video}, Output: {thumb_name}\nTemp dir: {tmpd}')
    logger.debug(f'Scale: {scale:.3f}, speedup {speedup}')
    logger.debug(f'Delay (10ms units): {delay}, loop: {loop}')

    # open the video and report attributes
    cap = cv2.VideoCapture(str(video))
    if cap.isOpened():
        nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        x = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        y = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        logger.info(f'{video.name} {nframes} {x}x{y} {fps}fps')

        ofnum = 1
        ofiles = list()
        # pull frames every 'speedup' factor save as intermediate images
        for fn in range(0, nframes, speedup):
            cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
            ret, frame = cap.read()
            ofrm2 = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
            ofname = tmpd / f'temp-{ofnum:02d}.jpg'
            ofnum += 1
            cv2.imwrite(str(ofname), ofrm2)
            ofiles.append(str(ofname))
        cap.release()

        # make an animated gif from intermediate frames
        cmd = ['magick', '-delay', delay, '-loop', loop]
        cmd.extend(ofiles)
        cmd.append(str(thumb_name))
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode == 0:
            logger.info(f'Animated gif written as {thumb_name}')
        else:
            logger.critical(f'Imagemagick failed to create gif. Return code" {res.returncode}\n'
                            f'stderr: {res.stderr.decode("utf-8")}')
        # remove intermediate files
        if tmp_cleanup:
            tmpfd.cleanup()
        else:
            for f in ofiles:
                Path(f).unlink(missing_ok=True)


if __name__ == "__main__":

    main()
    if logger is None:
        logging.basicConfig()
        logger = logging.getLogger(__process_name__)
        logger.setLevel(logging.DEBUG)
    # report our run time
    logger.info(f'Elapsed time: {time.time() - start_time:.1f}s')
