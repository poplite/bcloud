# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Copyright (C) 2019 poplite <poplite.xyz@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk

from bcloud import Config
_ = Config._

from bcloud.log import logger
from bcloud import gutil
from bcloud import pcs
from bcloud import util

(CHECK_COL, ICON_COL, NAME_COL, PATH_COL, SIZE_COL,
            HUMANSIZE_COL, ISFILE_COL, LOADED_COL) = list(range(8))

NUM = 100
ICON_SIZE = 24

class UnzipBrowserDialog(Gtk.Dialog):

    is_loading = False

    def __init__(self, app, path):

        super().__init__(_('Unzip'), app.window, Gtk.DialogFlags.MODAL,
                        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.app = app
        self.path = path
        self.selected = []

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_border_width(10)
        self.set_default_size(440, 480)

        box = self.get_content_area()

        scrolled_win = Gtk.ScrolledWindow()
        box.pack_start(scrolled_win, True, True, 0)

        # check, icon, name, path, size, humansize, isfile, loaded
        self.treestore = Gtk.TreeStore(bool, GdkPixbuf.Pixbuf,
                                       str, str, GObject.TYPE_INT64,
                                       str, bool, bool)
        self.treeview = Gtk.TreeView(model=self.treestore)
        self.treeview.set_tooltip_column(NAME_COL)
        self.treeview.set_level_indentation(4)
        scrolled_win.add(self.treeview)

        check_cell = Gtk.CellRendererToggle()
        check_cell.connect('toggled', self.on_check_cell_toggled)
        check_col = Gtk.TreeViewColumn('', check_cell, active=CHECK_COL,
                                       visible=ISFILE_COL)
        self.treeview.append_column(check_col)

        name_col = Gtk.TreeViewColumn(_('Name'))
        name_cell = Gtk.CellRendererText()
        icon_cell = Gtk.CellRendererPixbuf()
        name_col.pack_start(icon_cell, False)
        name_col.pack_start(name_cell, True)
        name_col.add_attribute(icon_cell, 'pixbuf', ICON_COL)
        name_col.add_attribute(name_cell, 'text', NAME_COL)
        self.treeview.append_column(name_col)
        self.treeview.set_expander_column(name_col)
        self.treeview.connect('row-expanded', self.on_row_expanded)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(_('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)

        box.show_all()

        self.first_run()

    def first_run(self):
        self.list_dir()

    def list_dir(self, parent_iter=None):
        if parent_iter:
            if self.treestore[parent_iter][LOADED_COL]:
                return
            first_child_iter = self.treestore.iter_nth_child(parent_iter, 0)
            if first_child_iter:
                self.treestore.remove(first_child_iter)
            subpath = self.treestore[parent_iter][PATH_COL]
        else:
            subpath = '/'

        has_next = True
        shown = 0
        file_rows = []
        while has_next:
            infos = pcs.unzip_view(self.app.cookie, self.app.tokens, self.path,
                                   subpath, start=shown, limit=NUM, return_path=False)
            if not infos or infos.get('errno', -1) != 0:
                logger.error('UnzipBrowserDialog.list_dir: %s' %infos)
                has_next = False
                return
            shown += len(infos['list'])
            if shown >= infos['total']:
                has_next = False
            for file_ in infos['list']:
                isfile = not file_['isdir']
                pixbuf, type_ = self.app.mime.get(file_['file_name'], file_['isdir'],
                                                  icon_size=ICON_SIZE)
                size = int(file_['size'])
                human_size = util.get_human_size(size)[0]
                if not file_['file_name'].startswith('/'):
                    path = subpath + '/' + file_['file_name']
                else:
                    path = subpath + file_['file_name']
                row = [
                    False,
                    pixbuf,
                    file_['file_name'],
                    path,
                    size,
                    human_size,
                    isfile,
                    False,
                ]
                # 如果行表示文件，先放在file_rows，循环结束后再添加到treestore
                # 这样防止目录和文件在列表中交替显示，改善美观
                if isfile:
                    file_rows.append(row)
                else:
                    item = self.treestore.append(parent_iter, row)
                    self.treestore.append(item,
                            [False, None, file_['file_name'], '', 0, '0', False, False, ])
        for row in file_rows:
            self.treestore.append(parent_iter, row)

        if parent_iter:
            self.treestore[parent_iter][LOADED_COL] = True

    def on_row_expanded(self, treeview, tree_iter, tree_path):
        if self.is_loading:
            return
        self.is_loading = True
        self.list_dir(tree_iter)
        self.is_loading = False
        self.treeview.expand_row(tree_path, False)

    def on_check_cell_toggled(self, cell, tree_path):
        self.treestore[tree_path][CHECK_COL] = not \
                self.treestore[tree_path][CHECK_COL]
        if self.treestore[tree_path][CHECK_COL]:
            self.selected.append(tree_path)
        else:
            self.selected.remove(tree_path)

    def get_selected_paths(self):
        '''获取勾选文件的路径列表'''
        selected_paths = []
        for tree_path in self.selected:
            selected_paths.append(self.treestore[tree_path][PATH_COL])
        return selected_paths


