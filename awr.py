#! /usr/bin/python
"""
  AWR (abidibo's Web Radio software)
  This software provides an interface to control the mplayer software.
  The web raidios configured in  the conf/radios.json json file are displayed
  in a GtkNotebook by genre.

  @author abidibo (Stefano Contini) <dev@abidibo.net>
  @license MIT License (http://opensource.org/licenses/MIT)
  @copyright 2013-2014 abidibo
"""
import os
import tempfile
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
import subprocess
from threading import Thread, Timer
import re
import json
from xml.sax.saxutils import escape
from time import sleep
from os import path

from agtk import MainWindow
from station_manager import StationManager, StationManagerUI
from tray import TrayIndicator

def project_path(relative_path):
    return path.abspath(path.join(path.dirname(__file__), relative_path))

# without this line threads are executed after the main loop
GObject.threads_init()

"""
  @brief AWR Graphic User Interface
"""
class AWRGUI:
  """
    @brief Constructor
    @param AWR app the main application instance
  """
  def __init__(self, app):
    self._app = app
    self._active_radio = None
    self._style = 'dark';
    self._station_ui = StationManagerUI(self, app)
    # main window
    self._win = MainWindow('main_window', 'AWR', self._app.kill_proc)
    self._win.set_resizable(True)
    # main container
    self.create_container()
    # track and controllers
    self.create_controlbar()
    # notebook
    self.create_notebook()
    # footer
    self.create_footer()

    # style
    self.style_provider = Gtk.CssProvider()
    self.style_provider.load_from_path(project_path('css/style-%s.css' % self._style))
    screen = Gdk.Screen.get_default()
    styleContext = Gtk.StyleContext()
    styleContext.add_provider_for_screen(screen, self.style_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    self._win.show_all()

  """
    Main window widget getter
  """
  def get_win(self):
    return self._win

  """
    @brief Creates the external container
  """
  def create_container(self):
    self._container = Gtk.Box(name='main_container', spacing=5, orientation=Gtk.Orientation.VERTICAL, homogeneous=False, margin=10)
    self._win.add(self._container)

  """
    @brief Creates the controller top bar
    @description displays current track and stop, play, pause controllers
  """
  def create_controlbar(self):
    controlbar_box = Gtk.Box(spacing=5)
    controlbar_box.get_style_context().add_class("ctrlbar");
    self._container.pack_start(controlbar_box, False, False, 0)
    # stop button
    self._stop_button = self._create_icon_button('media-playback-stop', 'Stop')
    self._stop_button.connect('clicked', self._app.stop_stream)
    controlbar_box.pack_start(self._stop_button, False, False, 0)
    # playpause button
    self._playpause_button = self._create_icon_button('media-playback-pause', 'Pause')
    self._playpause_button.connect('clicked', self._app.playpause_stream)
    controlbar_box.pack_start(self._playpause_button, False, False, 0)
    # onair label
    onair_label = Gtk.Label('On Air')
    controlbar_box.pack_start(onair_label, False, False, 0)
    # track label (changes dynamically)
    self._track_label = Gtk.Label('--')
    self._track_label.get_style_context().add_class("evidence");
    controlbar_box.pack_start(self._track_label, True, False, 0)

    # volume controls (right side)
    self._mute_button = self._create_icon_button('audio-volume-high', None)
    self._mute_button.get_style_context().add_class("volume-button")
    self._mute_button.connect('clicked', self._app.toggle_mute)
    controlbar_box.pack_end(self._mute_button, False, False, 0)

    self._volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
    self._volume_scale.set_value(50)
    self._volume_scale.set_draw_value(False)
    self._volume_scale.set_size_request(120, -1)
    self._volume_scale.get_style_context().add_class("volume-scale")
    self._volume_scale.connect('value-changed', self._app.set_volume)
    controlbar_box.pack_end(self._volume_scale, False, False, 0)

    self.update()

  def _create_icon_button(self, icon_name, label_text):
    button = Gtk.Button()
    box = Gtk.Box(spacing=4)
    image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
    box.pack_start(image, False, False, 0)
    if label_text:
      label = Gtk.Label(label_text)
      box.pack_start(label, False, False, 0)
    button.add(box)
    button.show_all()
    return button

  def _set_icon_button(self, button, icon_name, label_text):
    child = button.get_child()
    if child:
      button.remove(child)
    box = Gtk.Box(spacing=4)
    image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
    box.pack_start(image, False, False, 0)
    if label_text:
      label = Gtk.Label(label_text)
      box.pack_start(label, False, False, 0)
    button.add(box)
    button.show_all()

  """
    @brief Updates the controllers
  """
  def update(self, track_title=None):
    status = self._app.get_status()
    self.update_stop_button(status)
    self.update_playpause_button(status)
    self.update_track_label(status, track_title)
    if status == 'stopped':
      self.unset_active_radio()

  """
    @brief Updates the stop button
  """
  def update_stop_button(self, status):
    if status == 'stopped' or status == 'init':
      self._stop_button.set_sensitive(False)
      self._stop_button.get_style_context().add_class("button-disabled");
    else:
      self._stop_button.set_sensitive(True)
      self._stop_button.get_style_context().remove_class("button-disabled");

  """
    @brief Updates the play and pause buttons
  """
  def update_playpause_button(self, status):
    if status == 'stopped' or status == 'init':
      self._playpause_button.set_sensitive(False)
      self._set_icon_button(self._playpause_button, 'media-playback-pause', 'Pause')
      self._playpause_button.get_style_context().add_class("button-disabled");
    elif status == 'playing':
      self._playpause_button.set_sensitive(True)
      self._set_icon_button(self._playpause_button, 'media-playback-pause', 'Pause')
      self._playpause_button.get_style_context().remove_class("button-disabled");
    else:
      self._set_icon_button(self._playpause_button, 'media-playback-start', 'Play')

  def update_track_label(self, status, track_title):
    if status == 'stopped':
      self.update_track('--')
    elif track_title:
      self.update_track(track_title)

  """
    @brief Creates the genres notebook
  """
  def create_notebook(self):
    self._notebook = Gtk.Notebook()
    self._container.pack_start(self._notebook, True, True, 0)
    self.rebuild_notebook()

    # Add Genre button below notebook
    add_genre_btn = self._create_icon_button('list-add', 'Add Genre')
    add_genre_btn.get_style_context().add_class("add-station-btn")
    add_genre_btn.set_halign(Gtk.Align.START)
    add_genre_btn.connect('clicked', self._station_ui.on_add_genre)
    self._container.pack_start(add_genre_btn, False, False, 0)

  """
    @brief Rebuilds the notebook tabs from radios.json
  """
  def rebuild_notebook(self):
    # remove all existing pages
    while self._notebook.get_n_pages() > 0:
      self._notebook.remove_page(0)

    data = self._app._station_manager.load_radios()

    for genre in data['genres']:
      genre_label = Gtk.Label(genre['name'])
      genre_page = self._station_ui.construct_genre_page(genre)
      self._notebook.append_page(genre_page, genre_label)

    # Discover tab
    discover_label = Gtk.Label('Discover')
    discover_page = self._station_ui.construct_discover_page()
    self._notebook.append_page(discover_page, discover_label)

    self._notebook.show_all()

  """
    Creates the application footer
  """
  def create_footer(self):
    abidibo_container = Gtk.EventBox()
    abidibo = Gtk.Image.new_from_file(project_path('abidibo.png'))
    abidibo.set_property('xalign', 1)
    abidibo_container.add(abidibo)
    abidibo_container.connect('button_press_event', self.toggle_style)
    self._container.pack_start(abidibo_container, False, False, 0)


  """
    Sets the active radio widget
  """
  def set_active_radio(self, widget):
    self.unset_active_radio()
    self._active_radio = widget
    self._active_radio.get_style_context().add_class("button-selected");

  """
    Unsets the active radio widget
  """
  def unset_active_radio(self):
    if self._active_radio:
      self._active_radio.get_style_context().remove_class("button-selected");
      self._active_radio = None

  """
    @brief Updates the mute button icon
  """
  def update_mute_button(self, muted):
    icon = 'audio-volume-muted' if muted else 'audio-volume-high'
    self._set_icon_button(self._mute_button, icon, None)

  """
    @brief Updates the current track
  """
  def update_track(self, title):
    self._track_label.set_markup(title)

  """
    @brief Hides window to tray instead of quitting
  """
  def _on_window_delete(self, widget, event):
    widget.hide()
    return True

  """
    @brief Shows or hides the main window
  """
  def toggle_window(self):
    if self._win.get_visible():
      self._win.hide()
    else:
      self._win.present()

  """
    @brief Toggles between light and dark styles
  """
  def toggle_style(self, widget, event):
    self._style = 'dark' if self._style == 'light' else 'light'
    self.style_provider.load_from_path(project_path('css/style-%s.css' % self._style))


"""
  Main app class
"""
class AWR:

  """
    @brief Constructor
  """
  def __init__(self):
    self._proc = None
    self._ffmpeg_proc = None
    self._status = 'stopped'
    self._volume = 50
    self._muted = False
    self._station_manager = StationManager()
    self._gui = AWRGUI(self)
    self._tmpdir = tempfile.mkdtemp()
    self._fifo_path = os.path.join(self._tmpdir, 'fifo')
    os.mkfifo(self._fifo_path)
    self._audio_fifo_path = os.path.join(self._tmpdir, 'audio_fifo')
    os.mkfifo(self._audio_fifo_path)
    self._tray = TrayIndicator(self, project_path('awr.png'))

  """
    @brief Gets the player status
  """
  def get_status(self):
    return self._status

  """
    @brief Starts the stream of a web radio
    @param GtkWidget widget the widget which was clicked
    @param Object radio the radio json object
  """
  def stream_radio(self, widget, radio):
    self.kill_proc()
    self._muted = False
    self._ffmpeg_proc = None
    self._current_radio_name = radio.get('name', '')
    self._gui.update_mute_button(False)
    url = radio['url']
    is_hls = url.endswith('.m3u8') or '/hls/' in url.lower()

    if is_hls:
      # HLS streams: ffmpeg writes continuous audio to a named pipe,
      # mplayer reads from it as a file (slave mode stays on the command fifo)
      self._ffmpeg_proc = subprocess.Popen(
        ["ffmpeg", "-y", "-i", url, "-vn", "-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3", self._audio_fifo_path],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
      )
      self._proc = subprocess.Popen(
        ["mplayer", "-slave", "-input", "file=%s" % self._fifo_path, "-cache", "2048", self._audio_fifo_path],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE
      )
    elif radio['playlist']:
      self._proc = subprocess.Popen(["mplayer", "-slave", "-input", "file=%s" % self._fifo_path, "-playlist", url], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    else:
      self._proc = subprocess.Popen(["mplayer", "-slave", "-input", "file=%s" % self._fifo_path, url], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    self._status = 'init'

    thread = Thread(target = self.parse_stdout)
    thread.daemon = True
    thread.start()

    self._gui.set_active_radio(widget)

  """
    Parses mplayer stdout to catch the track title
  """
  def parse_stdout(self):
    self._got_icy = False
    try:
      for line in iter(self._proc.stdout.readline, b''):
        str_line = line.decode('utf-8', errors='replace').rstrip()
        print(str_line)
        if self._status == 'stopped':
          break
        if str_line.startswith('Starting playback'):
          self._status = 'playing'
          GObject.timeout_add(50, self._gui.update)
          GObject.timeout_add(3000, self._show_radio_name_fallback)
        if str_line.startswith('ICY Info:'):
          self._got_icy = True
          info = str_line.split(':', 1)[1].strip()
          attrs = dict(re.findall("(\w+)='([^']*)'", info))
          title = attrs.get('StreamTitle', '(unknown)')
          self._status = 'playing'
          # fixes seg fault when updating gui from inside another thread
          GObject.timeout_add(100, self._gui.update, '<b>%s</b>' % escape(title))
    except (ValueError, OSError):
      pass  # pipe closed by stop/kill

    # if stdout ends without user stopping, a stream error occurred
    if self._status != 'stopped':
      GObject.idle_add(self.display_info)

  def _show_radio_name_fallback(self):
    if self._status == 'playing' and not self._got_icy and self._current_radio_name:
      GObject.idle_add(self._gui.update, '<b>%s</b>' % escape(self._current_radio_name))


  """
    @brief Stops the stream
    @param GtkWidget widget the widget which was clicked
  """
  def stop_stream(self, widget):
    if self._proc:
      self._status = 'stopped'
      self._proc.communicate(b'stop\n')
      self._gui.update()

  """
    @brief Toggles the play/pause mode
    @param GtkWidget widget the widget which was clicked
  """
  def playpause_stream(self, widget):
    if self._proc:
      try:
        fifo = os.open(self._fifo_path, os.O_WRONLY)
        os.write(fifo, 'pause\n'.encode('utf-8'))
        # self._proc.communicate(b'pause\n')
        self._status = 'playing' if self._status == 'paused' else 'paused'
        self._gui.update()
      except:
        pass

  """
    @brief Sets the volume
    @param GtkWidget widget the volume scale widget
  """
  def set_volume(self, widget):
    self._volume = int(widget.get_value())
    if self._proc:
      try:
        fifo = os.open(self._fifo_path, os.O_WRONLY)
        os.write(fifo, ('volume %d 1\n' % self._volume).encode('utf-8'))
        os.close(fifo)
      except:
        pass

  """
    @brief Toggles mute on/off
    @param GtkWidget widget the mute button widget
  """
  def toggle_mute(self, widget):
    if self._proc:
      try:
        fifo = os.open(self._fifo_path, os.O_WRONLY)
        os.write(fifo, b'mute\n')
        os.close(fifo)
        self._muted = not self._muted
        self._gui.update_mute_button(self._muted)
      except:
        pass

  """
    @brief Kills the current mplayer process
  """
  def kill_proc(self):
    self._status = 'stopped'
    self._gui.update()
    if self._proc:
      timer = Timer(3, self._proc.kill)
      try:
        timer.start()
        stdout, stderr = self._proc.communicate(b'quit\n')
        timer.cancel()
      except:
        pass
    if getattr(self, '_ffmpeg_proc', None):
      try:
        self._ffmpeg_proc.kill()
        self._ffmpeg_proc.wait()
      except:
        pass
      self._ffmpeg_proc = None

  """
    Displays a check internet connection message
  """
  def display_info(self):
    dialog = Gtk.MessageDialog(self._gui.get_win(), Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK, "Application streaming error")
    dialog.format_secondary_text(
            "An error occured while streaming audio data. Check your internet connection.")
    dialog.run()
    dialog.destroy()

  def main(self):
    Gtk.main()

if __name__ == "__main__":
  awr = AWR()
  awr.main()
