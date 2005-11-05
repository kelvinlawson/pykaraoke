
---------------------------------------------------------------------------

Release:    pykaraoke v0.3.1
Date:       21/10/2005
Author:     Kelvin Lawson <kelvinl@users.sourceforge.net>
License:    LGPL
Website:    http://www.kibosh.org/pykaraoke/

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

WHATS NEW

Due to popular demand, this release now supports full-screen borderless 
player windows (CDG and MPG only).

We have modified the GUI to support the latest WxPython (v2.6). CPU usage
has also been improved, as earlier versions didn't yield the CPU when not
doing work.

Finally, to handle situations where the zip filename contains the songname
but the internal song file does not, we now display both the zip and song
filename in the playlist.

---------------------------------------------------------------------------

INSTALLATION

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
	# emerge python pygame wxGTK numeric

Debian users can install all prerequisites using:
    # apt-get install python python-pygame libwxgtk-python python-numeric

There is currently no installer for pykaraoke. Unzip the release
and you can start the player from the unzip location.

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

KAR/MID files can be played using:
	# python pykar.py karfilename.mid

MPEG files can be played using:
	# python pympg.py mpegfilename.mpg

---------------------------------------------------------------------------

COMMON INSTALLATION ISSUES

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

---------------------------------------------------------------------------

CHANGELOG (v0.3.1)

* Added full-screen player mode (CDG and MPG)
* Supports the latest WxPython (v2.6)
* Improved CPU usage
* Displays ZIP filename together with the internal song filename

Changes since v0.3:

 * Added MIDI/KAR file support
 * CDG player now uses psyco for faster playback on low-end machines 
 * Better handling of corrupt CDG rips
 * Minor changes to make it more OSX-friendly
 * Added facility for cancelling song database builds in PyKaraoke GUI

Changes since v0.2:

 * Fixed colour cycling in the CDG player
 * Fixed transparent colours used in CDG files
 * Searches are optimised to handle thousands of CDG files very quickly
 * Fixed inaccurate right-clicking in the playlist on some systems
 * Fixed Windows drive icon
 * Fixed tree root issue on some Linux systems
 * Added more status messages to the status bars

Changes since v0.1:

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
