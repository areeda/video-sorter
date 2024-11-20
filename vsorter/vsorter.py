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

import cv2

start_time = time.time()

import os
from ja_webutils.Page import Page
from ja_webutils.PageForm import PageForm, PageFormButton
from ja_webutils.PageItem import PageItemRadioButton, PageItemHeader, PageItemLink, \
    PageItemBlanks, PageItemVideo, PageItemArray, PageItemString
from ja_webutils.PageTable import PageTable, PageTableRow, RowType

from vsorter.movie_utils import get_config, get_def_config, start_gunicorn

import argparse
import logging
from pathlib import Path
import re

from multiprocessing import Queue, current_process
from subprocess import run
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


def get_movie_info(movie_path):
    """
    Get anhtml table describing the movie file
    :param Path movie_path: moviee file to describe
    :return PageTable: description
    """
    ret = PageTable()
    cap = cv2.VideoCapture(str(movie_path))
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    duraton = cap.get(cv2.CAP_PROP_FRAME_COUNT) / frame_rate
    frame_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    ret.add_row(["FPS", f'{frame_rate:.1f}'])
    ret.add_row(["Duration", f'{duraton:.1f}'])
    ret.add_row(["Height", f'{frame_height:.0f}'])
    ret.add_row(["Width", f'{frame_width:.0f}'])
    return ret


def mkhtml(movieq, odirs, form, maximg, noout, speeds, total_files):
    """

    :param Queue movieq: tuple (<path to full movie>, <path
    :param list odirs: tuple (<menu option text>, <path to dir>)
    :param PageForm form: form used to select images
    :param  int maximg: add at most this many images
    :param bool noout: do not create dirs or add disposition
    :param Array(float) speeds: array of speed options
    :param int total_files: total number of movies in the directory list vs max on one pae

    :return PageTable:
    """
    blink_dir_pat = re.compile('(\\d\\d)-(\\d\\d)-(\\d\\d)')
    blink_file_pat = re.compile('(\\d\\d)-(\\d\\d)-(\\d\\d)_.+mp4')
    blink_file_dt_pat = re.compile('(\\d\\d-\\d\\d-\\d\\d)T(\\d\\d-\\d\\d-\\d\\d)_.+mp4')
    img_table = PageTable()
    hdr = ['ID', 'Disposition', 'Movie']
    hdr_row = PageTableRow(hdr, RowType.HEAD)
    img_table.add_row(hdr_row)
    img_num = 0
    options = list()
    options.append(('action_noact', 'No action', 'noaction'))

    for odir in odirs:
        options.append((f'action_{odir[0]}', odir[0], f'{odir[0]}'))
    while True:
        itm = movieq.get()
        if itm[0] == 'DONE':
            break
        img_num += 1
        if img_num > maximg:
            continue

        movie_path: Path = itm[0]

        img_lbl = f'{img_num:03d}'
        next_lbl = f'{img_num+1:03d}' if img_num < maximg else 'none'
        movie_id = f'movie_{img_lbl}'
        row_id = f'row_{img_lbl}'
        if next_lbl == 'none':
            next_row_id = next_lbl
            next_movie_id = next_lbl
        else:
            next_row_id = 'row_' + next_lbl
            next_movie_id = 'movie_' + next_lbl

        row = PageTableRow(id=row_id)

        mstat = movie_path.stat()
        mtime = datetime.datetime.utcfromtimestamp(mstat.st_mtime)
        mtime_str = mtime.strftime('%A %x %X')
        pil = PageItemArray()
        pil.add(PageItemString('File mtime:<br>', escape=False))
        pil.add(mtime_str)
        pil.add(PageItemBlanks(2))
        movie_parent = movie_path.parent.name
        movie_name = movie_path.name
        pmatch = blink_dir_pat.match(movie_parent)
        fmatch = blink_file_pat.match(movie_name)
        fmatch2 = blink_file_dt_pat.match(movie_name)
        blink_time = None
        if pmatch and fmatch:
            blink_time = datetime.datetime(2000 + int(pmatch.group(1)), int(pmatch.group(2)), int(pmatch.group(3)),
                                           int(fmatch.group(1)), int(fmatch.group(2)), int(fmatch.group(3)))
        elif fmatch2:
            blink_time = datetime.datetime.strptime(f'{fmatch2.group(1)} {fmatch2.group(2)}', '%y-%m-%d %H-%M-%S')
        if blink_time:
            bldt = f'Blink time:<br>{blink_time.strftime("%A %x %X")}<br><br>'
            pil.add(PageItemString(bldt, False))
        pil.add(PageItemString(f'{img_num} of {maximg}/{total_files}<br>', False))
        img_link = PageItemLink(f'file://{movie_path.absolute()}', f'{movie_path.name}', target='_blank')
        pil.add(img_link)
        pil.add(PageItemBlanks(2))
        info_tbl = get_movie_info(movie_path)
        pil.add(info_tbl)
        pil.add(PageItemBlanks(2))
        for s in speeds:
            spd_str = f'{s:.2f}'
            btn_name = f'btn_{img_num:03d}_{s:.2f}'
            btn = PageFormButton(name=btn_name, contents=f'Play {spd_str}X', type='button', class_name='char_btn')
            btn.add_event('onclick', f'movie_start(\'{movie_id}\', {spd_str});')
            pil.add(btn)
            pil.add(PageItemBlanks(1))
        pil.add(PageItemBlanks(1))

        reset_char = PageItemString('&#x23EE;', escape=False, class_name='char_btn')
        next_char = PageItemString('&#x23ED;', escape=False, class_name='char_btn')

        bkup_char = PageItemString('&#x21ba;', escape=False, class_name='char_btn')
        play_pause_char = PageItemString('&#x23EF;', escape=False, class_name='char_btn')
        play_char = PageItemString('&#x25b9;', escape=False, class_name='char_btn')
        # nbsp = PageItemString('&nbsp;', escape=False, class_name='char_btn')

        btn = PageFormButton(name='reset_btn', contents=reset_char, type='button', class_name='char_btn')
        btn.add_event('onclick', f'movie_fn(\'{movie_id}\', \'reset\');')
        pil.add(btn)

        btn = PageFormButton(name='bkup_btn', contents=bkup_char, type='button', class_name='char_btn')
        btn.add_event('onclick', f'movie_fn(\'{movie_id}\', \'backup\');')
        pil.add(btn)

        btn = PageFormButton(name='pause', contents=play_pause_char, type='button', class_name='char_btn')
        btn.add_event('onclick', f'movie_fn(\'{movie_id}\', \'play_pause\');')
        pil.add(btn)

        btn = PageFormButton(name='play', contents=play_char, type='button', class_name='char_btn')
        btn.add_event('onclick', f'movie_fn(\'{movie_id}\', \'play\');')
        pil.add(btn)

        if next_row_id != 'none':
            btn = PageFormButton(name='next', contents=next_char, type='button', class_name='char_btn')
            btn.add_event('onclick', f'pause_scroll(\'{movie_id}\', \'{next_row_id}\', \'{next_movie_id}\');')
            pil.add(btn)
        pil.add(PageItemBlanks(1))
        row.add(pil)

        if not noout:
            disposition = PageItemRadioButton('Movie disposition', options, name=f'disposition_{img_lbl}',
                                              class_name='disposition')
            disposition.add_event('onclick', f'pause_scroll(\'{movie_id}\', \'{next_row_id}\', \'{next_movie_id}\');')
            row.add(disposition)

        form.add_hidden(f'movie_path_{img_lbl}', str(movie_path.absolute()))
        movie = PageItemVideo(src=f'file://{movie_path.absolute()}', controls=True, height=800,
                              id=movie_id, class_name='movie')
        row.add(movie)

        img_table.add_row(row)
    return img_table


