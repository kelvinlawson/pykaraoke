#!/usr/bin/env python 

# pympg - MPEG Karaoke Player
#
# Copyright (C) 2010  Kelvin Lawson (kelvinl@users.sourceforge.net)
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from pykconstants import *
from pykplayer import pykPlayer
from pykenv import env
from pykmanager import manager
import pygame, sys, os, string, subprocess
import threading

# OVERVIEW
#
# pympg is an MPEG player built using python. It was written for the
# PyKaraoke project but is in fact a general purpose MPEG player that
# could be used in other python projects requiring an MPEG player.
#
# The player uses the pygame library (www.pygame.org), and can therefore
# run on any operating system that runs pygame (currently Linux, Windows
# and OSX).
#
# You can use this file as a standalone player, or together with
# PyKaraoke. PyKaraoke provides a graphical user interface, playlists,
# searchable song database etc.
#
# For those writing a media player or similar project who would like
# MPG support, this module has been designed to be easily incorporated
# into such projects and is released under the LGPL.


# REQUIREMENTS
#
# pympg requires the following to be installed on your system:
# . Python (www.python.org)
# . Pygame (www.pygame.org)


# USAGE INSTRUCTIONS
#
# To start the player, pass the MPEG filename/path on the command line:
#       python pympg.py /songs/theboxer.mpg
#
# You can also incorporate a MPG player in your own projects by
# importing this module. The class mpgPlayer is exported by the
# module. You can import and start it as follows:
#   import pympg
#   player = pympg.mpgPlayer("/songs/theboxer.mpg")
#   player.Play()
# If you do this, you must also arrange to call pympg.manager.Poll()
# from time to time, at least every 100 milliseconds or so, to allow
# the player to do its work.
#
# The class also exports Close(), Pause(), Rewind(), GetPos().
#
# There are two optional parameters to the initialiser, errorNotifyCallback
# and doneCallback:
#
# errorNotifyCallback, if provided, will be used to print out any error
# messages (e.g. song file not found). This allows the module to fit 
# together well with GUI playlist managers by utilising the same GUI's
# error popup window mechanism (or similar). If no callback is provided,
# errors are printed to stdout. errorNotifyCallback should take one 
# parameter, the error string, e.g.:
#   def errorPopup (ErrorString):
#       msgBox (ErrorString)
#
# doneCallback can be used to register a callback so that the player
# calls you back when the song is finished playing. The callback should
# take no parameters, e.g.:
#   def songFinishedCallback():
#       msgBox ("Song is finished")
#
# To register callbacks, pass the functions in to the initialiser:
#   mpgPlayer ("/songs/theboxer.mpg", errorPopup, songFinishedCallback)
# These parameters are optional and default to None.
#
# If the initialiser fails (e.g. the song file is not present), __init__
# raises an exception.


# IMPLEMENTATION DETAILS
#
# pympg is implemented as a handful of python modules. Pygame provides
# all of the MPEG decoding and display capabilities, and can play an
# MPEG file with just a few lines of code. Hence this module is rather
# small. What it provides on top of the basic pygame features, is a
# player-like class interface with Play, Pause, Rewind etc. It also
# implements a resizable player window.  And, of course, it integrates
# nicely with pykaraoke.py and pykaraoke_mini.py.
#
# Previous implementations ran the player within a thread; this is no
# longer the case.  Instead, it is the caller's responsibility to call
# pycdg.manager.Poll() every once in a while to ensure that the player
# gets enough CPU time to do its work.  Ideally, this should be at
# least every 100 milliseconds or so to guarantee good video and audio
# response time.

# Display depth (bits)
DISPLAY_DEPTH       = 32 

# Check to see if the movie module is available.
try:
    import pygame.movie as movie
except ImportError:
    movie = None

