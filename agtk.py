#! /usr/bin/python
"""
  AGTKS (abidibo's GTK library)
  This library containes reusable GTK classes.

  @author abidibo (Stefano Contini) <dev@abidibo.net>
  @license MIT License (http://opensource.org/licenses/MIT)
  @date 2013
"""
from gi.repository import Gtk, Gdk

"""
  @brief Main window class
  @description Subclass Gtk.Window. Creates a Main window and attaches default events.
"""
class MainWindow(Gtk.Window):

  """
    Constructor
    @param string name the name of the window
    @param string title the window's title
    @param function destroy_callback a callback to run before destroying the window
  """
  def __init__(self, name, title, destroy_callback=None):
    self._destroy_callback = destroy_callback
    Gtk.Window.__init__(self, title=title, name=name)
    self.connect("delete_event", self.destroy)

  """
    Destroys the window
    @param GtkWidget widget widget which receives the event
    @param Mixed data additional data
  """
  def destroy(self, widget, data=None):
    if(self._destroy_callback):
      self._destroy_callback()
    return Gtk.main_quit()
