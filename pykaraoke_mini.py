#!/usr/bin/env python

# pykaraoke - Karaoke Player Frontend
#
# Copyright (C) 2010 Kelvin Lawson (kelvinl@users.sourceforge.net)
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
# titles file, which is a text file that contains one line per each
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
# subsets of your song files.  Each file should be named titles.txt,
# or some variant on titles*.txt, such as titles_mysubdir.txt.
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

    # This is the list of buttons that are always to be interpreted as
    # special command keys, not as type-and-search keys.
    CommandKeys = [
        pygame.K_UP, pygame.K_DOWN,
        pygame.K_LEFT, pygame.K_RIGHT,
        pygame.K_PAGEUP, pygame.K_PAGEDOWN,
        pygame.K_F1,
        ]

    # This is the list of buttons that are interpreted as special
    # command keys if there is not already a text typed.
    FirstCommandKeys = [
        pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS,
        pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS,
        ]

               
    def __init__(self):
        pykPlayer.__init__(self, '', None, self.errorPopupCallback,
                           self.songFinishedCallback, windowTitle = "PyKaraoke")
        self.SupportsFontZoom = True
        self.selectedSong = None

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

        splashFilename = os.path.join(manager.IconPath, 'splash.png')
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
        fontSize = int(manager.GetFontScale() * winHeight / 24)
        self.thinFont = pygame.font.Font(os.path.join(manager.FontPath, "DejaVuSansCondensed.ttf"), fontSize)

        fontSize = int(manager.GetFontScale() * winHeight / 20)
        self.boldFont = pygame.font.Font(os.path.join(manager.FontPath, "DejaVuSansCondensed-Bold.ttf"), fontSize)

        fontSize = int(manager.GetFontScale() * winHeight / 15)
        self.titleFont = pygame.font.Font(os.path.join(manager.FontPath, "DejaVuSansCondensed-Bold.ttf"), fontSize)
        fontSize = int(manager.GetFontScale() * winHeight / 18)
        self.subtitleFont = pygame.font.Font(os.path.join(manager.FontPath, "DejaVuSansCondensed.ttf"), fontSize)

        
        self.boldHeight = self.boldFont.get_linesize()
        self.thinHeight = self.thinFont.get_linesize()
        self.titleHeight = self.titleFont.get_linesize()
        self.subtitleHeight = self.subtitleFont.get_linesize()
        
        self.rowHeight = self.boldHeight + (self.numSongInfoLines - 1) * self.thinHeight
        self.songWindowRowHeight = self.boldHeight * 1.2

        # Make sure the color highlight covers the bottom of the line.
        # Empirically, the DejaVu fonts want this much shift:
        self.lineShift = -self.boldFont.get_descent() / 2

        self.numRows = max(int(winHeight / self.rowHeight), 1)
        self.yMargin = (winHeight - self.numRows * self.rowHeight) / 2 - self.lineShift
        self.xMargin = 5
        self.xIndent = 10

        self.numSongWindowRows = max(int(winHeight / self.songWindowRowHeight), 1)
        self.centerRow = (self.numRows - 1) / 2

    def paintWindow(self):
        if self.selectedSong:
            self.paintSongWindow()
        else:
            self.paintMainWindow()

    def paintSongWindow(self):
        """ The user has already selected a song, and now has to
        select the specific version of it he/she meant to play. """

        manager.display.fill((0,0,0))
        row = self.__writeSongTitle(self.selectedSong, 0)

        self.startSongWindowRow = int((row + self.songWindowRowHeight - 1) / self.songWindowRowHeight)
        numRows = self.numSongWindowRows - self.startSongWindowRow

        for i in range(len(self.selectedSong.sameSongs)):
            file = self.selectedSong.sameSongs[i]
            fg = file.getTextColour(False)
            y = (i + self.startSongWindowRow) * self.songWindowRowHeight

            filename = file.DisplayFilename
            if file.getMarkKey() in self.markedSongs:
                filename = '* ' + filename

            text = self.boldFont.render(filename, True, fg)
            manager.display.blit(text, (self.xMargin, y))

        # Now go back and re-draw the highlighted song.
        i = self.selectedSongRow
        file = self.selectedSong.sameSongs[i]
        fg = file.getTextColour(True)
        bg = file.getBackgroundColour(True)
        y = (i + self.startSongWindowRow) * self.songWindowRowHeight

        filename = file.DisplayFilename
        if file.getMarkKey() in self.markedSongs:
            filename = '* ' + filename
            
        text = self.boldFont.render(filename, True, fg, bg)
        manager.display.blit(text, (self.xMargin, y))

        pygame.display.flip()

    def paintMainWindow(self):
        """ Paints the main 'select a song' index. """

        manager.display.fill((0,0,0))

        # First, fill in the colored highlight bar in the center.
        y = self.yMargin + self.centerRow * self.rowHeight + self.lineShift
        rect = pygame.Rect(0, y, manager.displaySize[0], self.rowHeight)

        file = self.songDb.SongList[self.currentRow]
        bg = file.getBackgroundColour(True)
        manager.display.fill(bg, rect)

        # Now draw the text over everything.
        for i in range(self.numRows):
            y = self.yMargin + i * self.rowHeight
            r = (self.currentRow + i - self.centerRow) % len(self.songDb.SongList)
            song = self.songDb.SongList[r]
            a, b, c = self.songDb.GetSongTuple(song)
                
            if self.songIsMarked(song):
                a = '* ' + a

            fg = song.getTextColour(i == self.centerRow)
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

    def songIsMarked(self, song):
        """ If the song, or a different song with the same
        artist/title has been marked, returns the marked song object.
        If the song has not been marked, returns None. """

        marked = False
        if self.songDb.Sort == 'filename':            
            # If we're sorting by filename, then every song is
            # individually marked.
            if song.getMarkKey() in self.markedSongs:
                return song
            
        else:
            # If we're sorting by title or artist, then the song
            # line onscreen might correspond to multiple song
            # files, and we should show the marked flag if any one
            # of them is marked.
            for file in song.sameSongs:
                if file.getMarkKey() in self.markedSongs:
                    return file

        return None


    def markCurrentSongFile(self):
        """ Marks (or unmarks) the currently-highlighted song file.
        In artist or title sort, this actually marks the first song
        file with the matching artist /title. """

        if self.selectedSong:
            # Song window.  Only one filename can be highlighted, so
            # it is unambiguous.
            
            i = self.selectedSongRow
            file = self.selectedSong.sameSongs[i]
            if file.getMarkKey() in self.markedSongs:
                del self.markedSongs[file.getMarkKey()]
            else:
                self.markedSongs[file.getMarkKey()] = file

        else:
            # Main window.  This is unambiguous only in filename sort.
            # In artist or title sort, we might be highlighting
            # multiple song files at once.
            
            song = self.songDb.SongList[self.currentRow]
            file = self.songIsMarked(song)
            if file:
                # Unmark this particular song file.
                del self.markedSongs[file.getMarkKey()]

                # In fact, unmark all of them with the same artist
                # / title.
                file = self.songIsMarked(song)
                while file:
                    del self.markedSongs[file.getMarkKey()]
                    file = self.songIsMarked(song)

            else:
                # Mark this song file.
                self.markedSongs[song.getMarkKey()] = song

        self.markedSongsDirty = True
        self.screenDirty = True
    
    def start(self):
        self.appStart = pygame.time.get_ticks()
        self.heldStartTicks = self.appStart
        manager.OpenCPUControl()
        manager.setCpuSpeed('startup')

        self.numSongInfoLines = 1
        
        self.setupSplashScreen()
        manager.InitPlayer(self)
        self.setupScrollWindow()

        self.screenDirty = True

        needsSave = False

        if manager.options.scan_dir:
            # Replace the old scan list.
            self.songDb.Settings.FolderList = [ manager.options.scan_dir ]
            needsSave = True

        if manager.options.scan_dirs:
            # Add one or more new directories to the list.
            self.songDb.Settings.FolderList += manager.options.scan_dirs
            needsSave = True
        
        if manager.options.scan:
            # Re-scan the files.
            self.songDb.BuildSearchDatabase(pykdb.AppYielder(), MiniBusyCancelDialog(self))
            needsSave = True
        else:
            # Read the existing database.
            self.songDb.LoadDatabase(self.errorPopupCallback)

        if needsSave:
            self.songDb.SaveSettings()
            self.songDb.SaveDatabase()

        if not self.songDb.FullSongList:
            # No files.
            self.errorPopupCallback("No songs in catalog.")
            return

        if manager.options.validate:
            manager.ValidateDatabase(self.songDb)
            return

        if self.songDb.GotTitles:
            self.numSongInfoLines += 1
        if self.songDb.GotArtists:
            self.numSongInfoLines += 1
        self.setupScrollWindow()

        self.readMarkedSongs()

        if self.songDb.GotTitles:
            self.songDb.SelectSort('title')
        elif self.songDb.GotArtists:
            self.songDb.SelectSort('artist')
        else:
            self.songDb.SelectSort('filename')

        self.currentRow = 0
        self.searchString = ''
        self.heldKey = None
        self.heldStartTicks = 0
        self.heldRepeat = 0

        manager.setCpuSpeed('wait')

        # Now that we've finished loading, wait up a second and give
        # the user a chance to view the splash screen, in case we
        # loaded too fast.
        if self.splashStart != None:
            splashTime = pygame.time.get_ticks() - self.splashStart
            remainingTime = 2500 - splashTime
            if remainingTime > 0:
                pygame.time.wait(remainingTime)
        
        self.running = True

        manager.setCpuSpeed('menu_fast')
        self.heldStartTicks = pygame.time.get_ticks()
        
        while self.running:
            manager.Poll()

        self.writeMarkedSongs()
        manager.CloseDisplay()

    def readMarkedSongs(self):
        """ Reads marked.txt, which lists the files that have been
        marked by the user for later inspection or adjustment (for
        instance, to correct a title misspelling or something). """

        self.markedSongs = {}
        self.markedSongsDirty = False

        pathname = os.path.join (self.songDb.SaveDir, "marked.txt")
        if not os.path.exists(pathname):
            return

        # We need to re-sort by filename in order to look up the
        # songs properly.
        self.songDb.SelectSort('filename')

        file = open(pathname, 'r')
        for line in file:
            line = line.decode('utf-8').strip()
            if line:
                # Read a line from the list.  It describes a song, and
                # includes filename, title, and artist, though we only
                # really care about the filename.
                filename = line.split('\t', 1)[0]

                # Look up the song in the database.
                song = pykdb.SongStruct(filename, self.songDb.Settings,
                                        '', '', filename)
                found = False
                row = bisect.bisect_left(self.songDb.SongList, song)
                if row != len(self.songDb.SongList):
                    # If we found the song, record that it is marked.
                    song = self.songDb.SongList[row]
                    if song.DisplayFilename == filename:
                        self.markedSongs[song.getMarkKey()] = song
                        found = True

                if not found:
                    # If we didn't find the song, it follows that
                    # marked.txt is out-of-sync with the database, and
                    # needs to be rewritten.
                    self.markedSongsDirty = True

    def writeMarkedSongs(self):
        """ Rewrites marked.txt, if it needs to be written. """
        if not self.markedSongsDirty:
            return

        pathname = os.path.join (self.songDb.SaveDir, "marked.txt")
        file = open(pathname, 'w')
        markedSongs = self.markedSongs.items()
        markedSongs.sort()
        for key, song in markedSongs:
            line = '%s\t%s\t%s\n' % (song.DisplayFilename, song.Title, song.Artist)
            file.write(line.encode('utf-8'))

        self.markedSongsDirty = False

    def selectSong(self):
        """ The user has selected a song from the list.  There might
        be an ambiguity, if there are multiple song files with the
        same artist/title.  If so, present the new list to the user
        and allow her to choose the specific file she meant. """

        if self.selectedSong:
            # We're already on the selected-a-particular-song index.
            # Therefore, run with the one we've selected from that
            # index.
            file = self.selectedSong.sameSongs[self.selectedSongRow]
            self.beginSong(file)
            return

        file = self.songDb.SongList[self.currentRow]

        if len(file.sameSongs) == 1 or self.songDb.Sort == 'filename':
            # No ambiguity.
            self.beginSong(file)
            return

        manager.display.fill((0,0,0))

        self.selectedSong = file
        self.selectedSongRow = 0
        self.screenDirty = True

    def beginSong(self, file):
        self.selectedSong = None
        manager.setCpuSpeed('load')
        manager.display.fill((0,0,0))

        winWidth, winHeight = manager.displaySize
        winCenter = winWidth / 2

        rowA = winHeight / 3
        rowC = winHeight * 5 / 6

        self.__writeSongTitle(file, rowA)

        text = self.subtitleFont.render("Loading", True, (255,255,255))
        rect = text.get_rect()
        rect = rect.move(winCenter - rect.centerx, rowC)
        manager.display.blit(text, rect)

        pygame.display.flip()

        # This will call the songFinishedCallback, so call it early.
        self.shutdown()

        self.writeMarkedSongs()

        player = file.MakePlayer(
            self.songDb, self.errorPopupCallback, self.songFinishedCallback)
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

        manager.OpenCPUControl()
        manager.setCpuSpeed('menu_fast')
        self.heldStartTicks = pygame.time.get_ticks()
        
        manager.InitPlayer(self)
        manager.OpenDisplay()

        # In case the screen has been resized during the song.
        self.setupScrollWindow()

        self.screenDirty = True

        # Discard any events that occurred while we were resetting the
        # display.
        for event in pygame.event.get():
            pass
        
    def __writeSongTitle(self, file, row):
        """ Renders the song title and artist onscreen, beginning at
        the specified row. """
        
        winWidth, winHeight = manager.displaySize
        winCenter = winWidth / 2

        # Word-wrap the title
        for line in manager.WordWrapText(file.Title, self.titleFont, winWidth):
            line = line.strip()
            text = self.titleFont.render(line, True, (255,255,255))
            rect = text.get_rect()
            rect = rect.move(winCenter - rect.centerx, row)
            manager.display.blit(text, rect)
            row += self.titleHeight

        # Now word-wrap the artist
        if file.Artist:
            row += 10
            for line in manager.WordWrapText(file.Artist, self.subtitleFont, winWidth):
                line = line.strip()
                text = self.subtitleFont.render(line, True, (255,255,255))
                rect = text.get_rect()
                rect = rect.move(winCenter - rect.centerx, row)
                manager.display.blit(text, rect)
                row += self.subtitleHeight

        return row
        

    def rowDown(self, count):
        self.currentRow = (self.currentRow + count) % len(self.songDb.SongList)
        self.screenDirty = True

    def rowUp(self, count):
        self.currentRow = (self.currentRow - count) % len(self.songDb.SongList)
        self.screenDirty = True

    def pageDown(self, count):
        self.rowDown(count * self.numRows)

    def pageUp(self, count):
        self.rowUp(count * self.numRows)

    def letterDown(self, count):
        # Go to the next "letter".
        file = self.songDb.SongList[self.currentRow]
        currentLetter = (self.songDb.GetSortKey(file)[0] or ' ')[0]
        
        row = (self.currentRow + 1) % len(self.songDb.SongList)
        file = self.songDb.SongList[row]
        letter = (self.songDb.GetSortKey(file)[0] or ' ')[0]
        while row != self.currentRow and letter == currentLetter:
            row = (row + 1) % len(self.songDb.SongList)
            file = self.songDb.SongList[row]
            letter = (self.songDb.GetSortKey(file)[0] or ' ')[0]
        
        self.currentRow = row
        self.screenDirty = True

    def letterUp(self, count):
        # Go to the previous "letter".
        file = self.songDb.SongList[self.currentRow]
        currentLetter = (self.songDb.GetSortKey(file)[0] or ' ')[0]
        
        row = (self.currentRow - 1) % len(self.songDb.SongList)
        file = self.songDb.SongList[row]
        letter = (self.songDb.GetSortKey(file)[0] or ' ')[0]
        while row != self.currentRow and letter == currentLetter:
            row = (row - 1) % len(self.songDb.SongList)
            file = self.songDb.SongList[row]
            letter = (self.songDb.GetSortKey(file)[0] or ' ')[0]
        
        self.currentRow = row
        self.screenDirty = True

    def changeSort(self):
        file = self.songDb.SongList[self.currentRow]

        sort = None
        if self.songDb.Sort == 'title':
            if self.songDb.GotArtists:
                sort = 'artist'
            else:
                sort = 'filename'
        elif self.songDb.Sort == 'artist':
            sort = 'filename'
        else:  # 'filename'
            if self.songDb.GotTitles:
                sort = 'title'
            elif self.songDb.GotArtists:
                sort = 'artist'

        if not sort:
            # No need to change anything.
            return

        sortApplied = self.songDb.SelectSort(sort, allowResort = False)
        if not sortApplied:
            # Changing the sort will require re-sorting the list.  Pop
            # up a message indicating we're doing this.  This is
            # particularly necessary for low-end CPU's, for which this
            # process might take a few seconds, like the GP2X.
            manager.setCpuSpeed('load')
            manager.display.fill((0,0,0))
            winWidth, winHeight = manager.displaySize
            winCenterX = winWidth / 2
            winCenterY = winHeight / 2
            text = self.subtitleFont.render("Sorting", True, (255,255,255))
            rect = text.get_rect()
            rect = rect.move(winCenterX - rect.centerx,
                             winCenterY - rect.centery)
            manager.display.blit(text, rect)
            pygame.display.flip()
            self.songDb.SelectSort(sort, allowResort = True)

        if file.sameSongs:
            # If we were on the filename list, we might have been looking
            # at a file that doesn't actually appear in the artist or
            # title list.  Be sure we look up the one that does appear.
            file = file.sameSongs[0]

        self.currentRow = bisect.bisect_left(self.songDb.SongList, file)
        self.screenDirty = True

    def goToSearch(self, searchString):
        """ Sets the current row to the item beginning with
        searchString.  Assumes the FileList has previously been sorted
        by a call to SelectSort(). """

        ss = pykdb.SongStruct(searchString, self.songDb.Settings,
                              searchString, searchString, searchString)
        self.currentRow = bisect.bisect_left(self.songDb.SongList, ss)
        if self.currentRow == len(self.songDb.SongList):
            self.currentRow = 0

        self.screenDirty = True


    def handleRepeatable(self, type, key, mod, count):
        if type == pygame.KEYDOWN:
            if key == pygame.K_DOWN and (mod & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT | pygame.KMOD_LMETA | pygame.KMOD_RMETA)):
                self.pageDown(count)
            elif key == pygame.K_UP and (mod & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT | pygame.KMOD_LMETA | pygame.KMOD_RMETA)):
                self.pageUp(count)
            elif key == pygame.K_DOWN:
                self.rowDown(count)
            elif key == pygame.K_UP:
                self.rowUp(count)
            elif key == pygame.K_RIGHT:
                self.letterDown(count)
            elif key == pygame.K_LEFT:
                self.letterUp(count)
            elif key == pygame.K_PAGEDOWN:
                self.pageDown(count)
            elif key == pygame.K_PAGEUP:
                self.pageUp(count)

        elif type == pygame.JOYBUTTONDOWN:
            if key == GP2X_BUTTON_DOWN:
                if self.ShoulderRHeld:
                    self.pageDown(count)
                elif self.ShoulderLHeld:
                    pass
                else:
                    self.rowDown(count)
                    
            elif key == GP2X_BUTTON_UP:
                if self.ShoulderRHeld:
                    self.pageUp(count)
                elif self.ShoulderLHeld:
                    pass
                else:
                    self.rowUp(count)

            elif key == GP2X_BUTTON_RIGHT:
                self.letterDown(count)
            elif key == GP2X_BUTTON_LEFT:
                self.letterUp(count)

    def doStuff(self):
        pykPlayer.doStuff(self)

        if self.screenDirty:
            self.paintWindow()
            self.screenDirty = False

        if self.heldKey:
            elapsed = pygame.time.get_ticks() - self.heldStartTicks
            repeat = 0
            if elapsed > 4000:
                repeat = int((elapsed - 4000) / 5.) + 256
            else:
                repeat = int(math.pow((elapsed / 1000.), 4))

            if elapsed > 1000:
                manager.setCpuSpeed('menu_fast')
            elif manager.cpuSpeed != 'menu_fast':
                manager.setCpuSpeed('menu_slow')

            if repeat > self.heldRepeat:
                self.handleRepeatable(self.heldKey[0], self.heldKey[1],
                                      self.heldKey[2], repeat - self.heldRepeat)
                self.heldRepeat = repeat
        else:
            elapsed = pygame.time.get_ticks() - self.heldStartTicks
            if elapsed > 20000:
                manager.setCpuSpeed('menu_idle')
            elif elapsed > 2000:
                manager.setCpuSpeed('menu_slow')

    def handleEvent(self, event):
        if self.selectedSong:
            self.handleSongEvent(event)
        else:
            self.handleMainEvent(event)

    def handleSongEvent(self, event):
        """ The user has already selected a song, and now has to
        select the specific version of it he/she meant to play. """

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_TAB:
                # Back out to the main index.
                self.selectedSong = None
                self.screenDirty = True

                # Don't continue.  If we call up to pykPlayer, it will
                # shut us down with the escape key.
                return

            elif event.key == pygame.K_RETURN:
                self.selectSong()

            elif event.key == pygame.K_UP:
                self.selectedSongRow = max(self.selectedSongRow - 1, 0)
                self.screenDirty = True

            elif event.key == pygame.K_DOWN:
                self.selectedSongRow = min(self.selectedSongRow + 1, len(self.selectedSong.sameSongs) - 1)
                self.screenDirty = True

            elif event.key == pygame.K_F1:
                # F1: mark song for later inspection.
                self.markCurrentSongFile()

        elif event.type == pygame.QUIT:
            self.running = False

        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONDOWN:
            button = event.button

            if button == GP2X_BUTTON_UPLEFT or button == GP2X_BUTTON_UPRIGHT:
                button = GP2X_BUTTON_UP
            elif button == GP2X_BUTTON_DOWNLEFT or button == GP2X_BUTTON_DOWNRIGHT:
                button = GP2X_BUTTON_DOWN
                
            if button == GP2X_BUTTON_Y or button == GP2X_BUTTON_A or button == GP2X_BUTTON_SELECT:
                self.selectedSong = None
                self.screenDirty = True
                return
            elif button == GP2X_BUTTON_START or \
                 button == GP2X_BUTTON_X or \
                 button == GP2X_BUTTON_B:
                self.selectSong()
            elif button == GP2X_BUTTON_UP:
                self.selectedSongRow = max(self.selectedSongRow - 1, 0)
                self.screenDirty = True
            elif button == GP2X_BUTTON_DOWN:
                self.selectedSongRow = min(self.selectedSongRow + 1, len(self.selectedSong.sameSongs) - 1)
                self.screenDirty = True
            elif button == GP2X_BUTTON_CLICK:
                # F1: mark song for later inspection.
                self.markCurrentSongFile()

        pykPlayer.handleEvent(self, event)

    def handleMainEvent(self, event):
        """ Handles events on the main 'select a song' index. """
        
        if event.type == pygame.KEYDOWN:
            if self.searchString and (event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE):
                # Backing up on the search.
                self.searchString = self.searchString[:-1]
                self.goToSearch(self.searchString)
                return
            if event.unicode and event.unicode[0] >= ' ':
                # The user has typed a keystroke that counts toward a
                # search.
                if event.key in self.CommandKeys:
                    # Except any one of these keys, which are reserved
                    # for font zoom and other command navigation.
                    pass
                elif event.key in self.FirstCommandKeys and not self.searchString:
                    # These keys are used for navigation only if we
                    # haven't already started typing.
                    pass
                else:
                    self.searchString += event.unicode
                    self.goToSearch(self.searchString)
                    return
            if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                # Don't count these keys as wiping out the search.
                return

            self.searchString = ''
            self.heldKey = (pygame.KEYDOWN, event.key, event.mod)
            self.heldStartTicks = pygame.time.get_ticks()
            self.heldRepeat = 0

            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_RETURN:
                self.selectSong()
            elif event.key == pygame.K_TAB:
                self.changeSort()
            elif event.key == pygame.K_F1:
                # F1: mark song for later inspection.
                self.markCurrentSongFile()
            else:
                self.handleRepeatable(pygame.KEYDOWN, event.key, event.mod, 1)

        elif event.type == pygame.KEYUP:
            self.heldKey = None
            self.heldStartTicks = pygame.time.get_ticks()

        elif event.type == pygame.QUIT:
            self.running = False

        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONDOWN:
            button = event.button

            # Map these diagonal buttons to the nearest up/down
            # equivalent.  This helps avoid the interruption of
            # scrolling because the GP2X joystick drifts too far left
            # or right.
            if button == GP2X_BUTTON_UPLEFT or button == GP2X_BUTTON_UPRIGHT:
                button = GP2X_BUTTON_UP
            elif button == GP2X_BUTTON_DOWNLEFT or button == GP2X_BUTTON_DOWNRIGHT:
                button = GP2X_BUTTON_DOWN
                
            self.heldKey = (pygame.JOYBUTTONDOWN, button, 0)
            self.heldStartTicks = pygame.time.get_ticks()
            self.heldRepeat = 0

            if button == GP2X_BUTTON_Y:
                self.running = False
            elif button == GP2X_BUTTON_START or \
                 button == GP2X_BUTTON_X or \
                 button == GP2X_BUTTON_B:
                self.selectSong()
            elif button == GP2X_BUTTON_A:
                self.changeSort()
            elif button == GP2X_BUTTON_SELECT:
                # Break out so this one won't fall through to
                # pykPlayer, which would shut us down.
                return
            elif button == GP2X_BUTTON_CLICK:
                # F1: mark song for later inspection.
                self.markCurrentSongFile()
            else:
                self.handleRepeatable(pygame.JOYBUTTONDOWN, button, 0, 1)

        elif env == ENV_GP2X and event.type == pygame.JOYBUTTONUP:
            button = event.button

            if button == GP2X_BUTTON_UPLEFT or button == GP2X_BUTTON_UPRIGHT:
                button = GP2X_BUTTON_UP
            elif button == GP2X_BUTTON_DOWNLEFT or button == GP2X_BUTTON_DOWNRIGHT:
                button = GP2X_BUTTON_DOWN

            if self.heldKey == (pygame.JOYBUTTONDOWN, button, 0):
                self.heldKey = None
                self.heldStartTicks = pygame.time.get_ticks()

        pykPlayer.handleEvent(self, event)

    def errorPopupCallback(self, errorString, wait = True):
        print errorString

        manager.InitPlayer(self)
        manager.OpenDisplay()

        manager.display.fill((0,0,0))

        # Center the error message onscreen.
        winWidth, winHeight = manager.displaySize
        winCenter = winWidth / 2

        lines = manager.WordWrapText(errorString, self.subtitleFont, winWidth - X_BORDER * 2)

        row = (winHeight - len(lines) * self.subtitleHeight) / 2
        for line in lines:
            line = line.strip()
            text = self.subtitleFont.render(line, True, (255,255,255))
            rect = text.get_rect()
            rect = rect.move(winCenter - rect.centerx, row)
            manager.display.blit(text, rect)
            row += self.subtitleHeight

        pygame.display.flip()
        self.screenDirty = True

        if not wait:
            return

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

    def showProgressCallback(self, label, progress):
        """ This is called by the MiniBusyCancelDialog to show
        progress as we're scanning the database. """
        
        manager.InitPlayer(self)
        manager.OpenDisplay()

        manager.display.fill((0,0,0))

        # Center the error message onscreen.
        winWidth, winHeight = manager.displaySize
        winCenter = winWidth / 2

        lines = manager.WordWrapText(label, self.subtitleFont, winWidth - X_BORDER * 2)

        row = winHeight / 2 - 2 * self.subtitleHeight
        for line in lines:
            line = line.strip()
            text = self.subtitleFont.render(line, True, (255,255,255))
            rect = text.get_rect()
            rect = rect.move(winCenter - rect.centerx, row)
            manager.display.blit(text, rect)
            row += self.subtitleHeight

        # Now draw the progress bar.
        width = winWidth / 2
        height = self.subtitleHeight

        top = winHeight / 2
        left = winWidth / 2 - width / 2
        rect = pygame.Rect(left, top, width, height)
        manager.display.fill((255, 255, 255), rect)

        fill = int((width - 2) * progress + 0.5)
        rect = pygame.Rect(left + 1 + fill, top + 1, width - 2 - fill, height - 2)
        manager.display.fill((0, 0, 0), rect)

        pygame.display.flip()
        self.screenDirty = True

    def songFinishedCallback(self):
        self.songDb.CleanupTempFiles()

    def doResize(self, newSize):
        # This will be called internally whenever the window is
        # resized for any reason, either due to an application resize
        # request being processed, or due to the user dragging the
        # window handles.
        self.setupScrollWindow()
        self.screenDirty = True

    
class MiniBusyCancelDialog(pykdb.BusyCancelDialog):
    def __init__(self, app):
        pykdb.BusyCancelDialog.__init__(self)
        self.app = app
        
    def SetProgress(self, label, progress):
        """ Update the progress label onscreen. """
        self.app.showProgressCallback(label, progress)

def main():
    app = App()
    app.start()

if __name__ == "__main__":
    sys.exit(main())


