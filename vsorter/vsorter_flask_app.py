import re
import shutil
from pathlib import Path

from flask import Flask, request
from ja_webutils.Page import Page
from ja_webutils.PageItem import PageItemHeader, PageItemLink
from ja_webutils.PageTable import PageTable, PageTableRow, RowType

from vsorter.movie_utils import get_outfile, get_movie_date

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def home():
    try:
        page = Page()
        set_uri = PageItemLink('/settings', 'settings')
        page.add(set_uri)
        html = page.get_html()
    except Exception as ex:
        html = f'Error {ex}'
    return html


@app.route('/move_files', methods=['GET', 'POST'])
def process_vsort():  # put application's code here
    keys = request.form.keys()
    disp_pat = re.compile("disposition_(\\d+)")
    my_page = Page()
    basedir = request.form.get('basedir')
    basedir = Path(basedir) if basedir else None
    replace = request.form.get('replace') == 'True'
    in_files = request.form.get('in_files')
    total_files = request.form.get('total_files')
    table = PageTable()
    table.sorted = True
    table.sorted = True
    hdr = ['Disposition', 'Source', 'Destination']
    hdr_row = PageTableRow(hdr, RowType.HEAD)
    table.add_row(hdr_row)
    what_we_did = PageTable()
    counts = dict()

    for key in keys:
        m = disp_pat.match(key)
        if m:
            row = PageTableRow()
            img_num = m.group(1)
            disposition = request.form.get(key)
            if disposition != 'noaction':
                row.add(disposition)

                movie_path = request.form.get(f'movie_path_{img_num}')
                row.add(movie_path)
                table.add_row(row)
                odir = basedir / disposition
                movie_date = get_movie_date(movie_path)
                yymm = movie_date.strftime('%y-%m')
                odir_str = str(odir.absolute()).replace('{yy-mm}', yymm)
                row.add(odir_str)
                odir = Path(odir_str)
                odir.mkdir(parents=True, exist_ok=True)
                if disposition not in counts.keys():
                    counts[disposition] = 1
                else:
                    counts[disposition] += 1

                q = Path(movie_path).with_suffix('.*')
                mv_files = list(q.parent.glob(q.name))
                for mv_file in mv_files:
                    dest = odir / mv_file.name
                    if dest.exists() and replace:
                        dest.unlink()
                        what_we_did.add_row(PageTableRow(f'{Path(mv_file).name} already existed at {disposition}'))
                    else:
                        dest = get_outfile(mv_file, odir)
                    shutil.move(mv_file, str(dest.absolute()))
                    what_we_did.add_row(PageTableRow(f'Moved {Path(mv_file).name} to {disposition} at {dest.parent}'))

    cnt_table = PageTable()
    hdr_row = PageTableRow(row_type=RowType.HEAD)
    hdr_row.add(['Disposition', 'Count'])
    cnt_table.add_row(hdr_row)
    move_count = 0

    for k, v in counts.items():
        move_count += int(v)
        r = PageTableRow([k, v])
        cnt_table.add_row(r)

    my_page.add(PageItemHeader(f"Selected {move_count} movies out of {in_files}/{total_files} moved to {basedir}", 2))

    my_page.add(cnt_table)

    my_page.add(table)
    my_page.add_blanks(2)

    # my_page.add(PageItemHeader('Actions:', 3))
    # my_page.add(what_we_did)

    ret_html = my_page.get_html()
    return ret_html


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    page = Page()
    page.title = 'vsorter settings'
    page.add(PageItemHeader('Video sorter settings', 2))

    html = page.get_html()
    return html


@app.route('/vsorter_action')
def vsorter_action():
    return 'Hello, World!'


if __name__ == '__main__':
    app.run()
