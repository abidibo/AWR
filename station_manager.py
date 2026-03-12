"""
  Station Manager module for AWR
  Handles station CRUD (add/edit/delete), genre management,
  and radio discovery via the Radio Browser API.

  @author abidibo (Stefano Contini) <dev@abidibo.net>
  @license MIT License (http://opensource.org/licenses/MIT)
"""
import os
import re
import json
import shutil
import urllib.request
import urllib.parse
from threading import Thread
from xml.sax.saxutils import escape

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf, GObject

from os import path

def project_path(relative_path):
    return path.abspath(path.join(path.dirname(__file__), relative_path))

RADIO_BROWSER_API = 'https://de1.api.radio-browser.info'
USER_AGENT = 'AWR/0.2.0'
DISCOVER_PAGE_SIZE = 20


class StationManager:
  """
    Manages station data (load/save/add/remove/delete genre) on conf/radios.json
  """

  def load_radios(self):
    with open(project_path('conf/radios.json'), 'r') as f:
      return json.load(f)

  def save_radios(self, data):
    with open(project_path('conf/radios.json'), 'w') as f:
      json.dump(data, f, indent=2, ensure_ascii=False)

  def add_radio(self, genre_name, radio_data):
    data = self.load_radios()
    genre = next((g for g in data['genres'] if g['name'] == genre_name), None)
    if not genre:
      genre = {'name': genre_name, 'radios': []}
      data['genres'].append(genre)
    genre['radios'].append(radio_data)
    self.save_radios(data)

  def remove_radio(self, genre_name, radio_name):
    data = self.load_radios()
    genre = next((g for g in data['genres'] if g['name'] == genre_name), None)
    if genre:
      genre['radios'] = [r for r in genre['radios'] if r['name'] != radio_name]
    self.save_radios(data)

  def delete_genre(self, genre_name):
    data = self.load_radios()
    data['genres'] = [g for g in data['genres'] if g['name'] != genre_name]
    self.save_radios(data)