def get_indir_date(month_dir):
    """
    Determine the date of a blink dir from name or mtime
    :param Path month_dir: directory to analyze
    :return datetime.date or None:
    """
    ret = None
    m = re.match(r'.*(\d{2}-\d{2}-\d{2})', str(month_dir))
    if m:
        ret = datetime.datetime.strptime(m.group(1), '%y-%m-%d')
    else:
        m = re.match(r'.*(\d{2}-\d{2})', str(month_dir))
        if m:
            ret = datetime.datetime.strptime(m.group(1) + '-01', '%y-%m-%d')
    if ret is None:
        ret = datetime.datetime.fromtimestamp(month_dir.stat().st_mtime)

    return ret


def get_latest_daydir(month_dir):
    """
    Search through a month dir and find the latest day dir with movies left to sort
    :param Path month_dir: directory to search
    :return Path | None: latest day dir if available
    """
    day_dirs: list[Path] = list(month_dir.glob('*'))
    latest_day_dir: Path | None = None
    for day_dir in day_dirs:
        if day_dir.is_dir():
            if latest_day_dir is None or get_indir_date(day_dir) > get_indir_date(latest_day_dir):
                movies = list(day_dir.glob('*mp4'))
                if len(movies) > 0:
                    latest_day_dir = day_dir
    return latest_day_dir


