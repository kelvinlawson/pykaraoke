
---------------------------------------------------------------------------

Release:      pykaraoke v0.4
Date:         12/11/2005
Author:       Kelvin Lawson <kelvinl@users.sourceforge.net>
License:      LGPL
Website:      http://www.kibosh.org/pykaraoke/
Contributors: William Ferrell <willfe@gmail.com>

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

All modifications for v0.4 have been kindly contributed by Will Ferrell.

This release introduces several small changes and improvements. pycdg.py 
now accepts several command-line options; run "pycdg.py --help" to see a
full list. You can now specify the width and height of the output window,
and specify its position on the screen. You can now also start the output
window in fullscreen mode. Finally, the desired maximum frames per second
can be specified on the command line.

Other cosmetic changes include adding a key binding, [Q], to quit the 
player immediately (the [ESC] key binding for this remains as well), and 
hiding the mouse cursor when it's inside the player window (or entirely 
when the player is full screen).

---------------------------------------------------------------------------

INSTALLATION

PyKaraoke requires the following libraries to be installed:

 * Python (www.python.org)
 * Pygame (www.pygame.org)
 * WxPython (www.wxpython.org)
 * Numeric python module (numpy.sourceforge.net)
 * Optik (optik.sourceforge.net, *only* for Python 2.2 and older;
   it is shipped as "optparse" in Python 2.3 and newer by default)

If these libraries are not already installed on your system, you can
download them from the websites listed.

Linux users may find these packages are available directly from their
distro's package manager.

Gentoo users can install all prerequisites using:
	# emerge python pygame wxGTK numeric

Debian users can install all prerequisites using:
	# apt-get install python python-pygame libwxgtk-python python-numeric

There is currently no installer for pykaraoke. Unzip the release and you can
start the player from the unzip location.

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

Start the player using:
	# python pykaraoke.py

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

CHANGELOG (v0.4)

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
