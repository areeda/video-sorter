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
import time
import webbrowser
from configparser import ConfigParser

start_time = time.time()

import os
from ja_webutils.Page import Page
from ja_webutils.PageForm import PageForm
from ja_webutils.PageItem import PageItemImage, PageItemRadioButton, PageItemHeader, PageItemLink
from ja_webutils.PageTable import PageTable, PageTableRow, RowType

from vsorter.movie_utils import get_config, get_def_config

import argparse
import logging
from pathlib import Path
import re

from multiprocessing import Process, Queue, current_process
from subprocess import  run
import sys
from ._version import __version__

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'
__process_name__ = 'vsorter'

global logger


def mkthumb(inq, outq):
    """
    Create thumbnail gifs from a movie
    :param Queue|str inq: filenames
    :param Queue outq: (movie, thumb)
    :return: None
    """
    while True:
        fpath: Path = inq.get()
        myname = current_process().name
        if fpath == 'DONE':
            break

        thumb_name = fpath.parent / (os.path.splitext(fpath.name)[0] + '-thumb.gif')
        if thumb_name.exists():
            outq.put((fpath, thumb_name))
        else:
            cmd = ['movie2gif', str(fpath), str(thumb_name)]
            print(f'{myname}: {" ".join(cmd)}')
            res = run(cmd, capture_output=True)
            if res.returncode != 0:
                print(f'Problem making thumb for {str(fpath)}, return code: {res.returncode}')
            else:
                outq.put((fpath, thumb_name))


def mkhtml(movieq, odirs, form, maximg, noout):
    """

    :param Queue movieq: tuple (<path to full movie>, <path
    :param list odirs: tuple (<menu option text>, <path to dir>)
    :param PageForm form: form used to select images
    :param  int maximg: add at most this many images
    :param bool noout: do not create dirs or add disposition

    :return PageTable:
    """
    img_table = PageTable()
    hdr = ['ID', 'Thumb', 'Disposition']
    hdr_row = PageTableRow(hdr,RowType.HEAD)
    img_table.add_row(hdr_row)
    img_num = 0
    options = list()
    options.append((f'action_noact', 'No action', f'noaction'))
    need_basedir = True

    for odir in odirs:
        options.append((f'action_{odir[0]}', odir[0], f'{odir[0]}'))
    while True:
        itm = movieq.get()
        if itm[0] == 'DONE':
            break
        img_num += 1
        if img_num > maximg:
            continue

        row = PageTableRow()
        thumb_path:Path = itm[1]
        movie_path:Path = itm[0]
        if need_basedir:
            form.add_hidden('basedir', str(thumb_path.parent.absolute()))
        img_lbl = f'{img_num:03d}'
        img_link = PageItemLink(f'file://{movie_path.absolute()}', f'{img_lbl}: {movie_path.name}', target='_blank')
        row.add(img_link)
        thumb_id = f'thumb_{img_lbl}'
        form.add_hidden(f'thumb_path_{img_lbl}', str(thumb_path.absolute()))
        form.add_hidden(f'movie_path_{img_lbl}', str(movie_path.absolute()))

        thumb = PageItemImage(url=thumb_path.name, alt_text=thumb_id, id=thumb_id,
                              name=thumb_id, class_name='thumb')
        row.add(thumb)

        if not noout:
            disposition = PageItemRadioButton('Movie disposition', options, name=f'disposition_{img_lbl}')
            row.add(disposition)
        img_table.add_row(row)
    return img_table

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
    parser.add_argument('--nproc', type=int, help='number of parallel movie2gif jobs to run')
    parser.add_argument('--indir', type=Path, default='.', help='Path to directory with movies(.avi, ,p4, mov) files')
    parser.add_argument('--outdir', type=Path, help='Where to put html, default= same as indir')
    parser.add_argument('--config', type=Path, help='Vsorter configuration file')
    parser.add_argument('--noout', action="store_true", help='do not creat output dirs or add dispsition radio buttons')

    m2g_opts = parser.add_argument_group(title="movie2gif", description="option for making thumbnails")
    m2g_opts.add_argument('--delay', type=int, help='time between frames in thumbnail, overrides config')
    m2g_opts.add_argument('--scale', type=float,
                        help='Scale factor for movie to thumbnale 0< scale < 1, overrides config')
    m2g_opts.add_argument('--speedup', type=int, help='Number of frames to skip in movie to thumbnail, overrides config')

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

    indir: Path = args.indir
    outdir = args.outdir if args.outdir else indir

    if args.config:
        config: ConfigParser = get_config(args.config)
    else:
        config: ConfigParser = get_def_config('vsorter')

    files = list(indir.glob('*.mp4'))
    logger.info(f'{len(files)} movie files were found in {indir.absolute()}')
    gif_in_q = Queue()
    gif_out_q = Queue()

    maxfiles = min(len(files), int(config['vsorter']['imgperpage']))
    for f  in files:
        gif_in_q.put(f)

    processes = list()
    if args.nproc:
        nproc: int = args.nproc
    elif 'nproc' in config['vsorter'].keys():
        nproc = int(config['vsorter']['nproc'])
    else:
        nproc = 1

    if nproc > 1:
        for i in range(0, nproc):
            g2m = Process(target=mkthumb, args=(gif_in_q, gif_out_q), name=f'thumb-{i + 1}')
            g2m.daemon = True
            g2m.start()
            processes.append(g2m)
            gif_in_q.put('DONE')
    else:
        gif_in_q.put('DONE')
        mkthumb(gif_in_q, gif_out_q)

    for p in processes:
        p.join()

    gif_out_q.put(('DONE', 'DONE'))
    dirdef = config['vsorter']['dirs']
    if dirdef:
        dirdef = dirdef.split(',')

    odirs = list()
    if not args.noout:
        for d in dirdef:
            dname = d.strip()
            outd = outdir / dname
            outd.mkdir(0o755, parents=True, exist_ok=True)
            odirs.append((dname, outd))

    form = PageForm(action='http://127.0.0.1:5000/')
    img_tbl = mkhtml(gif_out_q, odirs, form, maxfiles, args.noout)
    form.add(img_tbl)

    page = Page()
    heading = f'Overview of {indir.absolute()} {len(files)} images in dir max {maxfiles} per run'
    page.add(PageItemHeader(heading, 2))
    page.add_blanks(2)
    page.add(form)
    html = page.get_html()
    ofile = outdir / 'index.html'
    with ofile.open('w') as ofp:
        print(html, file=ofp)

    logger.info(f'wrote {ofile.absolute()}')
    webbrowser.open_new_tab(f'file://{ofile.absolute()}')

if __name__ == "__main__":
    main()

    if logger is None:
        logging.basicConfig()
        logger = logging.getLogger(__process_name__)
        logger.setLevel(logging.DEBUG)

    # report our run time
    logger.info(f'Elapsed time: {time.time() - start_time:.1f}s')

