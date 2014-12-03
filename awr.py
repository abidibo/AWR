#! /usr/bin/python
"""
  AWR (abidibo's Web Radio software)
  This software provides an interface to control the mplayer software.
  The web raidios configured in  the conf/radios.json json file are displayed
  in a GtkNotebook by genre.

  @author abidibo (Stefano Contini) <dev@abidibo.net>
  @license MIT License (http://opensource.org/licenses/MIT)
  @date 2013
"""
from gi.repository import Gtk, Gdk, GObject
import subprocess
from threading import Thread
import re
import json
from xml.sax.saxutils import escape
from time import sleep
from os import path

from agtk import MainWindow

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
    self._style = 'light';
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
    self._stop_button = Gtk.Button(stock=Gtk.STOCK_MEDIA_STOP)
    self._stop_button.connect('clicked', self._app.stop_stream)
    controlbar_box.pack_start(self._stop_button, False, False, 0)
    # playpause button
    self._playpause_button = Gtk.Button(stock=Gtk.STOCK_MEDIA_PAUSE)
    self._playpause_button.connect('clicked', self._app.playpause_stream)
    controlbar_box.pack_start(self._playpause_button, False, False, 0)
    # onair label
    onair_label = Gtk.Label('on air')
    controlbar_box.pack_start(onair_label, False, False, 0)
    # track label (changes dynamically)
    self._track_label = Gtk.Label('--')
    self._track_label.get_style_context().add_class("evidence");
    controlbar_box.pack_start(self._track_label, False, False, 0)

    self.update()

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
      self._playpause_button.set_label(Gtk.STOCK_MEDIA_PAUSE)
      self._playpause_button.get_style_context().add_class("button-disabled");
    elif status == 'playing':
      self._playpause_button.set_sensitive(True)
      self._playpause_button.set_label(Gtk.STOCK_MEDIA_PAUSE)
      self._playpause_button.get_style_context().remove_class("button-disabled");
    else:
      self._playpause_button.set_label(Gtk.STOCK_MEDIA_PLAY)

  def update_track_label(self, status, track_title):
    if status == 'stopped':
      self.update_track('--')
    elif track_title:
      self.update_track(track_title)

  """
    @brief Creates the genres notebook
  """
  def create_notebook(self):
    json_data = open(project_path('conf/radios.json'))
    data = json.load(json_data)
    notebook = Gtk.Notebook()
    self._container.pack_start(notebook, False, False, 0)

    for genre in data['genres']:
      genre_label = Gtk.Label(genre['name']);
      genre_table = self.construct_genre_page(genre);
      notebook.append_page(genre_table, genre_label);

  """
    @brief Creates a genre page
  """
  def construct_genre_page(self, genre):
    num_radios = len(genre['radios'])
    grid = Gtk.Grid(row_spacing=10, margin=10)
    i = 0
    for radio in genre['radios']:
      img_button = Gtk.Button(image=Gtk.Image.new_from_file(project_path(radio['img'])))
      img_button.get_style_context().add_class("button-img");
      img_button.set_vexpand(False)
      img_button.connect('clicked', self._app.stream_radio, radio)
      label = Gtk.Label(use_markup=True, xalign=0, margin_left=5)
      label.set_line_wrap(True)
      label.set_markup('<b>%s</b>\n%s' % (radio['name'], radio['description']))
      grid.attach(img_button, 0, i, 1, 1)
      grid.attach_next_to(label, img_button, Gtk.PositionType.RIGHT, 1, 1)
      i = i + 1

    return grid

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
    @brief Updates the current track
  """
  def update_track(self, title):
    self._track_label.set_markup(title)

  """
    @brief Toggles between light and dark styles
  """
  def toggle_style(self, widget, event):
    self._style = 'dark' if self._style == 'light' else 'light'
    self.style_provider.load_from_path('./css/style-%s.css' % self._style)


"""
  Main app class
"""
class AWR:

  """
    @brief Constructor
  """
  def __init__(self):
    self._proc = None
    self._status = 'stopped'
    self._gui = AWRGUI(self)

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
    if radio['playlist']:
      self._proc = subprocess.Popen(["mplayer", "-slave", "-playlist", radio['url']], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    else:
      self._proc = subprocess.Popen(["mplayer", "-slave", radio['url']], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    self._status = 'init'

    thread = Thread(target = self.parse_stdout, )
    thread.start()

    self._gui.set_active_radio(widget)

  """
    Parses mplayer stdout to catch the track title
  """
  def parse_stdout(self):
    error = True
    for line in iter(self._proc.stdout.readline, ''):
      str_line = str(line).rstrip()
      if self._status == 'stopped':
        error = False
        break
      if str_line.startswith('ICY Info:'):
        info = str_line.split(':', 1)[1].strip()
        attrs = dict(re.findall("(\w+)='([^']*)'", info))
        title = attrs.get('StreamTitle', '(unknown)')
        self._status = 'playing'
        self._gui.update('<b>%s</b>' % escape(title))

    # if stdout stops without pressing the stop button then an error occurred
    if error:
      GObject.idle_add(self.display_info)

  """
    @brief Stops the stream
    @param GtkWidget widget the widget which was clicked
  """
  def stop_stream(self, widget):
    if self._proc:
      self._proc.stdin.write('stop\n')
      self._status = 'stopped'
      self._gui.update()

  """
    @brief Toggles the play/pause mode
    @param GtkWidget widget the widget which was clicked
  """
  def playpause_stream(self, widget):
    if self._proc:
      try:
        self._proc.stdin.write('pause\n')
        self._status = 'playing' if self._status == 'paused' else 'paused'
        self._gui.update()
      except:
        pass

  """
    @brief Kills the current mplayer process
  """
  def kill_proc(self):
    self._status = 'stopped'
    self._gui.update()
    if self._proc:
      try:
        self._proc.stdin.write('quit\n')
      except:
        pass
      sleep(1) # wait for thread to break
      self._proc.kill()

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