def get_latest_indir(config):
    """
    Find the latest subdirectory in th configuration's indir
    :param ConfigParser config: our configuration object
    :return list[Path]: The latest subdirectory (just 1)
    """
    indir = Path(config['vsorter']['indir'])
    ret = None
    month_dirs: list[Path] = list(indir.glob('*'))
    month_dirs.sort(reverse=True)
    latest_day_dir: Path | None = None
    for month_dir in month_dirs:
        if month_dir.is_dir():
            day_dir = get_latest_daydir(month_dir)
            if day_dir is not None and \
                    (latest_day_dir is None or get_indir_date(day_dir) > get_indir_date(latest_day_dir)):
                latest_day_dir = day_dir

    ret = Path.cwd() if latest_day_dir is None else latest_day_dir
    return ret


def get_file_list(config, in_dir_files, ftype, match):
    """
    Build list of files to process from the files and directories specified on the command line
    :param ConfigParser config: program configuration for default input
    :param str match: regex to match file name
    :param list in_dir_files: the command line argument or a list of path-like objects
    :param str ftype: which type of files to use
    :return tuple: files (list of files to process), dirs (list of directories visited) indir0 (first dir seen)
    """

    files = list()
    direct_fcount = 0
    indirs = dict()
    indir0 = None       # first directory seen, used as default out directory
    infile_dir = 'None'
    inlist = in_dir_files
    matcher = re.compile(match, re.IGNORECASE) if match is not None else None
    if len(inlist) == 0:
        inlist = [get_latest_indir(config)]

    for idf in inlist:
        in_dir_file = Path(idf)
        if in_dir_file.is_dir():
            inlist.extend(list(in_dir_file.glob('*')))
            infile_dir = in_dir_file
        elif in_dir_file.is_file():
            infile = Path(in_dir_file)
            if infile.suffix == ftype and (matcher is None or matcher.match(infile.name)):
                files.append(infile)
                direct_fcount += 1
                infile_dir = infile.parent
            else:
                continue
        elif not in_dir_file.exists():
            logger.critical(f'{in_dir_file.absolute()} does not exist.')
            continue

        indirstr = str(infile_dir) if infile_dir.is_dir() else str(infile_dir.parent)

        if len(indirs) == 0:
            indir0 = indirstr
            indirs[indirstr] = 1
        else:
            indirs[indirstr] = 1 if indirstr not in indirs.keys() else indirs[indirstr] + 1

    return files, indirs, indir0


def parser_add_args(parser):
    """
    Set up the command parser
    :param argparse.ArgumentParser parser:
    :return: None but parser object is updated
    """
    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help='increase verbose output')
    parser.add_argument('-V', '--version', action='version',
                        version=__version__)
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='show only fatal errors')
    parser.add_argument('--nproc', type=int, help='number of parallel movie2gif jobs to run')
    parser.add_argument('in_dir_files', type=Path, nargs='*',
                        help='Path to directory or files with movies(.avi, mp4, mov) files')
    parser.add_argument('--outdir', type=Path, help='Where to put html, default= same as indir')
    parser.add_argument('--baseurl')
    parser.add_argument('--config', type=Path, help='Vsorter configuration file default = ~/.vsorter.ini if'
                                                    'it exists else internal "vsorter" config')
    parser.add_argument('--match', help='regex for selecting file names such as blink camera name')
    parser.add_argument('--noout', action="store_true",
                        help='do not creat output dirs or add disposition radio buttons')
    parser.add_argument('--incfg', help='Select included config (vsorter, imovie)')
    parser.add_argument('--max-img', type=int, help='How many videos on the page')
    parser.add_argument('--print-config', action="store_true",
                        help='Print the included config to make it easy to edit')
    parser.add_argument('--no-gunicorn-start', action='store_true',
                        help='Do not check if gunicorn is running and start if needed')
    parser.add_argument('--reverse', action='store_true', help='Reverse the order of files')
    parser.add_argument('--replace', action='store_true',
                        help='Overwrite destination. By default make new file if destination ecxists.')


def find_config(args, logger):
    """
    find specified configuration file and do any variable substitutions
    :param Namespace args: cli arguments
    :param logging.logger logger: ur logger
    :return ConfigParser: config to use
    """
    config_file = args.config
    try:
        incfg = args.incfg
        if config_file:
            config_file = Path(config_file)
            if config_file.exists():
                config: ConfigParser = get_config(config_file)
            else:
                raise FileNotFoundError(f'Config file {config_file.absolute()} does not exist')

        elif incfg:
            config_file = 'internal config: ' + incfg
            config: ConfigParser = get_def_config(incfg)
        else:
            default_config = Path().home() / '.vsorter.ini'

            if default_config.exists():
                config_file = default_config.absolute()
                config: ConfigParser = get_config(default_config)
            else:
                config_file = 'Default internal config'
                config: ConfigParser = get_def_config('vsorter')
    except TypeError as ex:
        raise Exception(f'Error reading configuration from {config_file}') from ex

    logger.debug(f'Using {config_file}')
    return config


