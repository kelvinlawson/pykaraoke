#!/usr/bin/env python 

# pympg - MPEG Karaoke Player
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

""" This module provides the client implementation for PyKaraoke
remote communications.  This is intended to be used as a mix-in class
(for instance, for pykaraoke) to add functionality to control the
PyKaraoke window on some other machine.

This "client" implementation provides the master functionality: the
client will request songs the the "server" will play. """

from pykconstants import *
from pykplayer import pykPlayer
from pykenv import env
from pykmanager import manager
import pygame, sys, os, string, subprocess
import threading
import socket
import threading
import struct
import cPickle

# Display depth (bits)
DISPLAY_DEPTH       = 32 

class remotePlayer(pykPlayer):
    # Initialise the player instance
    def __init__(self, song, songDb, errorNotifyCallback=None, doneCallback=None):
        """The first parameter, song, may be either a pykdb.SongStruct
        instance, or it may be a filename. """

        pykPlayer.__init__(self, song, songDb, errorNotifyCallback, doneCallback)

        self.pos = 0
        self.length = 0
        
        manager.InitPlayer(self)
        manager.OpenDisplay(depth = DISPLAY_DEPTH)

        # Close the mixer, we don't need audio.
        manager.CloseAudio()

        winWidth, winHeight = manager.displaySize
        pygame.font.init()
        fontSize = int(1.5 * manager.GetFontScale() * winHeight / 24)
        self.textFont = pygame.font.Font(os.path.join(manager.FontPath, "DejaVuSansCondensed.ttf"), fontSize)
        self.textHeight = self.textFont.get_linesize()

        settings = self.songDb.Settings
        manager.surface.fill(settings.KarBackgroundColour)

        self.displayStatus('Queued')

    def displayStatus(self, status):
        self.status = status

        if not manager.surface:
            manager.OpenDisplay()
        
        winWidth, winHeight = manager.displaySize
        winCenter = winWidth / 2

        message = '%s\n%s\n%s\non %s' % (
            self.status, self.Song.Title, self.Song.Artist,
            manager.options.remote_server)

        lines = manager.WordWrapText(message, self.textFont, winWidth - X_BORDER * 2)

        settings = self.songDb.Settings
        manager.surface.fill(settings.KarBackgroundColour)

        row = (winHeight - len(lines) * self.textHeight) / 2
        for line in lines:
            line = line.strip()
            text = self.textFont.render(line, True, settings.KarTitleColour,
                                        settings.KarBackgroundColour)
            rect = text.get_rect()
            rect = rect.move(winCenter - rect.centerx, row)
            manager.display.blit(text, rect)
            row += self.textHeight

        pygame.display.flip()

    def doPlay(self):
        if not manager.sendRemoteCommand('play', self.Song):
            self.displayStatus('Failed')

    def doClose(self):
        manager.sendRemoteCommand('close', self.Song)

    def doPause(self):
        pass

    def doUnpause(self):
        pass

    def doRewind(self):
        pass

    def doStuff(self):
        pykPlayer.doStuff(self)
        
        while manager.serverCommands:
            command, args = manager.serverCommands[0]
            del manager.serverCommands[0]

            if command == 'doPlay':
                # Started playing.
                self.displayStatus('Playing')

            elif command == 'doClose':
                # Stopped playing.
                self.Close()
                return

            elif command == 'setPos':
                self.pos, self.length = args

            else:
                print "unhandled command %s" % (repr(command))
            
    # Get the movie length (in seconds).
    def GetLength(self):
        return self.length
        
    # Get the current time (in milliseconds).
    def GetPos(self):
        return self.pos

    def shutdown(self):
        # This will be called by the pykManager to shut down the thing
        # immediately.
        manager.sendRemoteCommand('close', self.Song)
        pykPlayer.shutdown(self)
        

# Can be called from the command line with the filepath as parameter
def main():
    player = remotePlayer(None, None)
    player.Play()
    manager.WaitForPlayer()

if __name__ == "__main__":
    sys.exit(main())
    
