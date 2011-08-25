
---------------------------------------------------------------------------

Release:      pykaraoke v0.7.5
Date:         26/08/2011
Author:       Kelvin Lawson <kelvinl@users.sourceforge.net>
License:      LGPL
Website:      http://www.kibosh.org/pykaraoke/
Contributors: John Schneiderman <JohnMS@member.fsf.org>
              William Ferrell <willfe@gmail.com>
              David Rose <pykar@ddrose.com>

---------------------------------------------------------------------------

INTRODUCTION

PyKaraoke is a karaoke player for Linux, FreeBSD, Windows and GP2X.

The following song formats are supported:
 * CDG (MP3+G, OGG+G)
 * MIDI/KAR
 * MPEG/AVI/Other video formats

MPEG2 files can usually be played directly within the PyKaraoke
framework.  Other file formats like AVI or QuickTime, or files which
use more exotic codecs like XviD, can also be handled by PyKaraoke,
but it will require an external program, such as mplayer or Windows
Media Player to show them.  This is a little less tightly integrated,
but it does work, and allows you to pick all your karaoke songs from
one database.

No song files are provided - this package provides you with the player
needed to play your own karaoke song files.

---------------------------------------------------------------------------

INSTALLATION (LINUX, SOURCE INSTALLS)

PyKaraoke requires the following libraries to be installed:

 * Python (www.python.org)
 * Pygame (www.pygame.org)
 * WxPython (www.wxpython.org)
 * SDL source distribution (www.libsdl.org)

