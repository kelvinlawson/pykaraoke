
---------------------------------------------------------------------------

Release:      pykaraoke v0.4.1
Date:         29/12/2005
Author:       Kelvin Lawson <kelvinl@users.sourceforge.net>
License:      LGPL
Website:      http://www.kibosh.org/pykaraoke/
Contributors: William Ferrell <willfe@gmail.com>
              David Rose <pykar@ddrose.com>

---------------------------------------------------------------------------

INTRODUCTION

PyKaraoke is a karaoke player for Linux and Windows.

The following song formats are supported:
 * CDG (MP3+G, OGG+G)
 * MIDI/KAR
 * MPEG

No song files are provided - this package provides you with the player
needed to play your own karaoke song files.

---------------------------------------------------------------------------

WHAT'S NEW

This release includes still more major performance improvements in the
CDG player.  There should be very few performance bottlenecks
remaining when playing CDG files.  The MIDI player has also received a
number of improvements with this release, including word wrap and
dynamic text scaling.

We have added the pykaraoke_mini interface, suitable for environments
lacking a keyboard/mouse, or for simple, casual karaoke parties.

This is the first release with support for the handheld GP2X console.

The PyKaraoke GUI now supports dragging and dropping songs from the Search
Results and Folder View windows into the Playlist. It's also now possible 
to use drag-and-drop within the Playlist to reorder the songs.

Craig Rindy added handling to the GUI file database for filenames with
non-ASCII characters. He also modified pykaraoke.py to make some of its
functionality reusable by other scripts.

The CDG player saw some changes for this release. A bug was found and fixed
in the handling of certain CDG files (due to the handling of the CDG Border
Preset command). The pycdg.py script no longer requires a .cdg extension
so you can use tab-completion from the command-line to start CDGs. Finally
some fixes were made to add support for a wider range of Python versions.

---------------------------------------------------------------------------

INSTALLATION (WINDOWS)

Windows users can install PyKaraoke by simply downloading and running the
installer executable. This installs all prerequisite libraries, and adds
icons in your start menu to run PyKaraoke.

