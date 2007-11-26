#!/usr/bin/env python

# pykaraoke - Karaoke Player Frontend
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


# OVERVIEW
#
# pykaraoke_mini is a frontend for the pycdg and pympg karaoke
# players.  It is similar to pykaraoke.py, but it is designed for use
# on small portable devices rather than PC's.  In particular, it could
# be useful on any device lacking a keyboard and mouse.
#
# It presents a scrolling list of songs to choose from, sorted by
# title, artist, or filename.  It works within the same pygame window
# used to render the karaoke songs themselves, so the scrolling
# interface is not available while a song is being performed.  The
# biggest strength of pykaraoke_mini is that it does not rely on a
# keyboard or a windowing interface, so it is ideal for use with a
# joystick or even an IR remote control in a bar.
#
# Unlike pykaraoke, pykaraoke_mini does not store a database of song
# files, nor does it search around through different folders to find
# your song files.  Instead, it is your responsibility to build a
# catalog file, which is a text file that contains one line per each
# song.  Each line should be of the form:
#
# filename <tab> title <tab> artist
#
# You can include international characters by encoding the file in
# UTF-8.  All three of these fields will be presented to the user in
# the scrolling list.  The filename is assumed to be relative to the
# catalog file itself.
#
# If you like, you can maintain multiple different catalog files of
# this form, which will allow you to run pykaraoke_mini with different
# subsets of your song files.  Use the --catalog command-line option
# to specify the full path to your catalog file; the default filename
# is songs/catalog.txt.
#
# While navigating the scrolling menu, the following keys are available:

# up / down  :  scroll through the list.  Hold the button down to
# scroll very rapidly.

# pageup / pagedown  :  scroll a page at a time.

# enter  :  select the highlighted song for performance.

# tab  :  change the sort mode between title, artist, and filename.
# The current sort key is displayed first for each file.

# + / -  :  enlarge or reduce the font scale.  This also affects the
# font scale when a MIDI file is selected (but does not affect CDG or
# MPG files).

# a-z  :  search for a song beginning with the indicated letter.  If you
# type multiple letters, search for a song beginning with the string
# you type.

from pykconstants import *
from pykenv import env
from pykmanager import manager
from pykplayer import pykPlayer
import pykversion
import pykdb
import pygame, sys, os, math, bisect

