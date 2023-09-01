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
import datetime
import time
import webbrowser
from configparser import ConfigParser
from typing import Any

start_time = time.time()

import os
from ja_webutils.Page import Page
from ja_webutils.PageForm import PageForm, PageFormButton
from ja_webutils.PageItem import PageItemImage, PageItemRadioButton, PageItemHeader, PageItemLink, PageItemList, \
    PageItemBlanks, PageItemVideo, PageItemArray, PageItemString
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


def mkhtml(movieq, odirs, form, maximg, noout, speeds):
    """

    :param Queue movieq: tuple (<path to full movie>, <path
    :param list odirs: tuple (<menu option text>, <path to dir>)
    :param PageForm form: form used to select images
    :param  int maximg: add at most this many images
    :param bool noout: do not create dirs or add disposition
    :param Array(float) speeds: array of speed options

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

        img_lbl = f'{img_num:03d}'
        movie_id = f'movie_{img_lbl}'

        mstat = movie_path.stat()
        mtime = datetime.datetime.utcfromtimestamp(mstat.st_mtime)
        mtime_str = mtime.strftime('%x %X')
        pil = PageItemArray()
        pil.add(mtime_str)
        pil.add(PageItemBlanks(1))
        img_link = PageItemLink(f'file://{movie_path.absolute()}', f'{img_lbl}: {movie_path.name}', target='_blank')
        pil.add(img_link)
        pil.add(PageItemBlanks(2))
        for s in speeds:
            spd_str = f'{s:.2f}' if s < 1 else f'         {s:4.0f}'
            btn_name = f'btn_{img_num:03d}_{s:.2f}'
            btn = PageFormButton(name=btn_name, contents=f'Play {spd_str}X', type='button',)
            btn.add_event('onclick', f'movie_start(\'{movie_id}\', {spd_str});')
            pil.add(btn)
            pil.add(PageItemBlanks(1))

        reset_char = PageItemString('&#x23EE;', escape=False, class_name='char_btn')
        bkup_char = PageItemString('&#x21ba;', escape=False, class_name='char_btn')
        pause_char = PageItemString('&#23F8;', escape=False, class_name='char_btn')
        nbsp = PageItemString('&nbsp;', escape=False, class_name='char_btn')

        btn = PageFormButton(name='reset_btn', contents=reset_char, type='button', )
        btn.add_event('onclick', f'movie_fn(\'{movie_id}\', \'reset\');')
        pil.add(btn)

        btn = PageFormButton(name='bkup_btn', contents=bkup_char, type='button', )
        btn.add_event('onclick', f'movie_fn(\'{movie_id}\', \'backup\');')
        pil.add(btn)

        pil.add(PageItemBlanks(1))

        form.add_hidden(f'movie_path_{img_lbl}', str(movie_path.absolute()))
        movie = PageItemVideo(src=f'file://{movie_path.absolute()}', controls=True, height=550,
                              id=movie_id, class_name='movie')
        row.add(pil)
        row.add(movie)

        if not noout:
            disposition = PageItemRadioButton('Movie disposition', options, name=f'disposition_{img_lbl}',
                                              class_name='disposition')
            row.add(disposition)
        img_table.add_row(row)
    return img_table

def main():
    global logger
    page = Page()

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
    parser.add_argument('--indir', type=Path, default='.', help='Path to directory with movies(.avi, mp4, mov) files')
    parser.add_argument('--outdir', type=Path, help='Where to put html, default= same as indir')
    parser.add_argument('--config', type=Path, help='Vsorter configuration file default = ~/.vsorter.ini if'
                                                    'it exists else internam imovie config')
    parser.add_argument('--noout', action="store_true",
                        help='do not creat output dirs or add disposition radio buttons')
    parser.add_argument('--incfg', help='Select included config (default, imovie)')
    parser.add_argument('--max-img', type=int, help='How many videos on the page')
    parser.add_argument('--print-config', action="store_true", help='Print the included config to make it easy to edit')

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

    config_file = None
    try:
        if args.config:
            config_file = args.config
            config: ConfigParser = get_config(args.config)
        elif args.incfg:
            config_file = 'internal config: ' + args.incfg
            config: ConfigParser = get_def_config(args.incfg)
        else:
            default_config = Path().home() / '.vsorter.ini'

            if default_config.exists():
                config_file = default_config.absolute()
                config: ConfigParser = get_config(default_config)
            else:
                config_file = 'Default internl config'
                config: ConfigParser = get_def_config('vsorter')
    except TypeError as ex:
        logger.critical(f'Error reading configuration from {config_file}: {ex}')
        return

    if args.print_config:
        config.write(sys.stdout, space_around_delimiters=True)
        return

    if 'outdir' in config['vsorter'].keys():
        outdir = config['vsorter']['outdir']
    else:
        outdir = None
    if args.outdir:
        outdir = args.outdir
    elif outdir is None:
        outdir = indir
    outdir = Path(outdir)
    logger.info(f'Moving data to {outdir.absolute()}')

    ftype = 'mp4'
    files = list(indir.glob('*.mp4'))
    logger.info(f'{len(files)} movie files were found in {indir.absolute()}')
    gif_in_q = Queue()
    gif_out_q = Queue()

    maxfiles = args.max_img if args.max_img else int(config['vsorter']['imgperpage'])
    maxfiles = min(len(files), maxfiles)
    if ftype == 'mp4':
        for f in files:
            gif_out_q.put((f, f))
    else:
        for f in files:
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

    speed_def = config['vsorter']['speeds']
    if speed_def:
        speed_def = speed_def.split(',')
    speeds = list()
    for s in speed_def:
        speed = float(s)
        speeds.append(speed)

    form = PageForm(action='http://127.0.0.1:5000/')
    form.add_hidden('indir', str(indir.absolute()))
    form.add_hidden('basedir', str(outdir.absolute()))
    img_tbl = mkhtml(gif_out_q, odirs, form, maxfiles, args.noout, speeds)
    form.add(img_tbl)

    page.title = indir.name
    page.include_js_cdn('jquery')
    page.add_style('.disposition {font-size: 1.4em;}')
    page.add_headjs(
        """
        function movie_start(id, speed)
        {
            let movie = document.getElementById(id);

            isVideoPlaying = (movie.currentTime > 0 && !movie.paused && !movie.ended && movie.readyState > 2);

            if (!isVideoPlaying)
            {
                movie.currentTime = 0;
                movie.playbackRate = speed;
                movie.play();
            }
            else
            {
                movie.pause();
            }
        }
        function movie_fn(id, fname)
        {
            let movie = document.getElementById(id);
            switch (fname)
            {
                case 'reset':
                    movie.currentTime = 0;
                    break;
                case 'backup':
                    movie.currentTime -= 5;
                    break;
            }
        }
        """
    )
    page.add_style(
        """
        .char_btn {font-size: 2.0em;}
        """
    )
    heading = f'Overview of {indir.absolute()} {len(files)} images in dir max {maxfiles} per run'
    page.add(PageItemHeader(heading, 2))
    page.add_blanks(2)
    page.add(form)
    html = page.get_html()
    ofile = indir / 'index.html'
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

