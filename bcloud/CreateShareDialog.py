# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Copyright (C) 2019 poplite <poplite.xyz@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from bcloud import Config
_ = Config._

from bcloud.const import SHARE_PERIOD, SHARE_PERIOD_NUM, SHARE_PWD_TABLE
from bcloud.log import logger
from bcloud import gutil
from bcloud import pcs

import random

class CreatePublicShareDialog(Gtk.Dialog):

    def __init__(self, app, fid_list):
        super().__init__(_('Public share'), app.window, Gtk.DialogFlags.MODAL)
        self.app = app
        self.fid_list = fid_list
        self.set_border_width(5)
        self.set_default_response(Gtk.ResponseType.OK)

        box = self.get_content_area()

        grid = Gtk.Grid()
        grid.halign = Gtk.Align.CENTER
        grid.props.column_spacing = 10
        grid.props.row_spacing = 5
        if Config.GTK_GE_312:
            grid.props.margin_start = 5
        else:
            grid.props.margin_left = 5
        box.pack_start(grid, True, True, 10)

        grid.attach(Gtk.Label.new(_('Period:')), 0, 0, 1, 1)

        self.period_combo = Gtk.ComboBoxText()
        self.period_combo.append_text(_('Forever'))
        self.period_combo.append_text(_('1 Day'))
        self.period_combo.append_text(_('7 Days'))
        self.period_combo.set_active(SHARE_PERIOD.FOREVER)
        grid.attach(self.period_combo, 1, 0, 1, 1)

        button_box = Gtk.Box(spacing=5)
        if Config.GTK_GE_312:
            button_box.props.margin_start = 13
        else:
            button_box.props.margin_left = 13
        box.pack_start(button_box, True, True, 0)

        ok_button = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        ok_button.connect('clicked', self.on_ok_button_clicked)
        button_box.pack_start(ok_button, False, False, 0)
        cancel_button = Gtk.Button.new_from_stock(Gtk.STOCK_CANCEL)
        cancel_button.connect('clicked', self.on_cancel_button_clicked)
        button_box.pack_start(cancel_button, False, False, 0)

        box.show_all()

    def on_ok_button_clicked(self, *args):
        def on_share(info, error=None):
            if error or not info or info['errno'] != 0:
                logger.error('CreatePublicShareDialog.on_share: %s, %s' %
                             (info, error))
                self.app.toast(_('Failed to share selected files'))
                return
            self.app.update_clipboard(info['shorturl'])
            self.response(Gtk.ResponseType.OK)

        period_id = self.period_combo.get_active()
        period = SHARE_PERIOD_NUM[period_id]
        gutil.async_call(pcs.enable_share, self.app.cookie, self.app.tokens,
                         self.fid_list, period, callback=on_share)


    def on_cancel_button_clicked(self, *args):
        self.response(Gtk.ResponseType.CANCEL)

class CreatePrivateShareDialog(Gtk.Dialog):

    def __init__(self, app, fid_list):
        super().__init__(_('Private share'), app.window, Gtk.DialogFlags.MODAL)

        self.app = app
        self.fid_list = fid_list
        self.set_border_width(5)
        self.set_default_size(200, 150)
        self.set_default_response(Gtk.ResponseType.OK)

        box = self.get_content_area()

        grid = Gtk.Grid()
        grid.halign = Gtk.Align.CENTER
        grid.props.column_spacing = 10
        grid.props.row_spacing = 5
        if Config.GTK_GE_312:
            grid.props.margin_start = 5
        else:
            grid.props.margin_left = 5
        box.pack_start(grid, True, True, 10)

        grid.attach(Gtk.Label.new(_('Period:')), 0, 0, 1, 1)
        grid.attach(Gtk.Label.new(_('Password:')), 0, 1, 1, 1)

        self.period_combo = Gtk.ComboBoxText()
        self.period_combo.append_text(_('Forever'))
        self.period_combo.append_text(_('1 Day'))
        self.period_combo.append_text(_('7 Days'))
        self.period_combo.set_active(SHARE_PERIOD.FOREVER)
        grid.attach(self.period_combo, 1, 0, 1, 1)

        self.passwd_entry = Gtk.Entry()
        self.passwd_entry.set_width_chars(4)
        self.passwd_entry.set_tooltip_text(
            _("The password must be 4 characters long, containing only 1-9, a-z"))
        grid.attach(self.passwd_entry, 1, 1, 1, 1)

        button_box = Gtk.Box(spacing=5)
        if Config.GTK_GE_312:
            button_box.props.margin_start = 30
        else:
            button_box.props.margin_left = 30
        box.pack_start(button_box, True, True, 0)

        ok_button = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        ok_button.connect('clicked', self.on_ok_button_clicked)
        button_box.pack_start(ok_button, False, False, 0)
        cancel_button = Gtk.Button.new_from_stock(Gtk.STOCK_CANCEL)
        cancel_button.connect('clicked', self.on_cancel_button_clicked)
        button_box.pack_start(cancel_button, False, False, 0)

        box.show_all()
        self.first_run()

    def first_run(self):
        self.passwd_entry.set_text(self.generate_share_pwd())

    def on_ok_button_clicked(self, *args):
        def on_share(info, error=None):
            if error or not info[0] or info[0]['errno'] != 0:
                logger.error('CreatePrivateShareDialog.on_share: %s, %s' %
                             (info, error))
                self.app.toast(_('Failed to share selected files'))
                return
            file_info, passwd = info
            self.app.update_clipboard(
                     "{0} {1}".format(file_info['shorturl'], passwd))
            self.response(Gtk.ResponseType.OK)

        period_id = self.period_combo.get_active()
        period = SHARE_PERIOD_NUM[period_id]
        passwd = self.passwd_entry.get_text()

        if len(passwd) == 4 and all([c in SHARE_PWD_TABLE for c in passwd]):
            gutil.async_call(pcs.enable_private_share, self.app.cookie,
                             self.app.tokens,self.fid_list,
                             passwd, period, callback=on_share)

    def on_cancel_button_clicked(self, *args):
        self.response(Gtk.ResponseType.CANCEL)

    def generate_share_pwd(self):
        '''随机获取4位分享提取码'''
        return ''.join(random.sample(SHARE_PWD_TABLE, 4))


