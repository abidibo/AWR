# AWR
abidibo's web radios software

AWR is a software which provides an interface to control web radios streaming with mplayer.
Web radios are configured in a json file and showed to the user.
Stream can be stopped/paused/resumed.
If a connection error occurs a notification message informs you.
The mplayer output is parsed in order to get the curent song title and artist, it works with many web radios but not all. Some web radios split the artist and the track title with a new line character. In the future perhaps I'll make the regexp configurable in the json file.
AWR was developed using the pygtk3 technology, no glade was armed in the making of this project.

## Requirements

- GTK+3
- python (2.6 or later)
- mplayer

## Installation
Just download the project and run awr.py.

You may use git

    git clone https://github.com/abidibo/AWR.git ./
    cd AWR.git
    python awr.py

Or simply download a tarball or a zip file from github, uncompress it in your HD and run the awr.py (right click, open with python)

## Usage
AWR comes with some web radios preconfigured. You may want to change them all or add some, then let's see how.

The configuration file id the *radios.json* file inside the *conf* folder. Open it and notice that all web radios are divided by genres. Each genre occupies a notebook page in the interface. Add here your genres or web radios. 
A web radio json object requires:

- name: the radio name
- url: the streaming url
- description: the radio description (a few words)
- img: the path to the image file relative to the project root. In the provided software all images are 64X64 px.
- playlist: whether or not the playlist option is required for mplayer to stream this url

Click the abidibo avatar to toggle between light and dark themes.

## License
© 2013 Stefano Contini - MIT License (http://opensource.org/licenses/MIT). See the LICENSE file for more information.

## Releases

- 2014-12-03 v0.1.1
- 2013-11-22 v0.1.0
