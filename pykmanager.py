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
        self.audioProps = None

        self.displaySize = None
        self.displayFlags = 0
        self.displayDepth = 0
        self.gotDisplayDefaults = False

        # Find the correct font path. If fully installed on Linux this
        # will be sys.prefix/share/pykaraoke/fonts. Otherwise look for
        # it in the current directory.
        if (os.path.isfile("fonts/DejaVuSans.ttf")):
            self.FontPath = "fonts"
            self.IconPath = "icons"
        else:
            self.FontPath = os.path.join(sys.prefix, "share/pykaraoke/fonts")
            self.IconPath = os.path.join(sys.prefix, "share/pykaraoke/icons")

        # This factor may be changed by the user to make text bigger
        # or smaller on those players that support it.
        self.fontScale = None

        # This value is a time in milliseconds that will be used to
        # shift the time of the lyrics display relative to the video.
        # It is adjusted by the user pressing the left and right
        # arrows during singing, and is persistent during a session.
        # Positive values make the lyrics anticipate the music,
        # negative values delay them.

        # For some reason, an initial value of -250 ms seems about
        # right empirically, on Linux, but not on Windows or on the
        # GP2X.
        if env == ENV_LINUX:
            self.UserOffsetTime = -250
        else:
            self.UserOffsetTime = 0

    # Get the current display size
    def GetDisplaySize(self):
        return self.displaySize

    def SetDisplaySize(self, displaySize):
        if not self.gotDisplayDefaults:
            self.getDisplayDefaults()

        if displaySize != self.displaySize:
            if self.display != None:
                self.OpenDisplay(displaySize)
            else:
                self.displaySize = displaySize

            if self.player:
                self.player.doResize(event.size)

    def SetFullScreen(self, flag = True):
        if not self.gotDisplayDefaults:
            self.getDisplayDefaults()

        isFullscreen = ((self.displayFlags & pygame.FULLSCREEN) != 0)
        if isFullscreen != flag:
            if flag:
                self.displayFlags |= pygame.FULLSCREEN
            else:
                self.displayFlags &= ~pygame.FULLSCREEN
                    
            if self.display != None:
                self.OpenDisplay()
            if self.player:
                self.player.doResize(event.size)

    def VolumeUp(self):
        volume = pygame.mixer.music.get_volume()
        volume = min(volume + 0.1, 1.0)

        pygame.mixer.music.set_volume(volume)

    def VolumeDown(self):
        volume = pygame.mixer.music.get_volume()
        volume = max(volume - 0.1, 0.0)

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
            pygame.display.set_caption(player.WindowTitle)


    def OpenDisplay(self, displaySize = None, flags = None, depth = None):
        """ Use this method to open a pygame display or set the
        display to a specific mode. """

        if not self.gotDisplayDefaults:
            self.getDisplayDefaults()

        if displaySize == None:
            displaySize = self.displaySize
        if flags == None:
            flags = self.displayFlags
        if depth == None:
            depth = self.displayDepth

        pygame.display.init()
        self.mouseVisible = not (env == ENV_GP2X or self.options.hide_mouse or (self.displayFlags & pygame.FULLSCREEN))
        pygame.mouse.set_visible(self.mouseVisible)

        if self.displayTitle != None:
            pygame.display.set_caption(self.displayTitle)
        elif self.player != None:
            pygame.display.set_caption(self.player.WindowTitle)
        
        self.displayTime = pygame.time.get_ticks()

        if self.display == None or \
           (self.displaySize, self.displayFlags, self.displayDepth) != (displaySize, flags, depth):
            self.display = pygame.display.set_mode(displaySize, flags, depth)
            self.displaySize = self.display.get_size()
            self.displayFlags = flags
            self.displayDepth = depth

        return self.display

    def CloseDisplay(self):
        """ Use this method to close the pygame window if it has been
        opened. """

        if self.display:
            pygame.display.quit()
            pygame.display.init()
            self.display = None

    def OpenAudio(self, suggestedProperties = None, requiredProperties = None):
        """ Use this method to initialize or change the audio
        parameters.

        suggestedProperties and requiredProperties should be None or a
        tuple of the form (frequency, size, channels).  The difference
        is that requiredProperties will override the command-line
        defaults, while suggestedProperties will not.

        The buffer size is specified in milliseconds; the
        actual buffer size chosen will be close to this amount of
        time."""

        if requiredProperties != None:
            frequency, size, channels = requiredProperties

        else:
            if suggestedProperties != None:
                frequency, size, channels = suggestedProperties
            else:
                frequency, size, channels = 22050, -16, 2

            if self.options.sample_rate != None:
                frequency = self.options.sample_rate
            if self.options.num_channels != None:
                channels = self.options.num_channels

        bufferMs = self.options.buffer

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

    def GetAudioBufferMS(self):
        """ Returns the number of milliseconds it will take to
        completely empty a full audio buffer with the current
        settings. """
        frequency, size, channels, bufferSamples = self.audioProps
        return bufferSamples * 1000 / (frequency * channels)
            
    def Quit(self):
        if self.player:
            self.player.shutdown()
            self.player = None
            
        if not self.initialized:
            return
        self.initialized = False

        pygame.quit()

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

    def SetupOptions(self, usage):
        """ Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application.  This version of this method returns the options
        that are likely to be useful for any karaoke application. """
            
        version = "%prog " + pykversion.PYKARAOKE_VERSION_STRING

        parser = optparse.OptionParser(usage = usage, version = version,
                                       conflict_handler = "resolve")

        if env != ENV_OSX and env != ENV_GP2X:
            parser.add_option('-x', '--window-x', dest = 'pos_x', type = 'int', metavar='X',
                              help = 'position song window X pixels from the left edge of the screen', default = None)
            parser.add_option('-y', '--window-y', dest = 'pos_y', type = 'int', metavar='Y',
                              help = 'position song window Y pixels from the top edge of the screen', default = None)

        if env != ENV_GP2X:
            parser.add_option('-w', '--width', dest = 'size_x', type = 'int', metavar='X',
                              help = 'draw song window X pixels wide', default = 640)
            parser.add_option('-h', '--height', dest = 'size_y', type = 'int', metavar='Y',
                              help = 'draw song window Y pixels high', default = 480)
            parser.add_option('-t', '--title', dest = 'title', type = 'string', metavar='TITLE',
                              help = 'set song window title to TITLE', default = None)
            parser.add_option('-f', '--fullscreen', dest = 'fullscreen', action = 'store_true', 
                              help = 'make song window fullscreen', default = False)
            parser.add_option('', '--hide-mouse', dest = 'hide_mouse', action = 'store_true', 
                              help = 'hide the mouse pointer', default = False)
            
        parser.add_option('-s', '--fps', dest = 'fps', metavar='N', type = 'int',
                          help = 'restrict visual updates to N frames per second', 
                          default = 30)
        parser.add_option('-r', '--sample-rate', dest = 'sample_rate', type = 'int',
                          help = 'specify the audio sample rate.  Ideally, this should match the recording.  For MIDI files, higher is better but consumes more CPU.',
                          default = None)
        parser.add_option('', '--num-channels', dest = 'num_channels', type = 'int',
                          help = 'specify the number of audio channels: 1 for mono, 2 for stereo.',
                          default = None)
        parser.add_option('', '--font-scale', metavar='SCALE', dest = 'font_scale', type = 'float',
                          help = 'specify the font scale factor; small numbers (between 0 and 1) make text smaller so more fits on the screen, while large numbers (greater than 1) make text larger so less fits on the screen.',
                          default = 1)

        parser.add_option('', '--zoom', metavar='MODE', dest = 'zoom_mode', type = 'choice',
                          choices = ['quick', 'int', 'full', 'soft', 'none' ],
                          help = 'specify the way in which graphics are scaled to fit the window.  The choices are "quick", "int", "full", "soft", or "none".',
                          default = 'int')

        parser.add_option('', '--buffer', dest = 'buffer', metavar = 'MS', type = 'int',
                          help = 'buffer audio by the indicated number of milliseconds', 
                          default = 50)
        parser.add_option('-n', '--nomusic', dest = 'nomusic', action = 'store_true',
                          help = 'disable music playback, just display graphics', default = False)

        return parser



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
            self.displaySize = (320, 240)
            self.displayFlags = pygame.HWSURFACE
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
            x = self.options.pos_x
            y = self.options.pos_y
            if x != None and y != None:
                os.environ['SDL_VIDEO_WINDOW_POS'] = "%s,%s" % (x, y)

        w = self.options.size_x
        h = self.options.size_y
        self.displaySize = (w, h)

        self.displayFlags = pygame.RESIZABLE | pygame.HWSURFACE
        if self.options.fullscreen:
            self.displayFlags |= pygame.FULLSCREEN

        self.displayDepth = 0
        self.displayTitle = self.options.title

        self.mouseVisible = not (env == ENV_GP2X or self.options.hide_mouse or (self.displayFlags & pygame.FULLSCREEN))

        self.gotDisplayDefaults = True
        
    
# Now instantiate a global pykManager object.
manager = pykManager()