class StationManagerUI:
  """
    UI components for station management: genre pages with edit/delete buttons,
    add station dialog, and the Discover tab with Radio Browser API search.
  """

  def __init__(self, gui, app):
    self._gui = gui
    self._app = app
    self._manager = app._station_manager

  def _icon_button(self, icon_name, label_text):
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

  # ---------------------------------------------------------------------------
  # Genre page construction
  # ---------------------------------------------------------------------------

  def construct_genre_page(self, genre):
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin=10)

    # genre management bar
    hbox_top = Gtk.Box(spacing=5)
    del_genre_btn = self._icon_button('edit-delete', 'Delete Genre')
    del_genre_btn.get_style_context().add_class("delete-btn")
    del_genre_btn.connect('clicked', self._on_delete_genre, genre['name'])
    hbox_top.pack_end(del_genre_btn, False, False, 0)
    vbox.pack_start(hbox_top, False, False, 0)

    grid = Gtk.Grid(row_spacing=10)
    i = 0
    for radio in genre['radios']:
      img_path = project_path(radio['img']) if os.path.exists(project_path(radio['img'])) else project_path('img/default-radio.png')
      img_button = Gtk.Button(image=Gtk.Image.new_from_file(img_path))
      img_button.get_style_context().add_class("button-img")
      img_button.set_vexpand(False)
      img_button.connect('clicked', self._app.stream_radio, radio)
      info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, margin_left=5)
      info_box.set_hexpand(True)
      name_label = Gtk.Label(use_markup=True, xalign=0)
      name_label.set_markup('<b>%s</b>' % escape(radio['name']))
      name_label.get_style_context().add_class("station-name")
      name_label.set_line_wrap(True)
      name_label.set_max_width_chars(50)
      info_box.pack_start(name_label, False, False, 0)
      desc_label = Gtk.Label(xalign=0)
      desc_label.set_text(radio['description'])
      desc_label.set_line_wrap(True)
      desc_label.set_max_width_chars(50)
      info_box.pack_start(desc_label, False, False, 0)

      play_btn = self._icon_button('media-playback-start', 'Play')
      play_btn.set_tooltip_text('Play station')
      play_btn.get_style_context().add_class("manage-btn")
      play_btn.set_valign(Gtk.Align.CENTER)
      play_btn.connect('clicked', self._app.stream_radio, radio)

      edit_btn = self._icon_button('document-edit', 'Edit')
      edit_btn.set_tooltip_text('Edit station')
      edit_btn.get_style_context().add_class("manage-btn")
      edit_btn.set_valign(Gtk.Align.CENTER)
      edit_btn.connect('clicked', self._on_edit_station, genre['name'], radio)

      del_btn = self._icon_button('edit-delete', 'Delete')
      del_btn.set_tooltip_text('Delete station')
      del_btn.get_style_context().add_class("manage-btn")
      del_btn.set_valign(Gtk.Align.CENTER)
      del_btn.connect('clicked', self._on_delete_station, genre['name'], radio)

      grid.attach(img_button, 0, i, 1, 1)
      grid.attach(info_box, 1, i, 1, 1)
      grid.attach(play_btn, 2, i, 1, 1)
      grid.attach(edit_btn, 3, i, 1, 1)
      grid.attach(del_btn, 4, i, 1, 1)
      i = i + 1

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.add(grid)
    vbox.pack_start(scrolled, True, True, 0)

    return vbox

  # ---------------------------------------------------------------------------
  # Station add/edit/delete handlers
  # ---------------------------------------------------------------------------

  def _on_add_station(self, widget, genre_name):
    self._show_station_dialog('Add Station', genre_name=genre_name)

  def _on_edit_station(self, widget, genre_name, radio):
    prefill = {
      'name': radio['name'],
      'url': radio['url'],
      'description': radio['description'],
      'playlist': radio['playlist'],
    }
    self._show_station_dialog('Edit Station', prefill=prefill, original_genre=genre_name, original_radio=radio)

  def _on_delete_station(self, widget, genre_name, radio):
    dialog = Gtk.MessageDialog(
      self._gui.get_win(), Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
      Gtk.ButtonsType.YES_NO, 'Delete "%s"?' % radio['name'])
    dialog.format_secondary_text('This will remove the station from your configuration.')
    response = dialog.run()
    dialog.destroy()
    if response == Gtk.ResponseType.YES:
      self._manager.remove_radio(genre_name, radio['name'])
      self._gui.rebuild_notebook()

  def _on_delete_genre(self, widget, genre_name):
    dialog = Gtk.MessageDialog(
      self._gui.get_win(), Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
      Gtk.ButtonsType.YES_NO, 'Delete genre "%s"?' % genre_name)
    dialog.format_secondary_text('This will remove the genre and all its stations.')
    response = dialog.run()
    dialog.destroy()
    if response == Gtk.ResponseType.YES:
      self._manager.delete_genre(genre_name)
      self._gui.rebuild_notebook()

  def on_add_genre(self, widget):
    dialog = Gtk.Dialog(title='Add Genre', parent=self._gui.get_win(), modal=True)
    dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
    dialog.add_button('Add', Gtk.ResponseType.OK)
    content = dialog.get_content_area()
    content.set_spacing(8)
    content.set_margin_start(10)
    content.set_margin_end(10)
    content.set_margin_top(10)
    content.set_margin_bottom(10)
    entry = Gtk.Entry()
    entry.set_placeholder_text('Genre name')
    entry.connect('activate', lambda e: dialog.response(Gtk.ResponseType.OK))
    content.pack_start(Gtk.Label(label='Name:', xalign=0), False, False, 0)
    content.pack_start(entry, False, False, 0)
    dialog.show_all()
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
      name = entry.get_text().strip()
      if name:
        data = self._manager.load_radios()
        existing = [g['name'] for g in data['genres']]
        if name in existing:
          dialog.destroy()
          self._show_message('Error', 'Genre "%s" already exists.' % name)
          return
        data['genres'].append({'name': name, 'radios': []})
        self._manager.save_radios(data)
        self._gui.rebuild_notebook()
    dialog.destroy()

  # ---------------------------------------------------------------------------
  # Station dialog (add / edit)
  # ---------------------------------------------------------------------------

  def _show_station_dialog(self, title, genre_name=None, prefill=None, original_genre=None, original_radio=None):
    dialog = Gtk.Dialog(title=title, parent=self._gui.get_win(), modal=True)
    dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
    dialog.add_button('Save', Gtk.ResponseType.OK)
    dialog.set_default_size(450, -1)
    content = dialog.get_content_area()
    content.set_spacing(8)
    content.set_margin_start(10)
    content.set_margin_end(10)
    content.set_margin_top(10)

    # name
    name_entry = Gtk.Entry()
    name_entry.set_placeholder_text('Station name')
    if prefill:
      name_entry.set_text(prefill.get('name', ''))
    content.pack_start(Gtk.Label(label='Name:', xalign=0), False, False, 0)
    content.pack_start(name_entry, False, False, 0)

    # url
    url_entry = Gtk.Entry()
    url_entry.set_placeholder_text('Stream URL')
    if prefill:
      url_entry.set_text(prefill.get('url', ''))
    content.pack_start(Gtk.Label(label='URL:', xalign=0), False, False, 0)
    content.pack_start(url_entry, False, False, 0)

    # description
    desc_entry = Gtk.Entry()
    desc_entry.set_placeholder_text('Description')
    if prefill:
      desc_entry.set_text(prefill.get('description', ''))
    content.pack_start(Gtk.Label(label='Description:', xalign=0), False, False, 0)
    content.pack_start(desc_entry, False, False, 0)

    # playlist checkbox
    playlist_check = Gtk.CheckButton(label='URL is a playlist (.m3u / .pls)')
    if prefill:
      playlist_check.set_active(prefill.get('playlist', False))
    content.pack_start(playlist_check, False, False, 0)

    # icon chooser
    icon_box = Gtk.Box(spacing=5)
    icon_label_widget = Gtk.Label(label='Icon:', xalign=0)
    icon_chooser = Gtk.FileChooserButton(title='Select station icon')
    icon_filter = Gtk.FileFilter()
    icon_filter.set_name('Images')
    icon_filter.add_mime_type('image/png')
    icon_filter.add_mime_type('image/jpeg')
    icon_chooser.add_filter(icon_filter)
    icon_box.pack_start(icon_label_widget, False, False, 0)
    icon_box.pack_start(icon_chooser, True, True, 0)
    content.pack_start(icon_box, False, False, 0)

    # genre selector
    data = self._manager.load_radios()
    genre_names = [g['name'] for g in data['genres']]
    genre_combo = Gtk.ComboBoxText()
    genre_combo.append_text('-- New Genre --')
    for gn in genre_names:
      genre_combo.append_text(gn)
    # set active genre
    if genre_name and genre_name in genre_names:
      genre_combo.set_active(genre_names.index(genre_name) + 1)
    elif original_genre and original_genre in genre_names:
      genre_combo.set_active(genre_names.index(original_genre) + 1)
    else:
      genre_combo.set_active(1 if genre_names else 0)

    new_genre_entry = Gtk.Entry()
    new_genre_entry.set_placeholder_text('New genre name')
    new_genre_entry.set_no_show_all(True)

    def on_genre_changed(combo):
      if combo.get_active() == 0:
        new_genre_entry.show()
      else:
        new_genre_entry.hide()
    genre_combo.connect('changed', on_genre_changed)

    content.pack_start(Gtk.Label(label='Genre:', xalign=0), False, False, 0)
    content.pack_start(genre_combo, False, False, 0)
    content.pack_start(new_genre_entry, False, False, 0)

    dialog.show_all()
    response = dialog.run()

    if response == Gtk.ResponseType.OK:
      name = name_entry.get_text().strip()
      url = url_entry.get_text().strip()
      if not name or not url:
        dialog.destroy()
        self._show_message('Error', 'Name and URL are required.')
        return
      desc = desc_entry.get_text().strip()
      is_playlist = playlist_check.get_active()

      # handle icon
      icon_path = 'img/default-radio.png'
      chosen_file = icon_chooser.get_filename()
      favicon_url = prefill.get('favicon', '') if prefill else ''

      if chosen_file:
        ext = os.path.splitext(chosen_file)[1] or '.png'
        safe_name = re.sub(r'[^a-z0-9_-]', '', name.lower().replace(' ', '-'))
        dest = 'img/%s%s' % (safe_name, ext)
        shutil.copy2(chosen_file, project_path(dest))
        icon_path = dest
      elif favicon_url:
        icon_path = self._download_favicon(favicon_url, name)
      elif original_radio:
        icon_path = original_radio.get('img', 'img/default-radio.png')

      # determine genre
      if genre_combo.get_active() == 0:
        target_genre = new_genre_entry.get_text().strip()
        if not target_genre:
          dialog.destroy()
          self._show_message('Error', 'Please enter a genre name.')
          return
      else:
        target_genre = genre_combo.get_active_text()

      radio_data = {
        'name': name,
        'url': url,
        'description': desc,
        'img': icon_path,
        'playlist': is_playlist,
      }

      # if editing, remove original first
      if original_genre and original_radio:
        self._manager.remove_radio(original_genre, original_radio['name'])

      self._manager.add_radio(target_genre, radio_data)
      self._gui.rebuild_notebook()

    dialog.destroy()

  def _download_favicon(self, favicon_url, name):
    try:
      safe_name = re.sub(r'[^a-z0-9_-]', '', name.lower().replace(' ', '-'))
      dest = 'img/%s.png' % safe_name
      req = urllib.request.Request(favicon_url, headers={'User-Agent': USER_AGENT})
      with urllib.request.urlopen(req, timeout=5) as resp:
        img_data = resp.read()
      with open(project_path(dest), 'wb') as f:
        f.write(img_data)
      # resize to 64x64
      try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(project_path(dest), 64, 64, True)
        pixbuf.savev(project_path(dest), 'png', [], [])
      except Exception:
        pass
      return dest
    except Exception:
      return 'img/default-radio.png'

  def _show_message(self, title, text):
    dialog = Gtk.MessageDialog(self._gui.get_win(), Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK, title)
    dialog.format_secondary_text(text)
    dialog.run()
    dialog.destroy()

  # ---------------------------------------------------------------------------
  # Discover tab (Radio Browser API)
  # ---------------------------------------------------------------------------

  def construct_discover_page(self):
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)

    # search bar
    search_box = Gtk.Box(spacing=5)
    self._discover_entry = Gtk.Entry()
    self._discover_entry.set_placeholder_text('Search radios (e.g. jazz, rock, chill...)')
    self._discover_entry.set_hexpand(True)
    self._discover_entry.connect('activate', self._on_discover_search)
    search_box.pack_start(self._discover_entry, True, True, 0)

    # country filter
    self._country_entry = Gtk.Entry()
    self._country_entry.set_placeholder_text('Country code (IT, US, UK...)')
    self._country_entry.set_width_chars(22)
    search_box.pack_start(self._country_entry, False, False, 0)

    search_btn = self._icon_button('edit-find', 'Search')
    search_btn.connect('clicked', self._on_discover_search)
    search_box.pack_start(search_btn, False, False, 0)

    vbox.pack_start(search_box, False, False, 0)

    # spinner for loading
    self._discover_spinner = Gtk.Spinner()
    vbox.pack_start(self._discover_spinner, False, False, 0)

    # results area
    self._discover_results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.set_min_content_height(300)
    scrolled.add(self._discover_results_box)
    vbox.pack_start(scrolled, True, True, 0)

    # pagination
    self._discover_page = 0
    page_box = Gtk.Box(spacing=10)
    page_box.set_halign(Gtk.Align.CENTER)
    self._prev_btn = self._icon_button('go-previous', 'Prev')
    self._prev_btn.connect('clicked', self._on_discover_prev)
    self._prev_btn.set_sensitive(False)
    self._next_btn = self._icon_button('go-next', 'Next')
    self._next_btn.connect('clicked', self._on_discover_next)
    self._next_btn.set_sensitive(False)
    self._page_label = Gtk.Label('')
    page_box.pack_start(self._prev_btn, False, False, 0)
    page_box.pack_start(self._page_label, False, False, 0)
    page_box.pack_start(self._next_btn, False, False, 0)
    vbox.pack_start(page_box, False, False, 0)

    return vbox

  def _on_discover_search(self, widget):
    self._discover_page = 0
    self._run_discover_search()

  def _on_discover_prev(self, widget):
    if self._discover_page > 0:
      self._discover_page -= 1
      self._run_discover_search()

  def _on_discover_next(self, widget):
    self._discover_page += 1
    self._run_discover_search()

  def _run_discover_search(self):
    query = self._discover_entry.get_text().strip()
    country = self._country_entry.get_text().strip().upper()
    if not query and not country:
      return
    self._discover_spinner.start()
    for child in self._discover_results_box.get_children():
      self._discover_results_box.remove(child)
    self._page_label.set_text('')
    self._prev_btn.set_sensitive(False)
    self._next_btn.set_sensitive(False)

    thread = Thread(target=self._fetch_discover_results, args=(query, country, self._discover_page))
    thread.daemon = True
    thread.start()

  def _fetch_discover_results(self, query, country, page):
    offset = page * DISCOVER_PAGE_SIZE
    params = {
      'limit': str(DISCOVER_PAGE_SIZE),
      'offset': str(offset),
      'order': 'clickcount',
      'reverse': 'true',
      'hidebroken': 'true',
    }
    if query:
      params['name'] = query
    if country:
      params['countrycode'] = country

    url = '%s/json/stations/search?%s' % (
      RADIO_BROWSER_API,
      urllib.parse.urlencode(params)
    )
    try:
      req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
      with urllib.request.urlopen(req, timeout=10) as resp:
        stations = json.loads(resp.read().decode('utf-8'))
      GObject.idle_add(self._display_discover_results, stations, page)
    except Exception as e:
      GObject.idle_add(self._display_discover_error, str(e))

  def _display_discover_error(self, error_msg):
    self._discover_spinner.stop()
    label = Gtk.Label(label='Search failed: %s' % error_msg)
    self._discover_results_box.pack_start(label, False, False, 0)
    self._discover_results_box.show_all()

  def _display_discover_results(self, stations, page):
    self._discover_spinner.stop()
    for child in self._discover_results_box.get_children():
      self._discover_results_box.remove(child)

    if not stations:
      label = Gtk.Label(label='No stations found.' if page == 0 else 'No more stations.')
      self._discover_results_box.pack_start(label, False, False, 0)
      self._discover_results_box.show_all()
      self._prev_btn.set_sensitive(page > 0)
      self._next_btn.set_sensitive(False)
      self._page_label.set_text('Page %d' % (page + 1))
      return

    for station in stations:
      row = Gtk.Box(spacing=10)
      row.get_style_context().add_class("discover-row")

      # station info
      info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
      info_box.set_hexpand(True)
      name_label = Gtk.Label(use_markup=True, xalign=0)
      name_label.set_markup('<b>%s</b>' % escape(station.get('name', 'Unknown')))
      name_label.get_style_context().add_class("station-name")
      name_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
      info_box.pack_start(name_label, False, False, 0)

      details = []
      if station.get('country'):
        details.append(station['country'])
      if station.get('codec'):
        details.append(station['codec'])
      if station.get('bitrate') and station['bitrate'] > 0:
        details.append('%d kbps' % station['bitrate'])
      if station.get('tags'):
        details.append(station['tags'][:60])
      detail_label = Gtk.Label(xalign=0)
      detail_label.set_text(' | '.join(details))
      detail_label.set_ellipsize(3)
      info_box.pack_start(detail_label, False, False, 0)
      row.pack_start(info_box, True, True, 0)

      # preview (play) button
      play_btn = self._icon_button('media-playback-start', 'Play')
      play_btn.set_tooltip_text('Preview this station')
      play_btn.get_style_context().add_class("manage-btn")
      play_btn.connect('clicked', self._on_discover_preview, station)
      row.pack_start(play_btn, False, False, 0)

      # add button
      add_btn = self._icon_button('list-add', 'Add')
      add_btn.set_tooltip_text('Add to your radios')
      add_btn.get_style_context().add_class("manage-btn")
      add_btn.connect('clicked', self._on_discover_add, station)
      row.pack_start(add_btn, False, False, 0)

      self._discover_results_box.pack_start(row, False, False, 0)

    self._prev_btn.set_sensitive(page > 0)
    self._next_btn.set_sensitive(len(stations) >= DISCOVER_PAGE_SIZE)
    self._page_label.set_text('Page %d' % (page + 1))
    self._discover_results_box.show_all()

  def _on_discover_preview(self, widget, station):
    url = station.get('url_resolved') or station.get('url', '')
    radio = {
      'name': station.get('name', 'Unknown'),
      'url': url,
      'description': '',
      'img': 'img/default-radio.png',
      'playlist': url.endswith(('.m3u', '.m3u8', '.pls')),
    }
    self._app.stream_radio(widget, radio)

  def _on_discover_add(self, widget, station):
    url = station.get('url_resolved') or station.get('url', '')
    tags = station.get('tags', '')
    prefill = {
      'name': station.get('name', ''),
      'url': url,
      'description': tags,
      'playlist': url.endswith(('.m3u', '.m3u8', '.pls')),
      'favicon': station.get('favicon', ''),
    }
    self._show_station_dialog('Add Station', prefill=prefill)
