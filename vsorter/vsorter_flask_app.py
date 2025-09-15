import re
import shutil
import textwrap
import traceback
from pathlib import Path

from flask import Flask, request
from ja_webutils.Page import Page
from ja_webutils.PageItem import PageItemHeader, PageItemLink, PageItemString
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
def process_vsort():  # put the application's code here
    keys = request.form.keys()
    disp_pat = re.compile("disposition_(\\d+)")
    my_page = Page()
    basedir = request.form.get('basedir')
    basedir = Path(basedir) if basedir else None
    replace = request.form.get('replace') == 'True'
    in_files = request.form.get('in_files')
    total_files = request.form.get('total_files')
    table = PageTable(id='saved_movies')
    table.sorted = True
    table.sort_initial_order = {0:0}
    hdr = ['Disposition', 'Source', 'Destination', 'Link to destination file']
    hdr_row = PageTableRow(hdr, RowType.HEAD)
    table.add_row(hdr_row)
    what_we_did = PageTable()
    counts = dict()

    try:
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
                    out_file = get_outfile(movie_path, odir)
                    out_dir = out_file.parent
                    row.add(str(out_file.parent))

                    link = PageItemLink(f'file://{out_file.absolute()}', f'moved: {out_file.parent.name}/{out_file.name}',)
                    row.add(link)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    if disposition not in counts.keys():
                        counts[disposition] = 1
                    else:
                        counts[disposition] += 1

                    # get a list of all files with the same name in the same directory, eg avi, mp4, gif
                    q = Path(movie_path).with_suffix('.*')
                    mv_files = list(q.parent.glob(q.name))
                    for mv_file in mv_files:
                        dest = out_file
                        if dest.exists() and replace:
                            dest.unlink()
                            what_we_did.add_row(PageTableRow(f'{Path(mv_file).name} already existed at {disposition}'))

                        shutil.move(mv_file, str(dest.absolute()))
                        what_we_did.add_row(PageTableRow(f'Moved {Path(mv_file).name} to {disposition} at {dest.parent}'))

        cnt_table = PageTable(id='count_table')
        hdr_row = PageTableRow(row_type=RowType.HEAD)
        hdr_row.add(['Disposition', 'Count'])
        cnt_table.add_row(hdr_row)
        move_count = 0

        for k, v in counts.items():
            move_count += int(v)
            r = PageTableRow([k, v])
            cnt_table.add_row(r)

        my_page.add(PageItemHeader(f"Selected {move_count} movies out of {in_files}/{total_files} moved to {basedir}", 2))

        my_page.add_blanks(2)
        my_page.add(PageItemHeader('Destination folder counts', 2))
        my_page.add(cnt_table)
        my_page.add_blanks(2)

        my_page.add(PageItemHeader('Saved movies', 2))
        my_page.add(table)
        my_page.add_blanks(2)

        my_page.add(PageItemHeader('What we did', 2))
        my_page.add(what_we_did)
        my_page.add_blanks(2)
        my_page.title = 'Movie Sorter'

        my_page.add(PageItemHeader('Notes', 2))
        File_link_note = textwrap.dedent('''\
        If the link to the file does not work in Chrome, you can coy the link address to the clipboard and
        paste into a new tab or window. <BR> Alternatively  
        you may want to install and configure the following extension. <BR>It is relatively safe to allow
        file links from http://127.0.0.1 to open in the browser.
        ''')
        my_page.add(PageItemString(File_link_note, escape=False))

        chrome_store_link = PageItemLink('https://chromewebstore.google.com/detail/enable-local-file-links/nikfmfgobenbhmocjaaboihbeocackld',
                                         'Chrome store extension to enable Local File Links')
        my_page.add(chrome_store_link)
    except Exception as ex:
        my_page.add(PageItemHeader('Error handling request', 2))
        my_page.add_blanks(2)
        my_page.add(f'{ex}')
        my_page.add_blanks(2)

        traceback_str = traceback.format_exc()
        traceback_str2 = traceback_str.replace('\n', '<br>')
        tbs = PageItemString(traceback_str2, escape=False)
        my_page.add(tbs)
        print(traceback_str)

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
