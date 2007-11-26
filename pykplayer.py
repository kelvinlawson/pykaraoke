#
# Copyright (C) 2007  Kelvin Lawson (kelvinl@users.sourceforge.net)
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

"""This module defines the class pykPlayer, which is a base class used
by the modules pykar.py, pycdg.py, and pympg.py.  This collects
together some common interfaces used by these different
implementations for different types of Karaoke files."""

from pykconstants import *
from pykmanager import manager
from pykenv import env
import pygame
import sys
import types
import os

class pykPlayer:
    def __init__(self, song, errorNotifyCallback = None, doneCallback = None,
                 windowTitle = None):
        """The first parameter, song, may be either a pykdb.SongStruct
        instance, or it may be a filename. """

        # Set the global command-line options if they have not already
        # been set.
        if manager.options == None:
            parser = self.SetupOptions()
            (manager.options, args) = parser.parse_args()

            if song is None:
                if (len(args) != 1):
                    parser.print_help()
                    sys.exit(2)
                song = args[0]

        if isinstance(song, types.StringTypes):
            # We were given a filename.  Convert it to a SongStruct.
            import pykdb
            song = pykdb.SongStruct(song)
        
        # Store the parameters
        self.Song = song
        self.WindowTitle = windowTitle

        # And look up the actual files corresponding to this SongStruct.
        self.SongDatas = song.GetSongDatas()
        if windowTitle is None:
            self.WindowTitle = song.DisplayFilename
            
        # Caller can register a callback by which we
        # print out error information, use stdout if none registered
        if errorNotifyCallback:
            self.ErrorNotifyCallback = errorNotifyCallback
        else:
            self.ErrorNotifyCallback = self.__defaultErrorPrint
    
        # Caller can register a callback by which we
        # let them know when the song is finished
        if doneCallback:
            self.SongFinishedCallback = doneCallback
        else:
            self.SongFinishedCallback = None

        self.State = STATE_INIT
        self.InternalOffsetTime = 0

        # These values are used to keep track of the current position
        # through the song based on pygame's get_ticks() interface.
        # It's used only when get_pos() cannot be used or is
        # unreliable for some reason.
        self.PlayTime = 0
        self.PlayStartTime = 0

        # self.PlayStartTime is valid while State == STATE_PLAYING; it
        # indicates the get_ticks() value at which the song started
        # (adjusted for any pause intervals that occurred during
        # play).  self.PlayTime is valid while State != STATE_PLAYING;
        # it indicates the total number of ticks (milliseconds) that
        # have elapsed in the song so far.

        # Set this true if the player can zoom font sizes.
        self.SupportsFontZoom = False

    # The following methods are part of the public API and intended to
    # be exported from this class.

    # Start the thread running. Blocks until the thread is started and
    # has finished initialising pygame.
    def Play(self):
        self.doPlay()
        self.PlayStartTime = pygame.time.get_ticks()
        self.State = STATE_PLAYING

    # Pause the song - Use Pause() again to unpause
    def Pause(self):
        if self.State == STATE_PLAYING:
            self.doPause()
            self.PlayTime = pygame.time.get_ticks() - self.PlayStartTime
            self.State = STATE_PAUSED
        elif self.State == STATE_PAUSED:
            self.doUnpause()
            self.PlayStartTime = pygame.time.get_ticks() - self.PlayTime
            self.State = STATE_PLAYING

    # Close the whole thing down
    def Close(self):
        self.State = STATE_CLOSING

    # you must call Play() to restart. Blocks until pygame is initialised
    def Rewind(self):
        self.doRewind()
        self.PlayTime = 0
        self.PlayStartTime = 0
        self.State = STATE_NOT_PLAYING

    # Stop the song and go back to the start. As you would
    # expect Stop to do on a CD player. Play() restarts from
    # the beginning
    def Stop(self):
        self.Rewind()
            
    # Get the song length (in seconds)
    def GetLength(self):
        ErrorString = "GetLength() not supported"
        self.ErrorNotifyCallback (ErrorString)
        return None

    # Get the current time (in milliseconds).
    def GetPos(self):
        if self.State == STATE_PLAYING:
            return pygame.time.get_ticks() - self.PlayStartTime
        else:
            return self.PlayTime

    def SetupOptions(self, usage = None):
        """ Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application. """

        if usage == None:
            usage = "%prog [options] <Karaoke file>"

        return manager.SetupOptions(usage)

    # Below methods are internal.

    def doPlay(self):
        pass

    def doPause(self): 
        pass

    def doUnpause(self):
        pass

    def doRewind(self):
        pass

    def doStuff(self):
        # Override this in a derived class to do some useful per-frame
        # activity.
        # Common handling code for a close request or if the
        # pygame window was quit
        if self.State == STATE_CLOSING:
            if manager.display:
                manager.display.fill((0,0,0))
                pygame.display.flip()
            self.shutdown()

    def doResize(self, newSize):
        # This will be called internally whenever the window is
        # resized for any reason, either due to an application resize
        # request being processed, or due to the user dragging the
        # window handles.
        pass

    def doResizeBegin(self):
        # This will be called internally before the screen is resized
        # by pykmanager and doResize() is called. Not all players need
        # to do anything here.
        pass

    def doResizeEnd(self):
        # This will be called internally after the screen is resized
        # by pykmanager and doResize() is called. Not all players need
        # to do anything here.
        pass

    def handleEvent(self, event):
        if event.type == pygame.USEREVENT:
            self.Close()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                self.Close()

            elif event.key == pygame.K_PAUSE:
                self.Pause()

            # Use left/right arrow to offset the current graphics time
            # by 1/4 sec.  Use the down arrow to restore them to sync.
            elif self.State == STATE_PLAYING and event.key == pygame.K_RIGHT:
                manager.UserOffsetTime += 250
            elif self.State == STATE_PLAYING and event.key == pygame.K_LEFT:
                manager.UserOffsetTime -= 250
            elif self.State == STATE_PLAYING and event.key == pygame.K_DOWN:
                manager.UserOffsetTime = 0

            if self.SupportsFontZoom:
                if event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS or \
                   event.key == pygame.K_KP_PLUS:
                    manager.ZoomFont(1.0/0.9)
                elif event.key == pygame.K_MINUS or event.key == pygame.K_UNDERSCORE or \
                   event.key == pygame.K_KP_MINUS:
                    manager.ZoomFont(0.9)

        elif event.type == pygame.QUIT:
            self.Close()
            
        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONDOWN:
            if event.button == GP2X_BUTTON_SELECT:
                self.Close()
            elif event.button == GP2X_BUTTON_START:
                self.Pause()

    def shutdown(self):
        # This will be called by the pykManager to shut down the thing
        # immediately.

        # If the caller gave us a callback, let them know we're finished
        if self.State != STATE_CLOSED:
            if self.SongFinishedCallback != None:
                self.SongFinishedCallback()
            self.State = STATE_CLOSED


    def __defaultErrorPrint(self, ErrorString):
        print (ErrorString)

