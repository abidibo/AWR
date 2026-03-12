# AWR

abidibo's web radios software

AWR is a software which provides an interface to control web radios streaming with mplayer.
Stations and genres can be added, edited and deleted directly from the app, or configured manually in the json file.
Stream can be stopped/paused/resumed, with volume control and mute support.
A **Discover** tab lets you search and preview stations from the [Radio Browser](https://www.radio-browser.info/) directory, and add them to your collection with one click.
If a connection error occurs a notification message informs you.
The mplayer output is parsed in order to get the curent song title and artist, it works with many web radios but not all. Some web radios split the artist and the track title with a new line character. In the future perhaps I'll make the regexp configurable in the json file.
AWR includes a system tray indicator for quick access to playback controls.
AWR was developed using the pygtk3 technology, no glade was armed in the making of this project.

## Requirements

- GTK+3
- python 3
- mplayer
- ffmpeg (for HLS stream support)

## Installation

Just download the project and run awr.py.

You may use git

    git clone https://github.com/abidibo/AWR.git ./
    cd AWR.git
    python awr.py

Or simply download a tarball or a zip file from github, uncompress it in your HD and run the awr.py (right click, open with python)

## Usage

### Managing stations in the app

You can manage your stations and genres directly from the interface:

- **Add/edit/delete stations** using the buttons next to each station
- **Add/delete genres** using the genre management controls
- **Discover new stations** via the Discover tab: search by name or country, preview stations, and add them to your collection

### Manual configuration

You can also configure stations manually. The configuration file is the *radios.json* file inside the *conf* folder. Open it and notice that all web radios are divided by genres. Each genre occupies a notebook page in the interface. Add here your genres or web radios.
A web radio json object requires:

- name: the radio name
- url: the streaming url
- description: the radio description (a few words)
- img: the path to the image file relative to the project root. In the provided software all images are 64X64 px.
- playlist: whether or not the playlist option is required for mplayer to stream this url

### Tips

- Click the abidibo avatar to toggle between light and dark themes.
- The system tray icon provides quick access to show/hide, play/pause, stop and quit.

## License

© 2013-2026 Stefano Contini - MIT License (<http://opensource.org/licenses/MIT>). See the LICENSE file for more information.