def main():
    global logger
    page = Page()

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

    config = find_config(args, logger)

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
        outdir = '${indir}'

    ftype = '.mp4'
    maxfiles = args.max_img if args.max_img else int(config['vsorter']['imgperpage'])
    in_dir_files = args.in_dir_files

    match: str = args.match
    if match is None:
        match = '.*'
    else:
        if not match.startswith('^'):
            match = '^.*' + match
        if not match.endswith('$'):
            match += '.*$'
    files, indirs, indir0 = get_file_list(config, in_dir_files, ftype, match)
    total_files = len(files)

    logger.info(f'{len(files)} files found in {total_files} directory(s)')
    if len(files) == 0:
        return

    files.sort(reverse=args.reverse)
    if str(outdir) == '${indir}':
        outdir = indir0

    outdir = Path(outdir)
    if not args.noout:
        logger.info(f'Moving requested data to subdirectories of  {outdir.absolute()}')
    gif_out_q = Queue()

    maxfiles = min(len(files), maxfiles)
    if ftype == '.mp4':
        for f in files:
            gif_out_q.put((f, f))

    gif_out_q.put(('DONE', 'DONE'))
    dirdef = config['vsorter']['dirs']
    if dirdef:
        dirdef = dirdef.split(',')

    odirs = list()
    if not args.noout:
        for d in dirdef:
            dname = d.strip()
            outd = outdir / dname
            odirs.append((dname, outd))

    speed_def = config['vsorter']['speeds']
    if speed_def:
        speed_def = speed_def.split(',')
    speeds = list()
    for s in speed_def:
        speed = float(s)
        speeds.append(speed)

    baseurl = config['vsorter']['baseurl'] if config['vsorter']['baseurl'] else 'http://127.0.0.1:8000/'
    move_files_url = baseurl + '/move_files'
    form = PageForm(action=move_files_url, id='movie_form', nosubmit=True)
    indir = Path(indir0)
    form.add_hidden('indir', indir0)
    form.add_hidden('basedir', str(outdir.absolute()))
    form.add_hidden('replace', 'True' if args.replace else 'False')
    img_tbl = mkhtml(gif_out_q, odirs, form, maxfiles, args.noout, speeds, total_files)
    form.add(img_tbl)

    indir_txt = f'{Path(indir0).absolute().parent.name}/{Path(indir0).absolute().name}'
    page.title = indir_txt
    page.include_js_cdn('jquery')
    page.add_style('.disposition {font-size: 1.4em;}')
    page.add_style('[type="radio"] {height: 20px; width: 20px;}')
    page.add_headjs(
        """
        default_speed = 3;

        function movie_start(id, speed)
        {
            let movie = document.getElementById(id);

            isVideoPlaying = (movie.currentTime > 0 && !movie.paused && !movie.ended && movie.readyState > 2);

            if (!isVideoPlaying)
            {
                movie.currentTime = 0;
                movie.playbackRate = speed;
                default_speed = speed
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
                case 'pause':
                    movie.pause();
                    break;
                case 'play':
                    movie.play();
                    break;

                case 'play_pause':
                    isVideoPlaying = (movie.currentTime > 0 && !movie.paused && !movie.ended && movie.readyState > 2);
                    if (isVideoPlaying)
                    {
                        movie.pause();
                    }
                    else
                    {
                        movie.play();
                    }
                    break;
            }
        }

        function pause_scroll(movie_id, next_row_id, next_movie_id)
        {
            movie_fn(movie_id, 'pause')
            if (next_row_id != 'none')
            {
                let row_element = document.getElementById(next_row_id);
                row_element.scrollIntoView(true);

                movie_start(next_movie_id, default_speed)
            }
        }
        """
    )
    page.add_style(
        """
        .char_btn {font-size: 1.5em;}
        table, th, td {border: 1px solid; }
        table {border-collapse: collapse; }

        """
    )
    heading = f'Overview of {Path(indir0).absolute()} {total_files} images in {len(indirs)} ' \
              f'directories max {maxfiles} per run'
    page.add(PageItemHeader(heading, 2))
    heading2 = f'Output directories will be under {outdir.absolute()}'
    page.add(PageItemHeader(heading2, 2))

    in_files = min(total_files, maxfiles)
    form.add_hidden('in_files', f'{in_files}')
    form.add_hidden('total_files', f'{total_files}')
    page.add_blanks(2)
    page.add(PageItemString('<div id="container">\n', escape=False))
    submit_btn = PageFormButton('submit', 'Submit', class_name='char_btn')
    form.add(submit_btn)

    page.add(form)
    page.add_blanks(2)
    page.add(PageItemString('</div>\n', escape=False))

    html = page.get_html()
    ofile = indir / 'index.html'
    with ofile.open('w') as ofp:
        print(html, file=ofp)

    if not args.no_gunicorn_start:
        start_gunicorn()
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