If you prefer, you may choose to build the Windows version from
source.  We will assume you are familiar with the steps involved for
installing a Python distribution from source on Windows; they are
similar to those for the Linux installation, below.  You will need to
download and unpack the SDL source distribution to a known place (for
instance, in the same directory with PyKaraoke, under the name like
"SDL-1.2.11", and you need to tell Python where that place is, with
the --include-dirs and --library-dirs option to setup.py, like this:

# python setup.py install --include-dirs=SDL-1.2.11/include --library_dirs=SDL-1.2.11/lib

---------------------------------------------------------------------------


INSTALLATION (LINUX, SOURCE INSTALLS)

PyKaraoke requires the following libraries to be installed:

 * Python (www.python.org)
 * Pygame (www.pygame.org)
 * WxPython (www.wxpython.org)
 * Numeric python module (numpy.sourceforge.net)

If these libraries are not already installed on your system, you can
download them from the websites listed.

Linux users may find these packages are available directly from their
distro's package manager.

Gentoo users can install all prerequisites using:
	# emerge python pygame wxGTK wxpython numeric

Debian users can install all prerequisites using:
	# apt-get install python python-pygame libwxgtk-python python-numeric

With the prerequisites installed, unzip the release and run the following
as root:

# python setup.py install

This installs the executables into /usr/bin, and you can then run
PyKaraoke from anywhere using "pykaraoke".

Alternatively you can run PyKaraoke without installing by simply
unzipping and running "python pykaraoke.py" from the unzip location.

---------------------------------------------------------------------------

INSTALLATION (MIDI/KAR FILE SUPPORT ON LINUX)

Windows users can enjoy MIDI/KAR file support using the standard
installation procedure.

MIDI/KAR support on Linux, however, requires the following:

 * Timidity++ (timidity.sourceforge.net)
 * Sound/patches for Timidity++

There are various sound patch collections available for Timidity++. Users
of PyKaraoke have used freepats and Eric Welsh's GUS patches.

To install Timidity++ on Gentoo together with Eric Welsh's patches use:

	# emerge timidity++ timidity-eawpatches

---------------------------------------------------------------------------

INSTRUCTIONS

If you used the install script you can start the player using:

	$ pykaraoke

Otherwise, start the player using:
	$ python pykaraoke.py

Once started, you will be presented with the Search View. From here you
can search through the karaoke songs in your database. You must first set
up your searchable song database, however, by clicking "Add Songs".

On the Add Songs popup you can add the folders containing your karaoke
songs, and perform your initial scan. This can be slow if you have a lot
of files, so PyKaraoke searches the disk once to build the database, and 
actual searches in the search engine only do a fast search in the database.

Once the scan is performed, you can save your database so that it will
still be available the next time you run PyKaraoke.

You can also specify various options when building the database, such as
filtering out which type of song file you wish to include in the database.
You can also request that the scan looks inside ZIP files for any karaoke
files contained in them.

Don't forget to run the scan again if you collect more karaoke files in
your folders.

With the search database set up, you can now enter searches in the search
engine in the main window. Matched search results will fill up in the left
pane, from where you can play them directly (double-click) or add them to
the playlist (right-click popup).

The right pane contains your playlist. You can perform your searches and
add them to the playlist, without actually starting a song playing. When
you are happy with the playlist collection, double-click on the song you
would like to start on, and a player window will open. When that song is
finished PyKaraoke moves on to the next song in your playlist. You can
delete single songs from the playlist, or clear the entire list by right-
clicking items in the playlist.

If you do not wish to use the search engine functionality, there is also a
Folder View, which can be selected using a drop-down in the main window.
From here you can browse the folders on your disk, and select individual
tracks for playing, or adding to the playlist.

---------------------------------------------------------------------------

MINI VERSION

There is now a reduced-interface frontend for PyKaraoke, which you can
invoke with:

	$ pykaraoke_mini

Or:
	$ python pykaraoke_mini.py

This is a more primitive interface which runs in the same window that
is also used for displaying the lyrics of the Karaoke songs.  It is
specifically designed to be a useful interface with a minimal input
device, for instance with a joystick or a remote control, for those
environments when you don't have convenient access to a full keyboard
and mouse.  It is the default interface on the GP2X handheld.

The pykaraoke_mini interface presents a scrolling window that lists
all of the songs in your database in alphabetical order by filename
(but you can also sort them by song title or artist name; see TITLES
AND ARTIST NAMES, below).

You can easily navigate through this list with the up and down arrow
keys, and press enter to select a song.  If you hold down the arrow
keys, the highlight gradually accelerates until it is moving quite
fast, so it doesn't take long to navigate through even a very large
list.  You can also use the PageUp and PageDown keys to move a
screen's worth at a time.

By default, the font is quite large, chosen to be easily visible on a
Karaoke monitor across the room.  You can change the font size at run
time (for instance, to make more text appear on the page) by pressing
the - and + keys.  This also affects the size of the font chosen for
the lyrics if you select a .kar file.

There is no search function in the mini player; the list always
includes the entire database.  (But you can type a few letters to go
straight to the song that begins with that string.)  There is also no
playlist feature; you must pick each song and play it one at a time.

The mini player uses the same database as the full-featured player, so
you may need to launch the full player from time to time to re-scan
the song database or update the directory list.  Alternatively, you
can use the command-line interface to do this:

pykaraoke_mini --set_scan_dir=/my/song/directory

   Removes any directories you had already set, and adds
   /my/song/directory as the only song directory.

pykaraoke_mini --add_scan_dir=/my/other/song/directory

   Adds /my/other/song/directory to the list of directories to scan.
   This option may be repeated.

pykaraoke_mini --scan

   Actually rescans all of the recorded directories into the database.

---------------------------------------------------------------------------

SONG TITLE AND ARTIST NAMES

By default, songs are listed in the search results panel by filename.
If you name your karaoke files with descriptive names, that may be all
you need.  However, as of PyKaraoke version 0.5, there is now a
feature which can record a separate title and/or artist name along
with each song.  These names will appear in separate columns in the
search results, and you can click on the column header to re-sort the
selected songs by the indicated column; for instance, click on the
"Artist" column to sort all of the songs in alphabetical order by
artist name.  In the mini player, press the TAB key to change the sort
mode between title, artist, and filename.

To get the artist and title names in the database, you must create a
file called titles.txt in the same directory with your song files, and
add one line for each song file, of the form:

filename<tab>title

or

filename<tab>title<tab>artist

The separator character between the fields must be an actual TAB
character, not just a sequence of spaces.  If you want to use
international characters in the title and artist names, save the file
using the utf-8 encoding.

Once you have created this file, re-scan the directory to read it into
the database.

---------------------------------------------------------------------------

COMMAND LINE VERSION

PyKaraoke is actually a GUI frontend which controls three libraries, pycdg
for CDG files, pykar for MIDI/KAR files, and pympg for MPEG files. If you 
do not wish to use the GUI you can actually start a player directly from 
the command-line (or by associating file-types in your operating system).

You can play MP3+G or OGG+G files using:
	# python pycdg.py songfilename.cdg

For a list of command-line options for pycdg.py, run:
	# python pycdg.py --help

KAR/MID files can be played using:
	# python pykar.py karfilename.mid

MPEG files can be played using:
	# python pympg.py mpegfilename.mpg

Note that if you used the install script, the above scripts can be started
using "pycdg", "pykar" or "pympg" from anywhere.

---------------------------------------------------------------------------

COMMON INSTALLATION ISSUES

LINUX DISTROS WITHOUT MP3 SUPPORT

Due to MP3 licensing issues, some distros such as Fedora Core and SUSE may
not include MP3 support in the SDL_mixer library. If this is the case you
will see the following message when attempting to play an MP3+G track:

    pygame.mixer.music.load(self.SoundFileName)
    error: Module format not recognized

To rebuild SDL_mixer with MP3 support, you need to install the smpeg-devel
package, and download and build SDL_mixer from source. The source tarball
for SDL_mixer can be downloaded from 
http://www.libsdl.org/projects/SDL_mixer/ and should be built as follows:

    # ./configure --prefix=/usr --enable-music-mp3
    # make; make install

You may need to modify the --prefix option depending on where
libSDL_mixer.so is installed on your distro. The above example assumes it
will be installed to /usr/lib/libSDL_mixer.so.

A full example SDL_mixer build procedure for Fedora Core has been 
provided by a PyKaraoke user:

    # rpm -ivh smpeg-devel-0.4.4-0.rhfc1.dag.i386.rpm
    # rpm -ev --nodeps SDL_mixer
    # tar xzvf SDL_mixer-1.2.6.tar.gz
    # cd SDL_mixer-1.2.6
    # ./configure --prefix=/usr --enable-music-mp3
    # make; make install

SuSE users may also need to install the slang-devel package.


AMD64 INSTALLATIONS

If you are running on the AMD64 platform (and possibly others) you may see
this error on startup:

Exception in thread Thread-1:
Traceback (most recent call last):
	...
ValueError: unsupported datatype for array

If this occurs, you need to download and install the latest development
release of pygame. Follow the instructions at http://pygame.org/cvs.html to obtain the latest development release, then:

1. Build the new release by running:
   # python makeref.py
   # python setup.py install --prefix=/path/to/temporary/spot
2. Find the directory named "pygame" within /path/to/temporary/spot/lib (on a
   development machine, the path was lib/python2.4/site-packages/pygame) and
   copy or move it (all of it, including the directory itself) into the
   folder containing pycdg.py and the rest of the PyKaraoke files.

The CDG player should then work properly.

---------------------------------------------------------------------------

CHANGELOG (v0.5)

Changes in v0.5 (submitted by David Rose):

* Fixed a problem in pykar.py with synchronization of lyrics to music
  on certain MIDI files (files in which the tempo changes during the
  song).
* Reworked rendering engine in pykar.py to support wordwrap and font
  scaling.
* Wrote pykaraoke_mini.py, with an in-window scrolling interface for
  environments in which a full keyboard/mouse is not available.
* Added pykplayer.py and pykmanager.py to collect together common bits
  of code between the various player types.
* Made command-line options available to all public entry points:
  pycdg.py, pykar.py, pymgr.py, pykaraoke.py, and pykaraoke_mini.py.
* Replaced threading code with explicit calls to manager.Poll().
* Moved the CDG-processing code from pycdg.py into pycdgAux.py, and
  also ported it down to C in _pycdgAux.c for further runtime
  optimization.
* Pushed default framerate back to 30 fps.  Setting it lower than
  that has limited benefit with the new codebase.
* Added --zoom to control the mode in which pycdg.py scales its
  display to fit the window.
* Added command-line parameters to control audio properties.
* Added separate "titles" and "artists" columns to the song database,
  making it possible to sort the returned songlist by any of the three
  columns.  The file titles.txt can be defined in the directory with
  all of your song files to define the title and/or artist for each
  song.
* Ported to the GP2X.

Changes in v0.4.2:

* pycdg.py: Allow CDG filenames without extension (just a .) to allow for 
  tab-completion.
* pycdg.py: Fix border preset (don't clear full-screen).
* pycdg.py: Add --nomusic option.
* pycdg.py: pycdg: Fix option type 'str' in optparse
* pycdg.py: pycdg: Fix FutureWarning on 0xFFFFFFFFs
* pykaraoke.py: Add drag-and-drop support from search results and within
  playlist.
* pykaraoke.py: Add drag-and-drop from Folder View
* pykaraoke.py: Reuse PyKaraoke without the GUI from Craig Rindy.
* pykaraoke.py: Support non-ASCII characters in filenames from Craig Rindy.

Changes in v0.4.1:

* Add install script and /usr/bin links in install directory.
* Get icons and fonts from current directory or /usr/share/pykaraoke.
* Use /usr/bin/env for shebang.
* pycdg.py: Fix typo in "CDG file may be corrupt" warning (wwf)
* pycdg.py: Add -t/--title option to set the window title to 
  something specific (useful for window managers that can remember
  window settings like sticky, size, location, stacking, desktop,
  etc., based on window title/name/class attributes, like 
  Enlightenment does) (wwf)
* pykaraoke.py: Add KAR inside ZIP fix from Andrei Gavrila.
* pykaraoke.py: Add mid/mpg extension fix from Andrei Gavrila.
* pycdg.py: Default to 10 frames per second.
* pycdg.py: Fix scrolling variable names
* pykaraoke.py: Fix wx 2.6 API change.
* pycdg.py: Split the screen into 24 tiles for better screen 
  update performance.
* pycdg.py: Lower delay time when no packets are due.
* pycdg.py: Don't update the screen if 1/4 second out of sync.
* pycdg.py: Don't specify the display depth, pygame will use the
  most appropriate.

Changes in v0.4 (All modifications submitted by William Ferrell):

* Use optparse to support additional command-line options (optparse is 
  included in Python 2.3 and newer, on all standard Python-supporting 
  platforms); run "pycdg.py --help" to see a full list of supported 
  options.
* Permit user to specify window's starting X and Y positions
* Permit user to specify window's starting X and Y sizes
* Permit user to start the player in fullscreen mode
* Permit user to specify FPS on command line, defaults to 60
* Pass cdgPlayer.__init__() an "options" object now instead of a filename;
  contains size_x, size_y, pos_x, pos_y, fullscreen, cdgFileName
* cdgPlayer.run(): it's pedantic, but use self.Close() instead of setting
  self.State manually
* Add key binding "q" to exit ([ESC] still works)
* Hide the mouse cursor (both in fullscreen and in windowed mode)
* Fix "Frames Per Second" so it's honored (previously it was ignored because
  curr_pos wasn't always updated as often as needed)
* Change order of import statements so local versions of pygame, Numeric can be
  picked up if present.
* Check for all mixed-case cases of matching audio files (mp3, ogg)
* Misc. tab/spacing fixes in "constant" definitions

Changes in v0.3.1:

* Added full-screen player mode (CDG and MPG)
* Supports the latest WxPython (v2.6)
* Improved CPU usage
* Displays ZIP filename together with the internal song filename

Changes in v0.3:

 * Added MIDI/KAR file support
 * CDG player now uses psyco for faster playback on low-end machines 
 * Better handling of corrupt CDG rips
 * Minor changes to make it more OSX-friendly
 * Added facility for cancelling song database builds in PyKaraoke GUI

Changes in v0.2.1:

 * Fixed colour cycling in the CDG player
 * Fixed transparent colours used in CDG files
 * Searches are optimised to handle thousands of CDG files very quickly
 * Fixed inaccurate right-clicking in the playlist on some systems
 * Fixed Windows drive icon
 * Fixed tree root issue on some Linux systems
 * Added more status messages to the status bars

Changes in v0.2:

 * PyKaraoke can now be used on Windows (98/XP/2000)
 * Modified the playlist logic
 * Changes to work with pygame-1.6.2

---------------------------------------------------------------------------

TEST SYSTEMS

PyKaraoke has been tested on (at least) the following systems:

 * Gentoo Linux (python-2.3.4, wxGTK-2.4.2-r2, pygame-1.6,   numeric-23.1)
 * Windows 2000 (python-2.3,   wxPython-2.5,   pygame-1.6,   numeric-23.6)
 * Windows XP   (python-2.3,   wxPython-2.4,   pygame-1.6.2, numeric-23.7)
 * Windows XP   (python-2.4,   wxPython-2.5,   pygame-1.6,   numeric-23.7)
 * Windows 98   (python-2.3,   wxPython-2.4,   pygame-1.6,   numeric-23.7)

---------------------------------------------------------------------------

SUGGESTIONS

This is an early release of pykaraoke. Please let us know if there are any
features you would like to see added, or you have any other suggestions or
bug reports. Contact the project at <kelvinl@users.sourceforge.net>

---------------------------------------------------------------------------
