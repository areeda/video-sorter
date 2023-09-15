import re
import shutil
from pathlib import Path

from flask import Flask, request
from ja_webutils.Page import Page
from ja_webutils.PageItem import PageItemHeader
from ja_webutils.PageTable import PageTable, PageTableRow, RowType

from vsorter.movie_utils import get_outfile

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def process_vsort():  # put application's code here
    keys = request.form.keys()
    disp_pat = re.compile("disposition_(\\d+)")
    my_page = Page()
    basedir = request.form.get('basedir')
    basedir = Path(basedir) if basedir else None
    replace = request.form.get('replace') == 'True'
    my_page.add(PageItemHeader(f"Selected movies moved to {basedir}", 2))
    table = PageTable()
    table.sorted = True
    table.sorted = True
    hdr = ['Disposition', 'Thumb', 'Movie']
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
                if odir.exists():
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
                        what_we_did.add_row(PageTableRow(f'Moved {Path(mv_file).name} to {disposition}'))
                else:
                    what_we_did.add_row(PageTableRow(f'{odir} does not exist'))

    cnt_table = PageTable()
    hdr_row = PageTableRow(row_type=RowType.HEAD)
    hdr_row.add(['Disposition', 'Count'])
    cnt_table.add_row(hdr_row)

    for k, v in counts.items():
        r = PageTableRow([k, v])
        cnt_table.add_row(r)
    my_page.add(cnt_table)

    my_page.add(table)
    my_page.add_blanks(2)

    my_page.add(PageItemHeader('Actions:', 3))
    my_page.add(what_we_did)
    ret_html = my_page.get_html()
    return ret_html


if __name__ == '__main__':
    app.run()