# We inherit from pykPlayer here, not because we need to play a song
# on the menu, but because we want to hook up to the pykManager and
# get resize callbacks, etc.
class App(pykPlayer):
    def __init__(self):
        pykPlayer.__init__(self, '', self.errorPopupCallback, self.songFinishedCallback,
                           windowTitle = "PyKaraoke")
        self.SupportsFontZoom = True

    def SetupOptions(self):
        """ Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application. """

        parser = pykPlayer.SetupOptions(self, usage = "%prog [options]")

        parser.add_option('', '--scan', dest = 'scan', action = 'store_true',
                          help = 'rescan song directories for new files')
        parser.add_option('', '--set-scan-dir', dest = 'scan_dir', action = 'store',
                          help = 'sets the named directory as the only directory to be scanned for karaoke files.')
        parser.add_option('', '--add-scan-dir', dest = 'scan_dirs', action = 'append',
                          help = 'adds the named directory to the list of directories to be scanned for karaoke files.')
       
        return parser

    
    def setupSplashScreen(self):
        # Quick, put up a splash screen for the user to look at while
        # we're loading.
        self.splashStart = None

        manager.OpenDisplay()

        splashFilename = os.path.join(manager.IconPath, 'splash.jpg')
        try:
            splash = pygame.image.load(splashFilename)
        except:
            print "Unable to load splash image."
            return

        # Put the version number up there too.
        pygame.font.init()
        font = pygame.font.Font(os.path.join(manager.FontPath, "DejaVuSansCondensed-Bold.ttf"), 12)

        text = font.render("v%s" % pykversion.PYKARAOKE_VERSION_STRING, True, (0, 0, 0))
        rect = text.get_rect()
        rect = rect.move(225 - rect.width, 43)
        splash.blit(text, rect)

        # Center the splash screen within our display window.
        winWidth, winHeight = manager.displaySize
        imgWidth, imgHeight = splash.get_size()

        scale = min(float(winWidth) / imgWidth,
                    float(winHeight) / imgHeight)

        # We can scale it smaller, but don't scale it bigger.
        scale = min(scale, 1)
        
        scaledWidth = int(scale * imgWidth)
        scaledHeight = int(scale * imgHeight)

        xOffset = (winWidth - scaledWidth) / 2
        yOffset = (winHeight - scaledHeight) / 2

        if scale < 1:
            scaled = pygame.transform.rotozoom(splash, 0, scale)
            manager.display.blit(scaled, (xOffset, yOffset))
        else:
            manager.display.blit(splash, (xOffset, yOffset))
            
        pygame.display.flip()

        # Record the time at which the user was first able to see the
        # splash screen.
        self.splashStart = pygame.time.get_ticks()


    def setupScrollWindow(self):
        winWidth, winHeight = manager.displaySize
        
        pygame.font.init()
        fontSize = int(manager.GetFontScale() * winHeight / 18)
        self.thinFont = pygame.font.Font(os.path.join(manager.FontPath, "DejaVuSansCondensed.ttf"), fontSize)

        fontSize = int(manager.GetFontScale() * winHeight / 15)
        self.boldFont = pygame.font.Font(os.path.join(manager.FontPath, "DejaVuSansCondensed-Bold.ttf"), fontSize)
        
        self.boldHeight = self.boldFont.get_linesize()
        self.thinHeight = self.thinFont.get_linesize()
        self.rowHeight = self.boldHeight + (self.numSongInfoLines - 1) * self.thinHeight

        # Make sure the color highlight covers the bottom of the line.
        # Empirically, the DejaVu fonts want this much shift:
        self.lineShift = -self.boldFont.get_descent() / 2

        self.numRows = max(int(winHeight / self.rowHeight), 1)
        self.yMargin = (winHeight - self.numRows * self.rowHeight) / 2 - self.lineShift
        self.xMargin = 5
        self.xIndent = 10

        self.centerRow = (self.numRows - 1) / 2

    def paintScrollWindow(self):
        manager.display.fill((0,0,0))

        # First, fill in the blue highlight bar in the center.
        y = self.yMargin + self.centerRow * self.rowHeight + self.lineShift
        rect = pygame.Rect(0, y, manager.displaySize[0], self.rowHeight)
        manager.display.fill((0, 0, 120), rect)

        # Now draw the text over everything.
        for i in range(self.numRows):
            y = self.yMargin + i * self.rowHeight
            r = (self.currentRow + i - self.centerRow) % len(self.SongDB.SongList)
            file = self.SongDB.SongList[r]
            a, b, c = self.SongDB.GetSongTuple(file)

            fg = (180, 180, 180)
            if i == self.centerRow:
                fg = (255, 255, 255)

            text = self.boldFont.render(a, True, fg)
            manager.display.blit(text, (self.xMargin, y))
            y += self.boldHeight
            if self.numSongInfoLines >= 2:
                text = self.thinFont.render(b, True, fg)
                manager.display.blit(text, (self.xMargin + self.xIndent, y))
                y += self.thinHeight
            if self.numSongInfoLines >= 3:
                text = self.thinFont.render(c, True, fg)
                manager.display.blit(text, (self.xMargin + self.xIndent, y))
                y += self.thinHeight

        pygame.display.flip()
    
    def start(self):
        self.appStart = pygame.time.get_ticks()

        self.numSongInfoLines = 1
        
        self.setupSplashScreen()
        manager.InitPlayer(self)
        self.setupScrollWindow()

        self.screenDirty = True
        self.SongDB = pykdb.globalSongDB
        self.SongDB.LoadSettings(self.errorPopupCallback)

        needsSave = False

        if manager.options.scan_dir:
            # Replace the old scan list.
            self.SongDB.Settings.FolderList = [ manager.options.scan_dir ]
            needsSave = True

        if manager.options.scan_dirs:
            # Add one or more new directories to the list.
            self.SongDB.Settings.FolderList += manager.options.scan_dirs
            needsSave = True
        
        if manager.options.scan:
            # Re-scan the files.
            self.errorPopupCallback("Scanning:\n%s" % ('\n'.join(self.SongDB.Settings.FolderList)))
            self.SongDB.BuildSearchDatabase(pykdb.AppYielder(), pykdb.BusyCancelDialog())
            needsSave = True


        if not self.SongDB.SongList:
            # No files.
            self.errorPopupCallback("No songs in catalog.")
            return

        if needsSave:
            self.SongDB.SaveSettings()

        if self.SongDB.GotTitles:
            self.numSongInfoLines += 1
        if self.SongDB.GotArtists:
            self.numSongInfoLines += 1
        self.setupScrollWindow()

        if self.SongDB.GotTitles:
            self.SongDB.SelectSort('title')
        elif self.SongDB.GotArtists:
            self.SongDB.SelectSort('artist')
        else:
            self.SongDB.SelectSort('filename')

        self.currentRow = 0
        self.searchString = ''
        self.heldKey = None
        self.heldStartTicks = 0
        self.heldRepeat = 0

        # Now that we've finished loading, wait up a second and give
        # the user a chance to view the splash screen, in case we
        # loaded too fast.
        if self.splashStart != None:
            splashTime = pygame.time.get_ticks() - self.splashStart
            remainingTime = 2500 - splashTime
            if remainingTime > 0:
                pygame.time.wait(remainingTime)
        
        self.running = True
        
        while self.running:
            manager.Poll()

    def selectSong(self):
        file = self.SongDB.SongList[self.currentRow]
        
        manager.display.fill((0,0,0))

        winWidth, winHeight = manager.displaySize
        winCenter = winWidth / 2

        rowA = winHeight / 3
        rowB = rowA + 10
        rowC = winHeight * 5 / 6

        # Word-wrap the title
        for line in manager.WordWrapText(file.Title, self.boldFont, winWidth):
            line = line.strip()
            text = self.boldFont.render(line, True, (255,255,255))
            rect = text.get_rect()
            rect = rect.move(winCenter - rect.centerx, rowA)
            manager.display.blit(text, rect)
            rowA += self.boldHeight
            rowB += self.boldHeight

        # Now word-wrap the artist
        if file.Artist:
            for line in manager.WordWrapText(file.Artist, self.thinFont, winWidth):
                line = line.strip()
                text = self.thinFont.render(line, True, (255,255,255))
                rect = text.get_rect()
                rect = rect.move(winCenter - rect.centerx, rowB)
                manager.display.blit(text, rect)
                rowB += self.thinHeight

        text = self.thinFont.render("Loading", True, (255,255,255))
        rect = text.get_rect()
        rect = rect.move(winCenter - rect.centerx, rowC)
        manager.display.blit(text, rect)

        pygame.display.flip()

        # This will call the songFinishedCallback, so call it early.
        self.shutdown()

        player = file.MakePlayer(self.errorPopupCallback, self.songFinishedCallback)
        if player == None:
            return
        
        # Start playing.
        try:
            player.Play()
        except:
            self.errorPopupCallback("Error starting player.\n%s\n%s" % (sys.exc_info()[0], sys.exc_info()[1]))
            return

        # Go to sleep until the song is over.
        try:
            manager.WaitForPlayer()
        except:
            self.errorPopupCallback("Error while playing song.\n%s\n%s" % (sys.exc_info()[0], sys.exc_info()[1]))
            return

        # The song is over.  Now recover control and redisplay the
        # song list.
        manager.InitPlayer(self)
        manager.OpenDisplay()

        # In case the screen has been resized during the song.
        self.setupScrollWindow()

        self.screenDirty = True

    def rowDown(self, count):
        self.currentRow = (self.currentRow + count) % len(self.SongDB.SongList)
        self.screenDirty = True

    def rowUp(self, count):
        self.currentRow = (self.currentRow - count) % len(self.SongDB.SongList)
        self.screenDirty = True

    def pageDown(self, count):
        self.rowDown(count * self.numRows)

    def pageUp(self, count):
        self.rowUp(count * self.numRows)

    def changeSort(self):
        file = self.SongDB.SongList[self.currentRow]

        if self.SongDB.Sort == 'title':
            if self.SongDB.GotArtists:
                self.SongDB.SelectSort('artist')
            else:
                self.SongDB.SelectSort('filename')
        elif self.SongDB.Sort == 'artist':
            self.SongDB.SelectSort('filename')
        else:  # 'filename'
            if self.SongDB.GotTitles:
                self.SongDB.SelectSort('title')
            elif self.SongDB.GotArtists:
                self.SongDB.SelectSort('artist')

        self.currentRow = bisect.bisect_left(self.SongDB.SongList, file)
        self.screenDirty = True

    def goToSearch(self, searchString):
        """ Sets the current row to the item beginning with
        searchString.  Assumes the FileList has previously been sorted
        by a call to SelectSort(). """

        self.currentRow = bisect.bisect_left(self.SongDB.SongList,
                                             pykdb.SongStruct(searchString, searchString, searchString, searchString))
        if self.currentRow == len(self.SongDB.SongList):
            self.currentRow = 0

        self.screenDirty = True


    def handleRepeatable(self, type, key, count):
        if type == pygame.KEYDOWN:
            if key == pygame.K_DOWN:
                self.rowDown(count)
            elif key == pygame.K_UP:
                self.rowUp(count)
            elif key == pygame.K_PAGEDOWN:
                self.pageDown(count)
            elif key == pygame.K_PAGEUP:
                self.pageUp(count)

        elif type == pygame.JOYBUTTONDOWN:
            if key == GP2X_BUTTON_DOWN:
                self.rowDown(count)
            elif key == GP2X_BUTTON_UP:
                self.rowUp(count)
            elif key == GP2X_BUTTON_R:
                self.pageDown(count)
            elif key == GP2X_BUTTON_L:
                self.pageUp(count)

    def doStuff(self):
        pykPlayer.doStuff(self)

        if self.screenDirty:
            self.paintScrollWindow()
            self.screenDirty = False

        if self.heldKey:
            elapsed = pygame.time.get_ticks() - self.heldStartTicks
            repeat = 0
            if elapsed > 4000:
                repeat = int((elapsed - 4000) / 5.) + 256
            else:
                repeat = int(math.pow((elapsed / 1000.), 4))

            if repeat > self.heldRepeat:
                self.handleRepeatable(self.heldKey[0], self.heldKey[1],
                                      repeat - self.heldRepeat)
                self.heldRepeat = repeat

    def handleEvent(self, event):
        
        if event.type == pygame.KEYDOWN:
            if event.unicode and event.unicode[0] >= ' ':
                # The user has typed a keystroke that counts toward a
                # search.
                if event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS or \
                   event.key == pygame.K_KP_PLUS or \
                   event.key == pygame.K_MINUS or event.key == pygame.K_UNDERSCORE or \
                   event.key == pygame.K_KP_MINUS:

                    # Except any one of these keys, which are reserved
                    # for font zoom.
                    pass
                else:
                    self.searchString += event.unicode
                    self.goToSearch(self.searchString)
                    return
            if self.searchString and event.key == pygame.K_BACKSPACE:
                # Backing up on the search.
                self.searchString = self.searchString[:-1]
                self.goToSearch(self.searchString)
                return

            self.searchString = ''
            self.heldKey = (pygame.KEYDOWN, event.key)
            self.heldStartTicks = pygame.time.get_ticks()
            self.heldRepeat = 0

            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_RETURN:
                self.selectSong()
            elif event.key == pygame.K_TAB:
                self.changeSort()
            else:
                self.handleRepeatable(pygame.KEYDOWN, event.key, 1)

        elif event.type == pygame.KEYUP:
            self.heldKey = None

        elif event.type == pygame.QUIT:
            self.running = False

        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONDOWN:
            self.heldKey = (pygame.JOYBUTTONDOWN, event.button)
            self.heldStartTicks = pygame.time.get_ticks()
            self.heldRepeat = 0

            if event.button == GP2X_BUTTON_Y:
                self.running = False
            elif event.button == GP2X_BUTTON_START or \
                 event.button == GP2X_BUTTON_X or \
                 event.button == GP2X_BUTTON_B:
                self.selectSong()
            elif event.button == GP2X_BUTTON_A:
                self.changeSort()
            elif event.button == GP2X_BUTTON_SELECT:
                # Break out so this one won't fall through to
                # pykPlayer, which would shut us down.
                return
            else:
                self.handleRepeatable(pygame.JOYBUTTONDOWN, event.button, 1)

        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONUP:
            self.heldKey = None

        pykPlayer.handleEvent(self, event)

    def errorPopupCallback(self, errorString):
        print errorString

        manager.InitPlayer(self)
        manager.OpenDisplay()

        manager.display.fill((0,0,0))

        # Center the error message onscreen.
        winWidth, winHeight = manager.displaySize
        winCenter = winWidth / 2

        lines = manager.WordWrapText(errorString, self.thinFont, winWidth - X_BORDER * 2)

        row = (winHeight - len(lines) * self.thinHeight) / 2
        for line in lines:
            line = line.strip()
            text = self.thinFont.render(line, True, (255,255,255))
            rect = text.get_rect()
            rect = rect.move(winCenter - rect.centerx, row)
            manager.display.blit(text, rect)
            row += self.thinHeight

        pygame.display.flip()
        self.screenDirty = True

        # Now wait a certain amount of time--say 5 seconds.
        waitUntil = pygame.time.get_ticks() + 5000

        # But also, wait a quarter second to give the user a chance to
        # react and stop hitting buttons.
        pygame.time.wait(250)

        # Discard any events that occurred in that quarter second.
        for event in pygame.event.get():
            pass

        # Now start listening for events.  The first key or button
        # event gets us out of here.
        buttonPressed = False
        while not buttonPressed and pygame.time.get_ticks() < waitUntil:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN or \
                   (env == ENV_GP2X and event.type == pygame.JOYBUTTONDOWN):
                    buttonPressed = True
                    break

    def songFinishedCallback(self):
        self.SongDB.CleanupTempFiles()

    def doResize(self, newSize):
        # This will be called internally whenever the window is
        # resized for any reason, either due to an application resize
        # request being processed, or due to the user dragging the
        # window handles.
        self.setupScrollWindow()
        self.screenDirty = True
    

def main():
    app = App()
    app.start()

if __name__ == "__main__":
    sys.exit(main())


