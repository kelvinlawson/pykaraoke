#******************************************************************************
#****                                                                      ****
#**** Copyright (C) 2010  Kelvin Lawson (kelvinl@users.sourceforge.net)    ****
#**** Copyright (C) 2010  PyKaraoke Development Team                       ****
#****                                                                      ****
#**** This library is free software; you can redistribute it and/or        ****
#**** modify it under the terms of the GNU Lesser General Public           ****
#**** License as published by the Free Software Foundation; either         ****
#**** version 2.1 of the License, or (at your option) any later version.   ****
#****                                                                      ****
#**** This library is distributed in the hope that it will be useful,      ****
#**** but WITHOUT ANY WARRANTY; without even the implied warranty of       ****
#**** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU    ****
#**** Lesser General Public License for more details.                      ****
#****                                                                      ****
#**** You should have received a copy of the GNU Lesser General Public     ****
#**** License along with this library; if not, write to the                ****
#**** Free Software Foundation, Inc.                                       ****
#**** 59 Temple Place, Suite 330                                           ****
#**** Boston, MA  02111-1307  USA                                          ****
#******************************************************************************

from pykconstants import *
from pykenv import env
import pykversion
import pygame
import os
import sys

# Python 2.3 and newer ship with optparse; older Python releases need "Optik"
# installed (optik.sourceforge.net)
try:
    import optparse
except:
    import Optik as optparse

if env == ENV_GP2X:
    import _cpuctrl as cpuctrl

