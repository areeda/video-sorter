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
import re
import subprocess

__author__ = 'joseph areeda'
__email__ = 'joseph.areeda@ligo.org'

from datetime import datetime

from pathlib import Path

import psutil

m2g_default_config = """
    [movie2gif]
        scale = .25
        tmpdir = None
        delay = 20
        loop = 0
        speedup = 5
"""

vsorter_default_config = """
    [vsorter]
        baseurl = http://127.0.0.1:8000
        outdir = ${indir}
        dirs = good, fair, other, furtherReview, trash
        imgperpage = 30
        height = 500
        nproc = 4
        speeds = 0.25, 0.5, 1, 1.5, 2, 3, 4 ,5
"""

vsorter_imovie_config = """
    [vsorter]
        baseurl = http://127.0.0.1:8000
        dirs = used, held, furtherReview, trash
        outdir = ${indir}
        imgperpage = 100
        height = 500
        nproc = 4
        speeds = 0.25, 0.5, 1, 1.5, 2, 3, 4 ,5
"""


def get_config(path):
    """
    Read a configuration file
    :param Path|str path:
    :return:
    """

    config = configparser.ConfigParser()
    config.read(path)
    return config


def get_def_config(prog: str) -> configparser.ConfigParser:
    """
    return a configparser object feom defaults
    :param str prog: which default (m2g, )
    :return ConfigParser: object created from internal values
    """
    config = configparser.ConfigParser()
    def_config = None
    if prog == 'm2g':
        def_config = m2g_default_config
    elif prog == 'vsorter':
        def_config = vsorter_default_config
    elif prog == 'imovie':
        def_config = vsorter_imovie_config

    if def_config:
        config.read_string(def_config)
    return config


def start_gunicorn():
    needs_start = True
    for p in psutil.process_iter():
        try:
            if 'python' in p.name():
                for cmd in p.cmdline():
                    if 'gunicorn' in cmd:
                        needs_start = False
                        break
        except psutil.Error:
            pass
    if needs_start:
        cmd = ['gunicorn', '--daemon', 'vsorter.vsorter_flask_app:app']
        subprocess.run(cmd)


blink_file_dt_pat = re.compile('(\\d\\d-\\d\\d-\\d\\d)T(\\d\\d-\\d\\d-\\d\\d)_.+mp4')


def get_movie_date(myinfile):
    """
    Figure out a date for this file preferable from its name
    :param Path|str myinfile: pat to the file
    :return  datetime.datetime: dae to se
    """
    file = Path(myinfile)
    match = blink_file_dt_pat.match(file.name)
    if match:
        ret = datetime.strptime(match.group(1), '%y-%m-%d')
    else:
        ret = datetime.fromtimestamp(file.stat(follow_symlinks=True).st_mtime)
    return ret


def get_outfile(infile, outdir=None, ndigits=2, ext=None):
    """
    get a unique output file name of the proper type, NB: not thread safe if multiple programs
    are working on the same file
    :param Path infile: path to an input file
    :param Path outdir: output directory or None to use infile's parent directory
    :param int ndigits: precision of version number
    :param str ext: new file type/extension, None -> use input extension
    :return Path: a path that does not exist to an output file
    """
    myinfile = Path(infile)
    myoutdir = outdir if outdir else infile.parent
    if ext is None:
        myext = myinfile.suffix
    else:
        myext = ext if ext.startswith('.') else '.' + ext

    n = 0
    movie_date = get_movie_date(myinfile)
    yyyymm = movie_date.strftime('%y-%m')

    outfile = myoutdir / f'{myinfile.with_suffix("").name}{myext}'
    v = re.sub('${yy-mm}', yyyymm, str(outfile), flags=re.IGNORECASE)
    outfile = Path(v)

    while outfile.exists():
        n += 1
        outfile = myoutdir / f'{myinfile.with_suffix("").name}-{n:0{ndigits}d}{myext}'

    return outfile