# mpgPlayer Class
class mpgPlayer(pykPlayer):
    # Initialise the player instace
    def __init__(self, song, songDb, errorNotifyCallback=None, doneCallback=None):
        """The first parameter, song, may be either a pykdb.SongStruct
        instance, or it may be a filename. """

        pykPlayer.__init__(self, song, songDb, errorNotifyCallback, doneCallback)

        self.Movie = None

        manager.setCpuSpeed('mpg')

        manager.InitPlayer(self)
        manager.OpenDisplay(depth = DISPLAY_DEPTH)

        # Close the mixer while using Movie
        manager.CloseAudio()

        # Open the Movie module
        filepath = self.SongDatas[0].GetFilepath()
        if type(filepath) == unicode:
            filepath = filepath.encode(sys.getfilesystemencoding())
        self.Movie = pygame.movie.Movie(filepath)
        self.Movie.set_display(manager.display, (0, 0, manager.displaySize[0], manager.displaySize[1]))


    def doPlay(self):
        self.Movie.play()

    def doPause(self):
        self.Movie.pause()

    def doUnpause(self):
        self.Movie.play()

    def doRewind(self):
        self.Movie.stop()
        self.Movie.rewind()
            
    # Get the movie length (in seconds).
    def GetLength(self):
        return self.Movie.get_length()
        
    # Get the current time (in milliseconds).
    def GetPos(self):
        return (self.Movie.get_time() * 1000)

    def SetupOptions(self):
        """ Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application. """

        parser = pykPlayer.SetupOptions(self, usage = "%prog [options] <mpg filename>")

        # Remove irrelevant options.
        parser.remove_option('--font-scale')
        
        return parser

    def shutdown(self):
        # This will be called by the pykManager to shut down the thing
        # immediately.
        if self.Movie:
            self.Movie.stop()
        # Must remove the object before using pygame.mixer module again
        self.Movie = None
        pykPlayer.shutdown(self)

    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and (event.mod & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT | pygame.KMOD_LMETA | pygame.KMOD_RMETA)):
            # Shift/meta return: start/stop song.  Useful for keybinding apps.
            self.Close()
            return
        
        pykPlayer.handleEvent(self, event)

    # Internal. Only called by the pykManager.
    def doResize(self, newSize):
        # Resize the screen.
        self.Movie.set_display(manager.display, (0, 0, manager.displaySize[0], manager.displaySize[1]))

    # Internal. Only called by the pykManager.
    def doResizeBegin(self):
        # The Movie player must be paused while resizing otherwise we
        # get Xlib errors. pykmanager will call here before the resize
        # so that we can do it.
        if self.State == STATE_PLAYING:
            self.Movie.pause()

    # Internal. Only called by the pykManager.
    def doResizeEnd(self):
        # Called by pykmanager when resizing has finished.
        # We only play if it was playing in the first place.
        if self.State == STATE_PLAYING:
            self.Movie.play()

class externalPlayer(pykPlayer):

    """ This class is used to invoke an external command and wait for
    it to finish.  It is usually used to play a video file using an
    external player. """
    
    def __init__(self, song, songDb, errorNotifyCallback=None, doneCallback=None):
        """The first parameter, song, may be either a pykdb.SongStruct
        instance, or it may be a filename. """

        pykPlayer.__init__(self, song, songDb, errorNotifyCallback, doneCallback)

        self.Movie = None

        manager.setCpuSpeed('mpg')
        manager.InitPlayer(self)

        # Close the audio and the display
        manager.CloseAudio()
        manager.CloseDisplay()
        manager.CloseCPUControl()

        self.procReturnCode = None
        self.proc = None


    def doPlay(self):
        if self.procReturnCode != None:
            # The movie is done.
            self.__stop()

        if not self.proc:
            self.__start()

    def GetLength(self):
        # We cannot fetch the length from arbitrary external players.
        # Return zero-length.
        return 0

    def GetPos(self):
        # Use the default GetPos() which simply checks the time
        # since we started playing. This does not take account
        # for any fast-forward/rewind that may occur in the
        # external player, but we cannot support getting the
        # song position from arbitrary user-supplied players.
        return pykPlayer.GetPos(self)

    def doStuff(self):
        if self.procReturnCode != None:
            # The movie is done.
            self.__stop()
            self.Close()

        pykPlayer.doStuff(self)

    def __start(self):
        filepath = self.SongDatas[0].GetFilepath()

        external = manager.settings.MpgExternal
        if '%' in external:
            # Assume the filename parameter is embedded in the string.
            cmd = external % {
                'file' : filepath,
                }

        elif external:
            # No parameter appears to be present; assume the program
            # accepts the filename as the only parameter.
            cmd = [external, filepath]
            
        shell = True
        if env == ENV_WINDOWS:
            # Don't try to open the process under a "shell" in
            # Windows; that just breaks commands with spaces.
            shell = False

        assert self.procReturnCode == None
        sys.stdout.flush()
        self.proc = subprocess.Popen(cmd, shell = shell)
        if manager.settings.MpgExternalThreaded:
            # Wait for it to complete in a thread.
            self.thread = threading.Thread(target = self.__runThread)
            self.thread.start()
        else:
            # Don't wait for it in a thread; wait for it here.
            self.thread = None
            self.__runThread()

    def __stop(self):
        if self.thread:
            self.thread.join()
        self.proc = None
        self.procReturnCode = None
        self.thread = None
        

    def __runThread(self):
        """ This method runs in a sub-thread.  Its job is just to wait
        for the process to finish. """

        try:
            self.procReturnCode = self.proc.wait()
        except OSError:
            self.procReturnCode = -1
        
        

# Can be called from the command line with the MPG filepath as parameter
def main():
    player = mpgPlayer(None, None)
    player.Play()
    manager.WaitForPlayer()

if __name__ == "__main__":
    sys.exit(main())
    #import profile
    #result = profile.run('main()', 'pympg.prof')
    #sys.exit(result)
    
