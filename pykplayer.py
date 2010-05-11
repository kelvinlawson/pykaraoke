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
    def __init__(self, song, songDb,
                 errorNotifyCallback = None, doneCallback = None,
                 windowTitle = None):
        """The first parameter, song, may be either a pykdb.SongStruct
        instance, or it may be a filename. """

        if songDb == None:
            import pykdb
            songDb = pykdb.globalSongDB
            songDb.LoadSettings(None)
        self.songDb = songDb

        # Set the global command-line options if they have not already
        # been set.
        if manager.options == None:
            parser = self.SetupOptions()
            (manager.options, args) = parser.parse_args()
            manager.ApplyOptions(self.songDb)

            if song is None:
                if (len(args) != 1):
                    parser.print_help()
                    sys.exit(2)
                song = args[0]

        # Unfortunately, we can't capture sound when dumping.  There
        # are two reasons for this.  (1) pymedia doesn't currently
        # support multiplexing audio with a video stream, so when
        # you're dumping an mpeg file, it has to be video-only.  (2)
        # pygame doesn't provide a way for us to programmatically
        # convert a midi file to sound samples anyway--all you can do
        # with a midi file is route it through the speakers.

        # So, for these reasons, we always just disable sound when
        # dumping images or movies.
        if manager.options.dump:
            manager.options.nomusic = True

        if isinstance(song, types.StringTypes):
            # We were given a filename.  Convert it to a SongStruct.
            song = self.songDb.makeSongStruct(song)
        
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
        self.PlayFrame = 0

        # self.PlayStartTime is valid while State == STATE_PLAYING; it
        # indicates the get_ticks() value at which the song started
        # (adjusted for any pause intervals that occurred during
        # play).  self.PlayTime is valid while State != STATE_PLAYING;
        # it indicates the total number of ticks (milliseconds) that
        # have elapsed in the song so far.

        # self.PlayFrame starts at 0 and increments once for each
        # frame.  It's not very meaningful, except in STATE_CAPTURING
        # mode.

        # Keep track of the set of modifier buttons that are held
        # down.  This is currently used only for the GP2X interface.
        self.ShoulderLHeld = False
        self.ShoulderRHeld = False

        # Set this true if the player can zoom font sizes.
        self.SupportsFontZoom = False

    # The following methods are part of the public API and intended to
    # be exported from this class.

    def Validate(self):
        """ Returns True if the karaoke file appears to be playable
        and contains lyrics, or False otherwise. """

        return self.doValidate()

    def Play(self):
        self.doPlay()

        if manager.options.dump:
            self.setupDump()
        else:
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
        self.PlayFrame = 0
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

        return manager.SetupOptions(usage, self.songDb)

    # Below methods are internal.

    def setupDump(self):
        # Capture the output as a sequence of numbered frame images.
        self.PlayTime = 0
        self.PlayStartTime = 0
        self.PlayFrame = 0
        self.State = STATE_CAPTURING

        self.dumpFrameRate = manager.options.dump_fps
        assert self.dumpFrameRate

        filename = manager.options.dump
        base, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        self.dumpEncoder = None
        if ext_lower == '.mpg':
            # Use pymedia to convert frames to an mpeg2 stream
            # on-the-fly.
            import pymedia
            import pymedia.video.vcodec as vcodec

            self.dumpFile = open(filename, 'wb')
            frameRate = int(self.dumpFrameRate * 100 + 0.5)
            self.dumpFrameRate = float(frameRate) / 100.0
            
            params= { \
              'type': 0,
              'gop_size': 12,
              'frame_rate_base': 125,
              'max_b_frames': 0,
              'height': manager.options.size_y,
              'width': manager.options.size_x,
              'frame_rate': frameRate,
              'deinterlace': 0,
              'bitrate': 9800000,
              'id': vcodec.getCodecID('mpeg2video')
            }
            self.dumpEncoder = vcodec.Encoder( params )
            return
            
        # Don't dump a video file; dump a sequence of frames instead.
        self.dumpPPM = (ext_lower == '.ppm' or ext_lower == '.pnm')
        self.dumpAppend = False
        
        # Convert the filename to a pattern.
        if '#' in filename:
            hash = filename.index('#')
            end = hash
            while end < len(filename) and filename[end] == '#':
                end += 1
            count = end - hash
            filename = filename[:hash] + '%0' + str(count) + 'd' + filename[end:]
        else:
            # There's no hash in the filename.
            if self.dumpPPM:
                # We can dump a series of frames all to the same file,
                # if we're dumping ppm frames.  Mjpegtools likes this.
                self.dumpAppend = True
                try:
                    os.remove(filename)
                except OSError:
                    pass
            else:
                # Implicitly append a frame number.
                filename = base + '%04d' + ext
            
        self.dumpFilename = filename

    def doFrameDump(self):
        if self.dumpEncoder:
            import pymedia.video.vcodec as vcodec

            ss = pygame.image.tostring(manager.surface, "RGB")
            bmpFrame = vcodec.VFrame(
                vcodec.formats.PIX_FMT_RGB24,
                manager.surface.get_size(), (ss,None,None))
            yuvFrame = bmpFrame.convert(vcodec.formats.PIX_FMT_YUV420P)
            d = self.dumpEncoder.encode(yuvFrame)
            self.dumpFile.write(d.data)
            return

        if self.dumpAppend:
            filename = self.dumpFilename
        else:
            filename = self.dumpFilename % self.PlayFrame
            print filename

        if self.dumpPPM:
            # Dump a PPM file.  We do PPM by hand since pygame
            # doesn't support it directly, but it's so easy and
            # useful.
            
            w, h = manager.surface.get_size()
            if self.dumpAppend:
                f = open(filename, 'ab')
            else:
                f = open(filename, 'wb')
            f.write('P6\n%s %s 255\n' % (w, h))
            f.write(pygame.image.tostring(manager.surface, 'RGB'))

        else:
            # Ask pygame to dump the file.  We trust that pygame knows
            # how to store an image in the requested format.
            pygame.image.save(manager.surface, filename)
            

    def doValidate(self):
        return True
    
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

        elif self.State == STATE_CAPTURING:
            # We are capturing a video file.
            self.doFrameDump()

            # Set the frame time for the next frame.
            self.PlayTime = 1000.0 * self.PlayFrame / self.dumpFrameRate
            
        self.PlayFrame += 1
        

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
            if event.key == pygame.K_ESCAPE:
                self.Close()

            elif event.key == pygame.K_PAUSE or event.key == pygame.K_p:
                self.Pause()

            elif event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE:
                self.Rewind()
                self.Play()

            # Use control-left/right arrow to offset the current
            # graphics time by 1/4 sec.  Use control-down arrow to
            # restore them to sync.
            elif self.State == STATE_PLAYING and event.key == pygame.K_RIGHT and event.mod & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL):
                manager.settings.SyncDelayMs += 250
                print "sync %s" % manager.settings.SyncDelayMs
            elif self.State == STATE_PLAYING and event.key == pygame.K_LEFT and event.mod & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL):
                manager.settings.SyncDelayMs -= 250
                print "sync %s" % manager.settings.SyncDelayMs
            elif self.State == STATE_PLAYING and event.key == pygame.K_DOWN and event.mod & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL):
                manager.settings.SyncDelayMs = 0
                print "sync %s" % manager.settings.SyncDelayMs

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
            elif event.button == GP2X_BUTTON_L:
                self.ShoulderLHeld = True
            elif event.button == GP2X_BUTTON_R:
                self.ShoulderRHeld = True

            if self.SupportsFontZoom:
                if event.button == GP2X_BUTTON_RIGHT and self.ShoulderLHeld:
                    manager.ZoomFont(1.0/0.9)
                elif event.button == GP2X_BUTTON_LEFT and self.ShoulderLHeld:
                    manager.ZoomFont(0.9)
            
        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONUP:
            if event.button == GP2X_BUTTON_L:
                self.ShoulderLHeld = False
            elif event.button == GP2X_BUTTON_R:
                self.ShoulderRHeld = False

    def shutdown(self):
        # This will be called by the pykManager to shut down the thing
        # immediately.

        # If the caller gave us a callback, let them know we're finished
        if self.State != STATE_CLOSED:
            self.State = STATE_CLOSED
            if self.SongFinishedCallback != None:
                self.SongFinishedCallback()


    def __defaultErrorPrint(self, ErrorString):
        print (ErrorString)


    def findPygameFont(self, fontData, fontSize):
        """ Returns a pygame.Font selected by this data. """
        if not fontData.size:
            # The font names a specific filename.
            filename = fontData.name
            if os.path.sep not in filename:
                filename = os.path.join(manager.FontPath, filename)
            return pygame.font.Font(filename, fontSize)

        # The font names a system font.
        pointSize = int(fontData.size * fontSize / 10.0 + 0.5)
        return pygame.font.SysFont(
            fontData.name, pointSize, bold = fontData.bold,
            italic = fontData.italic)
