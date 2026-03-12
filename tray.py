#! /usr/bin/python
"""
  Tray indicator module for AWR.
  Provides the system tray icon and context menu.

  @author abidibo (Stefano Contini) <dev@abidibo.net>
  @license MIT License (http://opensource.org/licenses/MIT)
"""
import gi
gi.require_version('Gtk', '3.0')
try:
  gi.require_version('AyatanaAppIndicator3', '0.1')
  from gi.repository import AyatanaAppIndicator3 as AppIndicator3
except (ValueError, ImportError):
  try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
  except (ValueError, ImportError):
    AppIndicator3 = None
from gi.repository import Gtk


class TrayIndicator:
  """
    @brief System tray indicator with context menu
  """
  def __init__(self, app, icon_path):
    self._app = app
    self._indicator = None
    if not AppIndicator3:
      return
    self._indicator = AppIndicator3.Indicator.new(
      'awr-radio',
      icon_path,
      AppIndicator3.IndicatorCategory.APPLICATION_STATUS
    )
    self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    self._indicator.set_menu(self._build_menu())

  def _build_menu(self):
    menu = Gtk.Menu()

    self._show_item = Gtk.MenuItem(label='Show/Hide')
    self._show_item.connect('activate', lambda _: self._app._gui.toggle_window())
    menu.append(self._show_item)

    menu.append(Gtk.SeparatorMenuItem())

    self._playpause_item = Gtk.MenuItem(label='Play/Pause')
    self._playpause_item.connect('activate', self._app.playpause_stream)
    menu.append(self._playpause_item)

    self._stop_item = Gtk.MenuItem(label='Stop')
    self._stop_item.connect('activate', self._app.stop_stream)
    menu.append(self._stop_item)

    menu.append(Gtk.SeparatorMenuItem())

    quit_item = Gtk.MenuItem(label='Quit')
    quit_item.connect('activate', self._on_quit)
    menu.append(quit_item)

    menu.show_all()
    return menu

  def _on_quit(self, widget):
    self._app.kill_proc()
    Gtk.main_quit()