class pykManager:

    """ There is only one instance of this class in existence during
    program execution, and it is never destructed until program
    termination.  This class manages the pygame interface, keeping
    interfaces open or closed as necessary; it also provides callbacks
    into handling pygame events. """

    def __init__(self):
        self.initialized = False
        self.player = None
        self.options = None
        self.display = None
        self.surface = None
        self.audioProps = None

        self.displaySize = None
        self.displayFlags = 0
        self.displayDepth = 0
        self.cpuSpeed = None

        # Find the correct font path. If fully installed on Linux this
        # will be sys.prefix/share/pykaraoke/fonts. Otherwise look for
        # it in the current directory.
        if (os.path.isfile("fonts/DejaVuSans.ttf")):
            self.FontPath = "fonts"
            self.IconPath = "icons"
        else:
            self.FontPath = os.path.join(sys.prefix, "share/pykaraoke/fonts")
            self.IconPath = os.path.join(sys.prefix, "share/pykaraoke/icons")

        if env == ENV_GP2X:
            speed = cpuctrl.get_FCLK()
            print "Initial CPU speed is %s" % (speed)
            x, y, tvout = cpuctrl.get_screen_info()
            print "Initial screen size is %s, %s" % (x, y)
            if tvout:
                print "TV-Out mode is enabled."

        # This factor may be changed by the user to make text bigger
        # or smaller on those players that support it.
        self.fontScale = None

    def setCpuSpeed(self, activityName):
        """ Sets the CPU speed appropriately according to what the
        current activity is.  At the moment, this is used only for the
        GP2X. """

        if self.cpuSpeed == activityName:
            # No change.
            return
        self.cpuSpeed = activityName

        # The activityName directly hooks into a CPU speed indicated
        # in the user settings.

        attr = 'CPUSpeed_%s' % (activityName)
        speed = getattr(self.settings, attr, None)
        if speed is not None:
            self.OpenCPUControl()
            if env == ENV_GP2X:
                cpuctrl.set_FCLK(speed)
                pass

    def VolumeUp(self):
        try:
            volume = pygame.mixer.music.get_volume()
        except pygame.error:
            print "Failed to raise music volume!"
            return
        volume = min(volume + 0.1, 1.0)

        pygame.mixer.music.set_volume(volume)

    def VolumeDown(self):
        try:
            volume = pygame.mixer.music.get_volume()
        except pygame.error:
            print "Failed to lower music volume!"
            return
        volume = max(volume - 0.1, 0.0)

        pygame.mixer.music.set_volume(volume)

    def GetVolume(self):
        """ Gives the current volume level. """
        if vars().has_key('music'):
            return pygame.mixer.music.get_volume()
        else:
            return 0.50 # 75% is the industry recommended maximum value

    def SetVolume(self, volume):
        """ Sets the volume of the music playback. """
        volume = min(volume, 1.0)
        volume = max(volume, 0.0)
        pygame.mixer.music.set_volume(volume)

    def GetFontScale(self):
        """ Returns the current font scale. """
        if self.fontScale == None:
            self.fontScale = self.options.font_scale
        return self.fontScale

    def ZoomFont(self, factor):
        """ Zooms the font scale by the indicated factor.  This is
        treated like a resize event, even though the window is not
        changing size; player.doResize() will be called. """
        self.GetFontScale()
        self.fontScale *= factor
        if self.player:
            self.player.doResize(self.displaySize)

    def InitPlayer(self, player):

        """ A pykPlayer will call this when it constructs.  This
        registers the player with the pykManager, so that it will get
        callbacks and control of the display.  This call also ensures
        that pygame has been initialized. """

        if self.player:
            self.player.shutdown()
            self.player = None

        # Ensure we have been initialized.
        if not self.initialized:
            self.pygame_init()

        self.player = player
        self.player.State = STATE_NOT_PLAYING

        if self.display != None and self.displayTitle == None:
            try:
                pygame.display.set_caption(player.WindowTitle)
            except UnicodeError:
                pygame.display.set_caption(player.WindowTitle.encode('UTF-8', 'replace'))


    def OpenDisplay(self, displaySize = None, flags = None, depth = None):
        """ Use this method to open a pygame display or set the
        display to a specific mode. """

        self.getDisplayDefaults()

        if displaySize == None:
            displaySize = self.displaySize
        if flags == None:
            flags = self.displayFlags
        if depth == None:
            depth = self.displayDepth

        if self.options.dump:
            # We're just capturing frames offscreen.  In that case,
            # just open an offscreen buffer as the "display".
            self.display = None
            self.surface = pygame.Surface(self.displaySize)
            self.mouseVisible = False
            self.displaySize = self.surface.get_size()
            self.displayFlags = self.surface.get_flags()
            self.displayDepth = self.surface.get_bitsize()
        else:
            # Open the onscreen display normally.
            pygame.display.init()

            self.mouseVisible = not (env == ENV_GP2X or self.options.hide_mouse or (self.displayFlags & pygame.FULLSCREEN))
            pygame.mouse.set_visible(self.mouseVisible)

            if self.displayTitle != None:
                pygame.display.set_caption(self.displayTitle)
            elif self.player != None:
                try:
                    pygame.display.set_caption(self.player.WindowTitle)
                except UnicodeError:
                    pygame.display.set_caption(self.player.WindowTitle.encode('UTF-8', 'replace'))

            if self.display == None or \
               (self.displaySize, self.displayFlags, self.displayDepth) != (displaySize, flags, depth):
                self.display = pygame.display.set_mode(displaySize, flags, depth)
                self.displaySize = self.display.get_size()
                self.displayFlags = flags
                self.displayDepth = depth

            self.surface = self.display

        self.displayTime = pygame.time.get_ticks()

    def Flip(self):
        """ Call this method to make the displayed frame visible. """
        if self.display:
            pygame.display.flip()

    def CloseDisplay(self):
        """ Use this method to close the pygame window if it has been
        opened. """

        if self.display:
            pygame.display.quit()
            pygame.display.init()
            self.display = None

        self.surface = None

    def OpenAudio(self, frequency = None, size = None, channels = None):
        """ Use this method to initialize or change the audio
        parameters."""

        # We shouldn't mess with the CPU control while the audio is
        # open.
        self.CloseCPUControl()

        if frequency == None:
            frequency = self.settings.SampleRate

        if size == None:
            size = -16

        if channels == None:
            channels = self.settings.NumChannels

        bufferMs = self.settings.BufferMs

        # Compute the number of samples that would fill the indicated
        # buffer time.
        bufferSamples = bufferMs * (frequency * channels) / 1000

        # This needs to be a power of 2, so find the first power of 2
        # larger, up to 2^15.
        p = 1
        while p < bufferSamples and p < 32768:
            p <<= 1
        # Now choose the power of 2 closest.

        if (abs(bufferSamples - (p >> 1)) < abs(p - bufferSamples)):
            bufferSamples = p >> 1
        else:
            bufferSamples = p

        audioProps = (frequency, size, channels, bufferSamples)
        if audioProps != self.audioProps:
            # If the audio properties have changed, we have to shut
            # down and re-start the audio subsystem.
            pygame.mixer.quit()
            pygame.mixer.init(*audioProps)
            self.audioProps = audioProps

    def CloseAudio(self):
        pygame.mixer.quit()
        self.audioProps = None

    def OpenCPUControl(self):
        self.CloseAudio()
        if env == ENV_GP2X:
            cpuctrl.init()

    def CloseCPUControl(self):
        if env == ENV_GP2X:
            cpuctrl.shutdown()

    def GetAudioBufferMS(self):
        """ Returns the number of milliseconds it will take to
        completely empty a full audio buffer with the current
        settings. """
        if self.audioProps:
            frequency, size, channels, bufferSamples = self.audioProps
            return bufferSamples * 1000 / (frequency * channels)
        return 0

    def Quit(self):
        if self.player:
            self.player.shutdown()
            self.player = None

        if not self.initialized:
            return
        self.initialized = False

        pygame.quit()

    def __errorCallback(self, message):
        self.songValid = False
        print message
    def __doneCallback(self):
        pass

    def ValidateDatabase(self, songDb):
        """ Validates all of the songs in the database, to ensure they
        are playable and contain lyrics. """

        self.CloseDisplay()
        invalidFile = open('invalid.txt', 'w')

        songDb.SelectSort('filename')
        for song in songDb.SongList[:1074]:
            self.songValid = True
            player = song.MakePlayer(songDb, self.__errorCallback, self.__doneCallback)
            if not player:
                self.songValid = False
            else:
                if not player.Validate():
                    self.songValid = False

            if self.songValid:
                print '%s ok' % (song.DisplayFilename)
            else:
                print '%s invalid' % (song.DisplayFilename)
                print >> invalidFile, '%s\t%s' % (song.Filepath, song.ZipStoredName)
                invalidFile.flush()

    def Poll(self):
        """ Your application must call this method from time to
        time--ideally, within a hundred milliseconds or so--to perform
        the next quantum of activity. Alternatively, if the
        application does not require any cycles, you may just call
        WaitForPlayer() instead. """

        if not self.initialized:
            self.pygame_init()

        self.handleEvents()

        if self.player:
            if self.player.State == STATE_CLOSED:
                self.player = None
            else:
                self.player.doStuff()

        # Wait a bit to save on wasteful CPU usage.
        pygame.time.wait(1)

    def WaitForPlayer(self):
        """ The interface may choose to call this method in lieu of
        repeatedly calling Poll().  It will block until the currently
        active player has finished, and then return. """

        while self.player and self.player.State != STATE_CLOSED:
            self.Poll()

    def SetupOptions(self, usage, songDb):
        """ Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application.  This version of this method returns the options
        that are likely to be useful for any karaoke application. """

        version = "%prog " + pykversion.PYKARAOKE_VERSION_STRING

        settings = songDb.Settings

        parser = optparse.OptionParser(usage = usage, version = version,
                                       conflict_handler = "resolve")

        if env != ENV_OSX and env != ENV_GP2X:
            pos_x = None
            pos_y = None
            if settings.PlayerPosition:
                pos_x, pos_y = settings.PlayerPosition
            parser.add_option('-x', '--window-x', dest = 'pos_x', type = 'int', metavar='X',
                              help = 'position song window X pixels from the left edge of the screen', default = pos_x)
            parser.add_option('-y', '--window-y', dest = 'pos_y', type = 'int', metavar='Y',
                              help = 'position song window Y pixels from the top edge of the screen', default = pos_y)

        if env != ENV_GP2X:
            parser.add_option('-w', '--width', dest = 'size_x', type = 'int', metavar='X',
                              help = 'draw song window X pixels wide', default = settings.PlayerSize[0])
            parser.add_option('-h', '--height', dest = 'size_y', type = 'int', metavar='Y',
                              help = 'draw song window Y pixels high', default = settings.PlayerSize[1])
            parser.add_option('-t', '--title', dest = 'title', type = 'string', metavar='TITLE',
                              help = 'set song window title to TITLE', default = None)
            parser.add_option('-f', '--fullscreen', dest = 'fullscreen', action = 'store_true',
                              help = 'make song window fullscreen', default = settings.FullScreen)
            parser.add_option('', '--hide-mouse', dest = 'hide_mouse', action = 'store_true',
                              help = 'hide the mouse pointer', default = False)

        parser.add_option('-s', '--fps', dest = 'fps', metavar='N', type = 'int',
                          help = 'restrict visual updates to N frames per second',
                          default = 30)
        parser.add_option('-r', '--sample-rate', dest = 'sample_rate', type = 'int',
                          help = 'specify the audio sample rate.  Ideally, this should match the recording.  For MIDI files, higher is better but consumes more CPU.',
                          default = settings.SampleRate)
        parser.add_option('', '--num-channels', dest = 'num_channels', type = 'int',
                          help = 'specify the number of audio channels: 1 for mono, 2 for stereo.',
                          default = settings.NumChannels)
        parser.add_option('', '--font-scale', metavar='SCALE', dest = 'font_scale', type = 'float',
                          help = 'specify the font scale factor; small numbers (between 0 and 1) make text smaller so more fits on the screen, while large numbers (greater than 1) make text larger so less fits on the screen.',
                          default = 1)

        parser.add_option('', '--zoom', metavar='MODE', dest = 'zoom_mode', type = 'choice',
                          choices = settings.Zoom,
                          help = 'specify the way in which graphics are scaled to fit the window.  The choices are %s.' % (', '.join(map(lambda z: '"%s"' % z, settings.Zoom))),
                          default = settings.CdgZoom)

        parser.add_option('', '--buffer', dest = 'buffer', metavar = 'MS', type = 'int',
                          help = 'buffer audio by the indicated number of milliseconds',
                          default = settings.BufferMs)
        parser.add_option('-n', '--nomusic', dest = 'nomusic', action = 'store_true',
                          help = 'disable music playback, just display graphics', default = False)

        parser.add_option('', '--dump', dest = 'dump',
                          help = 'dump output as a sequence of frame images, for converting to video',
                          default = '')
        parser.add_option('', '--dump-fps', dest = 'dump_fps', type = 'float',
                          help = 'specify the number of frames per second of the sequence output by --dump',
                          default = 29.97)

        parser.add_option('', '--validate', dest = 'validate', action = 'store_true',
                          help = 'validate that all songs contain lyrics and are playable')

        return parser

    def ApplyOptions(self, songDb):
        """ Copies the user-specified command-line options in
        self.options to the settings in songDb.Settings. """

        self.settings = songDb.Settings

        self.settings.CdgZoom = self.options.zoom_mode

        if hasattr(self.options, 'fullscreen'):
            self.settings.FullScreen = self.options.fullscreen
            self.settings.PlayerSize = (self.options.size_x, self.options.size_y)
        if hasattr(self.options, 'pos_x') and \
           self.options.pos_x != None and self.options.pos_y != None:
            self.settings.PlayerPosition = (self.options.pos_x, self.options.pos_y)

        self.settings.NumChannels = self.options.num_channels
        self.settings.SampleRate = self.options.sample_rate
        self.settings.BufferMs = self.options.buffer

    def WordWrapText(self, text, font, maxWidth):
        """Folds the line (or lines) of text into as many lines as
        necessary to fit within the indicated width (when rendered by
        the given font), word-wrapping at spaces.  Returns a list of
        strings, one string for each separate line."""


        lines = []

        for line in text.split('\n'):
            fold = self.FindFoldPoint(line, font, maxWidth)
            while line:
                lines.append(line[:fold])
                line = line[fold:]
                fold = self.FindFoldPoint(line, font, maxWidth)

        return lines

    def FindFoldPoint(self, line, font, maxWidth):
        """Returns the index of the character within line which should
        begin the next line: the first non-space before maxWidth."""

        if maxWidth <= 0 or line == '':
            return len(line)

        fold = len(line.rstrip())
        width, height = font.size(line[:fold])
        while fold > 0 and width > maxWidth:
            sp = line[:fold].rfind(' ')
            if sp == -1:
                fold -= 1
            else:
                fold = sp
            width, height = font.size(line[:fold])

        while fold < len(line) and line[fold] == ' ':
            fold += 1

        if fold == 0:
            # Couldn't even get one character in.  Put it in anyway.
            fold = 1

        if line[:fold].strip() == '':
            # Oops, nothing but whitespace in front of the fold.  Try
            # again without the whitespace.
            ws = line[:fold]
            line = line[fold:]
            wsWidth, height = font.size(ws)
            return self.FindFoldPoint(line, font, maxWidth - wsWidth) + len(ws)

        return fold


    # The remaining methods are internal.

    def handleEvents(self):
        """ Handles the events returned from pygame. """

        if self.display:
            # check for Pygame events
            for event in pygame.event.get():
                self.handleEvent(event)


    def handleEvent(self, event):
        # Only handle resize events 250ms after opening the
        # window. This is to handle the bizarre problem of SDL making
        # the window small automatically if you set
        # SDL_VIDEO_WINDOW_POS and move the mouse around while the
        # window is opening. Give it some time to settle.
        player = self.player
        if event.type == pygame.VIDEORESIZE and pygame.time.get_ticks() - self.displayTime > 250:

            # Tell the player we are about to resize. This is required
            # for pympg.
            if player:
                player.doResizeBegin()

            # Do the resize
            self.displaySize = event.size
            self.settings.PlayerSize = tuple(self.displaySize)
            pygame.display.set_mode(event.size, self.displayFlags, self.displayDepth)
            # Call any player-specific resize
            if player:
                player.doResize(event.size)

            # Tell the player we have finished resizing
            if player:
                player.doResizeEnd()

        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONDOWN:
            if event.button == GP2X_BUTTON_VOLUP:
                self.VolumeUp()
            elif event.button == GP2X_BUTTON_VOLDOWN:
                self.VolumeDown()

        if player:
            player.handleEvent(event)

    def pygame_init(self):
        """ This method is called only once, the first time an
        application requests a pygame window. """

        pygame.init()

        if env == ENV_GP2X:
            num_joysticks = pygame.joystick.get_count()
            if num_joysticks > 0:
                stick = pygame.joystick.Joystick(0)
                stick.init() # now we will receive events for the GP2x joystick and buttons

        self.initialized = True

    def getDisplayDefaults(self):
        if env == ENV_GP2X:
            # The GP2x has no control over its window size or
            # placement.  You'll get fullscreen and like it.

            # Unfortunately, it appears that pygame--or maybe our SDL,
            # even though we'd compiled with paeryn's HW SDL--doesn't
            # allow us to open a TV-size window, so we have to settle
            # for the standard (320, 240) size and let the hardware
            # zooming scale it for TV out.
            self.displaySize = (320, 240)
            self.displayFlags = pygame.HWSURFACE | pygame.FULLSCREEN
            self.displayDepth = 0
            self.displayTitle = None
            self.mouseVisible = False
            return

        # Fix the position at top-left of window. Note when doing
        # this, if the mouse was moving around as the window opened,
        # it made the window tiny.  Have stopped doing anything for
        # resize events until 1sec into the song to work around
        # this. Note there appears to be no way to find out the
        # current window position, in order to bring up the next
        # window in the same place. Things seem to be different in
        # development versions of pygame-1.7 - it appears to remember
        # the position, and it is the only version for which fixing
        # the position works on MS Windows.

        # Don't set the environment variable on OSX.
        if env != ENV_OSX:
            if self.settings.PlayerPosition:
                x, y = self.settings.PlayerPosition
                os.environ['SDL_VIDEO_WINDOW_POS'] = "%s,%s" % (x, y)

        w, h = self.settings.PlayerSize
        self.displaySize = (w, h)

        self.displayFlags = pygame.RESIZABLE
        if self.settings.DoubleBuf:
            self.displayFlags |= pygame.DOUBLEBUF
        if self.settings.HardwareSurface:
            self.displayFlags |= pygame.HWSURFACE
        
        if self.settings.NoFrame:
            self.displayFlags |= pygame.NOFRAME
        if self.settings.FullScreen:
            self.displayFlags |= pygame.FULLSCREEN

        self.displayDepth = 0
        self.displayTitle = self.options.title

        self.mouseVisible = not (env == ENV_GP2X or self.options.hide_mouse or (self.displayFlags & pygame.FULLSCREEN))


# Now instantiate a global pykManager object.
manager = pykManager()