Optional libraries are as follows:

 * Mutagen (http://code.google.com/p/mutagen/)
 * PyMedia - Only required for converting CDG/KAR to MPG

PyKaraoke now offers two builds: an ultra-portable Python version, and
a highly optimised C version. The default install is to use the faster
C version which requires the SDL source distribution for compilation
purposes. All supported platforms should support compilation of the C
version, but the portable Python-only version will continue to be
supported. Python-only installs do not require the SDL source
distribution, and instead require the NumPy Python module
(numpy.scipy.org).

If these libraries are not already installed on your system, you can
download them from the websites listed.

Linux users may find these packages are available directly from their
distro's package manager. For example Debian users can install all
prerequisites using:
	# apt-get install python-dev python-pygame libwxgtk-python 
                  libsdl-dev python-mutagen

With the prerequisites installed, unzip the release and run the following
as root:

	# python setup.py install

This installs the executables into /usr/bin, and you can then run
PyKaraoke from anywhere using "pykaraoke".

Alternatively you can run PyKaraoke without installing by simply
unzipping and running "python pykaraoke.py" from the unzip location.
Beware that the uninstalled version method requires the NumPy (or the
older Numeric) library, and runs the more portable but slower
Python-only version of the CDG player.

---------------------------------------------------------------------------

INSTALLATION (OS X)

PyKaraoke is known to work well on Macintosh OS X.  It has been tested
on OS X versions 10.3, 10.4, and 10.5.  On this platform, you must
install from source, similar to the Linux platforms, as described
above, since we do not presently provide a binary OS X installation.

Unfortunately, there are several supporting packages you must install
first in order to run PyKaraoke on OS X.

The biggest troublemaker in the mix is Pygame.  Pygame is available
via fink, MacPorts, and via precompiled versions.  If you are already
familiar with using fink or MacPorts, you may find one of these the
easiest way to install it.  However, we will leave this as your own
exercise; we describe below the process of installing it via the
precompiled version.

Unfortunately, installing the precompiled version of Pygame also
requires installing the latest version of Python from python.org,
instead of relying on the version of Python that comes pre-installed
with OS X.  This means you must visit:

http://www.pygame.org/download.shtml

  Follow the link for "Pygame OSX PackageManager Site".  Verify the
  version of Python that the binaries here are compiled for.  At the
  time of this writing, this was python version 2.5.

http://www.python.org/download/

  Follow the link for "Python 2.5.2 for Macintosh OS X", or whatever
  the version requested by pygame.org.  Note that the minor version
  (the final .2 in this example) doesn't matter; just get whichever
  minor version is offered that matches the major version required by
  pygame.org.

http://www.pygame.org/download.shtml

  Once you have installed the proper version of Python, go back to
  this site and install both pygame and pyobjc.

http://www.wxpython.org/

  Even though wxPython was already installed for your system default
  version of Python, you must now install a new version of wxPython to
  go with the custom version of Python you just installed.  Scroll
  down to "OS X Binaries" and install the latest version of wxPython
  runtime under the version of Python that you installed (e.g. under
  the Python 2.5 column).  We recommend picking the osx-unicode
  version, though this doesn't really matter much.

That will be all you need to install in order to play .kar files.  In
order to play .cdg files as well, you will also need to install the
NumPy package:

http://www.scipy.org/Download


Now you have everything installed that you need in order to play .kar
and .cdg files.  In order to launch PyKaraoke, open a terminal window
and type the command:

/Library/Frameworks/Python.framework/Versions/Current/bin/pythonw pykaraoke.py

You can use Platypus ( http://www.sveinbjorn.org/platypus ) to hide
this ugly command inside a convenient application icon, so you don't
have to type it every time.  For now, just type the command exactly as
shown above.  This accesses the version of Python that you have just
installed, as opposed to the version that is already pre-installed
with OS X.

Test everything that you have installed.  If your CPU is fast enough
(iMacs seem to do just fine), it will be able to play CDG files
smoothly using the native Python version, without requiring you to
build the optimised C version.  If, on the other hand, you observe a
lot of stuttering or sluggish graphic updates while playing CDG files,
then you will need to go a little bit further to compile the C
version.  This will require installing the XCode development suite,
and the SDL header files that match the version of SDL installed
automatically by pygame, above.  The details of this process are out
of the scope of this installation guide.

If you wish to play .avi files, .mov files, or .mpg files via an
external player, you will need to install a player that can be
launched via the command line, and which exits automatically when the
video is finished.  One such application is mplayer, which you can
install via MacPorts or fink.  There is also a precompiled version
available.  This is again beyond the scope of this installation guide.

---------------------------------------------------------------------------

INSTALLATION (WINDOWS)

Windows users can install PyKaraoke by simply downloading and running the
installer executable. This installs all prerequisite libraries, and adds
icons in your start menu to run PyKaraoke.

If you prefer, you may choose to build the Windows version from source. We
will assume you are familiar with the steps involved for installing a
Python distribution from source on Windows; they are similar to those for
the Linux installation, below. You will need to have pygame
(www.pygame.org) and wxpython (www.wxpython.org) installed. You will also
need to download and unpack the SDL source distribution (www.libsdl.org)
into the same directory with PyKaraoke, under its default name, which will
be something like "SDL-1.2.11" (by default, setup.py will search for any
directories named SDL* in the current directory). You will then invoke the
command:

python setup.py install

You may also choose to unpack the source distribution elsewhere and
specify its path with --sdl-location=/path/to/SDL on the above command.

---------------------------------------------------------------------------

CREATING WINDOWS INSTALLERS

To build a Windows installer, you additionally need to have py2exe
(www.py2exe.org) and NSIS (nsis.sourceforge.net) installed, and then you
may invoke:

python setup.py nsis

This will create an executable called pykaraoke-<current_version>.exe
in the current directory, which will be a standalone Windows installer
program you may then distribute to other Windows users. You don't
need to install PyKaraoke before building an installer for it.

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

INSTALLATION (GP2X)

PyKaraoke can run on the GP2X handheld console, giving you a Karaoke
machine that fits in your pocket. You may find it easiest simply to
install the prebuilt binary version. The prebuilt version already
includes Python and the necessary supporting libraries. Simply unpack
this archive onto your SD card; it will expand to a small hierarchy of
files.  One of these directory names is pykaraoke/songs, which will be
empty; you should put your song files in this pykaraoke/songs
directory (or in any nested directory structure within
pykaraoke/songs). The first time you install, and each time you add
new song files to this directory, you should run the "rescan_songs"
script to rebuild the database with the new song files; but most of
the time, you should start PyKaraoke simply by running the script
named "pykaraoke".

As of PyKaraoke version 0.6, you can also play video karaoke files on
your GP2X.  You should use your existing GP2X tools to convert these
to AVI format, as supported by the GP2X version of mplayer, and put
them under the songs directory with your other karaoke files.
PyKaraoke will index them and present them along with all of your
other songs.

COMPILATION (GP2X)

If, for some reason, you wish to build your own version for the GP2X,
this is possible, but there will be a bit of work involved.  You will
need to install the GP2X development kit, which includes a
cross-compiler for the GP2X. You should next use this cross-compiler
to build and install SDL and PyGame, so that you have the appropriate
source headers and matching binaries for these library. Note it may be
necessary for you to apply patches to SDL_mixer to support using
tremor and libmad, which are alternative libraries used for playing
OGG and MP3 files, respectively.  (The default OGG and MP3
implementations used by SDL_mixer make heavy use of floating-point
arithmetic, which does not perform well on the GP2X.)  You will also
need to patch the timidity/config.h file to reduce the MIDI rendering
demands on the CPU. All of these patches are available for download
elsewhere.

To play AVI files, you will need a version of mplayer that accepts the
movie file on the command line (the default version supplied with the
GP2X firmware ignores the command-line arguments and always presents a
file-navigation GUI).  Use svn to obtain GPH's version of the mplayer
source code from:

http://svn.gp2x.com/gp2x/tag/application/2006.07.05/mplayer/

And then apply the patches given within this source archive in
install/mplayer-gp2x-cmdline-pykaraoke.diff .  This file combines the
patches available from the wiki at http://wiki.gp2x.org/wiki/MPlayer ,
but also adds a few fixes of my own (to fix relative avi files, and
also to automatically exit the player when the song has finished).

Once all that is done, you need to use the cross compiler to build
_pycdgAux.so. A sample script called cross-build-gp2x.sh is provided to do
this. Then it is simply a matter of copying this file, along with all of
the .py files, to the GP2X.

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
is also used for displaying the lyrics of the Karaoke songs. It is
specifically designed to be a useful interface with a minimal input
device, for instance with a joystick or a remote control, for those
environments when you don't have convenient access to a full keyboard and
mouse. It is the default interface on the GP2X handheld.

The pykaraoke_mini interface presents a scrolling window that lists all of
the songs in your database in alphabetical order by filename (but you can
also sort them by song title or artist name; see TITLES AND ARTIST NAMES
below).

You can easily navigate through this list with the up and down arrow keys,
and press enter to select a song.  If you hold down the arrow keys, the
highlight gradually accelerates until it is moving quite fast, so it
doesn't take long to navigate through even a very large list. You can also
use the PageUp and PageDown keys to move a screen's worth at a time.

By default, the font is quite large, chosen to be easily visible on a
Karaoke monitor across the room. You can change the font size at run time
(for instance, to make more text appear on the page) by pressing the - and
+ keys.  This also affects the size of the font chosen for the lyrics if
you select a .kar file.

There is no search function in the mini player; the list always includes
the entire database (but you can type a few letters to go straight to the
song that begins with that string). There is also no playlist feature; you
must pick each song and play it one at a time.

The mini player uses the same database as the full-featured player, so
you may need to launch the full player from time to time to re-scan the
song database or update the directory list. Alternatively, you can use the
command-line interface to do this:

pykaraoke_mini --set_scan_dir=/my/song/directory

   Removes any directories you had already set, and adds
   /my/song/directory as the only song directory.

pykaraoke_mini --add_scan_dir=/my/other/song/directory

   Adds /my/other/song/directory to the list of directories to scan.
   This option may be repeated.

pykaraoke_mini --scan

   Actually rescans all of the recorded directories into the database.


Keys available in the mini version:

Escape                   Exit the program
Enter (Return)           Play the current song
Tab                      Change the sort order: artist, title, filename
F1                       Mark the song for later editing (see below)
Up/Down                  Advance the highlight one line
Page Up/Page Down        Advance the highlight one page
+/-                      Change the font size

On the GP2X:

Y                        Exit the program
X, B, Start              Play the current song
A                        Change the sort order: artist, title, filename
Joystick click           Mark the song for later editing (see below)
Up/Down                  Advance the highlight one line
ShoulderRight+Up,Down    Advance the highlight one page
ShoulderRight+Left,Right Change the font size


Marking a Song

The full PyKaraoke version allows you to edit song titles or artists
on-the-fly, which is very useful when you discover an error in the
field.  The mini version does not support this editing.  However, you
can "mark" a song with the F1 key (Or a click in on the joystick on
the GP2X), which is intended to serve as a helpful reminder to you to
go back and edit the song later.  You can find the list of marked
songs listed in the filename marked.txt, which is stored in the
PyKaraoke datafiles directory (e.g., ~/.pykaraoke on Linux).


---------------------------------------------------------------------------

GP2X USAGE

On the GP2X you will run PyKaraoke with the pykaraoke_mini interface
(see above). This interface presents your song files in a long
list.

While viewing this list, use the joystick up and down to navigate to a
song, or hold it down to scroll very rapidly. Hold down the right
shoulder buttons while you move the joystick up and down to move a
page at a time.  Press the joystick left or right to jump quickly to
the next letter.

Press B or X to select a song, and Y to exit. If you have supplied
song titles and artist names with a titles.txt file (see below), you
can change the sort order of the list with the A button.

To change the font size both for the index and for .kar files, hold
down the left shoulder button while you push the joystick left or
right.

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

The file need not strictly be named titles.txt.  In general, it may be
named anything that *ends* with titles.txt, for instance,
cdg_titles.txt or MySubDirtitles.txt.  You may include multiple of
these *titles.txt files scattered throughout your song directories;
each one should reference song filenames relative to itself.  It may
be simplest just to put each *titles.txt in the same directory with
the song files it describes, though it is also possible to put it in a
parent directory.

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

CONVERTING CDG/KAR TO MPEG

It is possible to use PyKaraoke to convert CDG files to MPEG files.
They can then be burned to DVD-R or Video CD, for playback on standard
DVD players.

Although it is not trivial to do this, it is not really difficult
either.  Depending on your libraries installed, PyKaraoke can either
write a series of numbered frame images, or a single video-only MPEG
file; you must then use additional software to convert this to the
final output form including audio.  On Linux, we recommend mjpegtools
for this.

This kind of conversion can only be done via the command-line
interface.  Use the --dump and/or --dump-fps command-line options, for
instance:

python pycdg.py --dump=frame_####.png --dump-fps=29.97 songfilename.cdg

The above command will generate a sequence of numbered images, one for
each frame of the video, with the filenames frame_0000.png,
frame_0001.png, frame_0002.png, and so on.  It is then your
responsibility to use external software to assemble these frames
together into an MPEG file, along with the audio track.

The parameter to --dump is the filename pattern of each frame image.
A sequence of hash marks (#) is replaced with the frame number.  The
filename extension you specify determines the type of image file
written; the supported file extensions include .ppm, .png, .bmp, and
.tga.  If you use the .ppm extension, you may omit the hash marks; in
this case, the frames are all appended together into the same file.

The parameter to --dump-fps specifies the number of frames per second
that are written.  NTSC video uses 29.97 frames per second, while PAL
uses 25 frames per second.  Whichever frame rate you request, you
should specify the same value to the software you use when you
assemble the frames into an MPEG file, to ensure the timing remains in
sync.

If you have the pymedia library installed, PyKaraoke can use it to
generate an MPEG video file directly.  However, due to limitations in
the currently available version of pymedia, it cannot include the
audio--the generated MPEG file will be silent, and you must multiplex
the audio in separately (mjpegtools can do this easily).

To write out an MPEG file, omit the hash marks and specify a filename
that ends in the extension .mpg, for instance:

python pycdg.py --dump=movie.mpg --dump-fps=29.97 songfilename.cdg

When converting CDG files, you might also wish to specify --zoom=soft
to give the best possible quality for the resulting output.  Or you
might choose to specify --zoom=none with a window size of 288x192
(e.g. --width=288 --height=192) and then scale the images to the
appropriate video size using external software.


It is also possible to convert KAR files to a numbered image sequence,
or to MPEG, in a similar way:

python pykar.py --dump=frame_####.png --dump-fps=29.97 songfilename.kar

Once again, the output from PyKaraoke will lack audio, which you must
multiplex in separately.  In order to multiplex the MIDI audio, you
will need to convert the MIDI file to WAV, for instance via timidity.

THE CDG2MPG SCRIPT

There is a script, cdg2mpg, available within the PyKaraoke source
distribution, and automatically installed by the Linux distribution.
On Linux, if you have mjpegtools installed, it can be used to
automatically convert an entire directory of cdg+wav files to mpg
format, using the NTSC convention.  Consider it a sample script that
you may need to modify to suit your particular needs.  For instance,
feel free to modify the script to support kar, cdg+mp3, or cdg+ogg, or
to generate PAL or VCD format output.

---------------------------------------------------------------------------

THE SETTINGS.DAT FILE

When you use the configure dialog to customize your settings and
preferences, the settings you choose are saved in the file
settings.dat, in the PyKaraoke database directory (the particular
directory name varies according to the platform).  For the most part,
you don't need to worry about the contents of this file, since it's
more convenient to change it via the configure dialog.

However, there may be occasions that you need to edit it directly.
For instance, on the GP2X, there is no configure dialog available.  In
order to edit the settings.dat file on the GP2X, therefore, you can
either (a) copy your settings.dat to a PC-based version of PyKaraoke,
and run the configure dialog there, then copy it back, or (b) simply
hand-edit the settings.dat file to your liking.  Some of the
GP2X-specific settings, such as CPU speed controls, can only be
changed by hand-editing the settings.dat file.

There may not be a settings.dat file at all until the first time you
run PyKaraoke.  At that time, a default settings.dat file is created.

The most interesting settings that you might want to change on the
GP2X are:

MIDISampleRate = 11025

    This is the sample rate, in Hz, of the synthesized music generated
    for .kar files.  Since this is CPU-intensive, you may need to
    tweak this setting down somewhat if you are experience many clicks
    and pops when you are playing .kar files.  You can also tweak it
    down to allow you to set the CPU speed, below, lower (thus saving
    battery power).  On the other hand, you can increase it to improve
    the overall sound quality of your MIDI music.

CPUSpeed_startup = 240
CPUSpeed_menu_idle = 33
CPUSpeed_menu_slow = 100
CPUSpeed_menu_fast = 240
CPUSpeed_load = 240
CPUSpeed_cdg = 200
CPUSpeed_kar = 240
CPUSpeed_mpg = 200

    This configures the CPU speed setting during various operation
    modes.  Set the number higher to improve performance (decrease
    audio pops), or lower to improve battery life.  In theory, 240 is
    the highest safe number, though you can try to push it higher if
    you want to try overclocking your CPU.

    The operation modes are:

      startup - initial loading, from splash screen to first display
        of the song list, including scan if running rescan_songs.
      menu_idle - when the menu screen has been idle for more than 20
        seconds.
      menu_slow - when the user is slowly scrolling the menu screen.
      menu_fast - when the user is rapidly scrolling the menu screen.
      load - after selecting a song, but before it starts to play.
      cdg, kar, mpg - while playing a song of the indicated type.

KarEncoding = 'cp1252'
KarFont = FontData("DejaVuSans.ttf")
KarBackgroundColour = (0, 0, 0)
KarReadyColour = (255, 50, 50)
KarSweepColour = (255, 255, 255)
KarInfoColour = (0, 0, 200)
KarTitleColour = (100, 100, 255)

    These control the appearance of the text for .kar files.  You can
    change the encoding, font, and colours of the text during
    playback.

For the complete list of configurable options, see the source code of
pykdb.py, in the definition of the SettingsStruct class.

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


LINUX: NO AVAILABLE AUDIO DEVICE

Linux users may get the following error message:

    pygame.error: No available audio device

You should try switching between libsdl-oss and libsdl-alsa.


AMD64 INSTALLATIONS

If you are running on the AMD64 platform (and possibly others) you may see
this error on startup:

Exception in thread Thread-1:
Traceback (most recent call last):
	...
ValueError: unsupported datatype for array

If this occurs, you need to download and install the latest development
release of pygame. Follow the instructions at http://pygame.org/cvs.html to
obtain the latest development release, then:

1. Build the new release by running:
   # python makeref.py
   # python setup.py install --prefix=/path/to/temporary/spot
2. Find the directory named "pygame" within /path/to/temporary/spot/lib (on a
   development machine, the path was lib/python2.4/site-packages/pygame) and
   copy or move it (all of it, including the directory itself) into the
   folder containing pycdg.py and the rest of the PyKaraoke files.

The CDG player should then work properly.


SLACKWARE AND TIMIDITY++

Slackware users may find that the MIDI player cannot find the timidity
configuration files. You can fix this by creating a link from the PyKaraoke
installation directory:

    # cd pykaraoke_install_dir
    # ln -s /usr/share/timidity/timidity.cfg .
    # ln -s /usr/share/timidity/instruments


GP2X: ZIP ARCHIVES

When you store your Karaoke files within a zip archive, PyKaraoke has
to unpack them to a temporary file in order to play them. This all
happens transparently; normally, PyKaraoke will unpack them within the
/tmp directory.

However, on the GP2X the /tmp directory is mounted as a 5MB Ramdisk. This
is good, because it's very fast; but it means you can't unpack a file
larger than about 5MB. Many mp3 and ogg files are smaller than 5MB, but
depending on the bitrate you used to encode them, you may also have some
that are larger than this. This means you cannot play these large song
files on your GP2X if they are stored within a zip file.

There are several possible workarounds to this.

(1) Reconfigure your GP2X to make the size of the /tmp directory
    larger. We don't recommend doing this.

(2) Reencode all of your mp3 or ogg files so that they are smaller
    than 5MB.  This is certainly a fine option; you will lose a bit of
    quality, but probably not much.

(3) Uncomment the indicated lines in pykaraoke.gpe to configure
    PyKaraoke to store temporary files on the SD card instead. This,
    however, will be much slower; and it does require that you keep a
    certain amount of space available on your SD card.

(4) Don't store your mp3 and ogg files in a zip file. Just store the
    cdg files there, if you want to use zip files at all, but leave
    the mp3 files in the directory, next to the zip file--PyKaraoke
    can still find them there. You won't get any compression benefit
    from storing the mp3 or ogg files in a zip file, anyway. If you
    are using zip files for organisation, use a subdirectory instead.

We recommend approach (4).


GP2X: MIDI ISSUES (dropped notes, or stuttering / slow playback)

The GP2X has no hardware to perform MIDI synthesis, so it must perform
this work on the CPU (it uses the Timidity software MIDI player to do
this). Unfortunately, Timidity requires lots of floating-point
calculations, and the GP2X also lacks hardware to perform
floating-point arithmetic, so this kind of work is hard for the GP2X
to do. Consequently, MIDI playback requires a lot of CPU power.

The default parameters that ship with PyKaraoke are sufficient to play
most MIDI karaoke files acceptably well. You may, however, come across
the occasional MIDI file that gives the GP2X a hard time. There are
two different kinds of problems: you may get stuttering or slow
playback if the song or its patches are too complex, or you may get
omitted notes if the song uses too many simultaneous voices.

For stuttering playback, you can try editing your settings file to
increase the CPU speed reserved for playing kar files, as described
above.  Edit your settings.dat file and change the line:

CPUSpeed_kar = 240

To some higher value, such as 260 or higher.

For dropped notes, you will need to edit the troublesome MIDI file
with a MIDI editor program (there are many free programs available) to
simplify it.  Remove some of the filler notes in complex chords, or
remove some unneeded background instruments, to bring the total
polyphony count to 16 or lower (this is the maximum number of notes
that PyKaraoke's Timidity library is configured to play simultaneously
on the GP2X).

Alternatively, for either problem you can:

(1) Use PyKaraoke (on your PC) to convert your troublesome .kar files
to AVI format. See CONVERTING CDG/KAR TO MPEG, above. The new
AVI files will be a *lot* bigger than the original KAR files, but
they should play without popping.

or

(2) Use some other third-party software to convert your troublesome
.kar files to CDG+MP3 format. These will not be nearly as large
as AVI files (though still larger than the original KAR), and they
will be easier for PyKaraoke to play. However, there don't appear
to be any free tools that will make this conversion. Prepare to
spend some money.

---------------------------------------------------------------------------

SUGGESTIONS

Please let us know if there are any features you would like to see added,
or you have any other suggestions or bug reports. Contact the project at
<kelvinl@users.sourceforge.net>

---------------------------------------------------------------------------
