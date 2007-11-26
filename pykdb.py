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

""" This module provides support for the PyKaraoke song database, as
well as the user's settings file. """

import pykversion
import pygame
from pykconstants import *
from pykenv import env
import pykar, pycdg, pympg
import os, cPickle, zipfile, codecs, sys

# The amount of time to wait, in milliseconds, before yielding to the
# app for windowing updates during a long update process.
YIELD_INTERVAL = 1000

# The maximum number of zip files we will attempt to store in our zip
# file cache.
MAX_ZIP_FILES = 10

class AppYielder:
    """ This is a simple class that knows how to yield control to the
    windowing system every once in a while.  It is passed to functions
    like SearchDatabase and BuildSearchDatabase--tasks which might
    take a while to perform.

    This class is just an abstract base class and does nothing.  Apps
    should subclass it and override Yield() to make any use from
    it. """
    
    def __init__(self):
        self.lastYield = pygame.time.get_ticks()

    def ConsiderYield(self):
        now = pygame.time.get_ticks()
        if now - self.lastYield >= YIELD_INTERVAL:
            self.Yield()
            self.lastYield = now

    def Yield(self):
        """ Override this method to actually yield control to the
        windowing system. """
        pass

class BusyCancelDialog:

    """This class implements a busy dialog to show a task is
    progressing, and it includes a cancel button the user might click
    on to interrupt the task.  This is just an abstract base class and
    does nothing.  Apps should subclass from it. """
    
    def __init__(self):
        self.Clicked = False

    def Show(self):
        pass

    def Destroy(self):
        pass

class SongData:
    """This class is returned by SongStruct.GetSongData(), below.  It
    represents either a song file that exists on disk (and must still
    be read), or it is a song file that was found in a zip archive
    (and its data is available now)."""

    def __init__(self, filename, data):
        self.filename = filename
        self.tempFilename = None
        self.data = data
        self.Ext = os.path.splitext(filename)[1].lower()

        # By convention, if data is passed as None to the constructor,
        # that means this file is a true file that exists on disk.  On
        # the other hand, if data is not None, then this is not a true
        # file, and data contains its contents.
        self.trueFile = (data == None)

    def GetData(self):
        """Returns the actual data of the file.  If the file has not
        yet been read, this will read it and return the data."""

        if self.data != None:
            # The file has already been read; return that data.
            return self.data

        # The file has not yet been read
        self.data = open(self.filename, 'rb').read()
        return self.data

    def GetFilepath(self):
        """Returns a full pathname to the file.  If the file does not
        exist on disk, this will write it to a temporary file and
        return the name of that file."""

        if self.trueFile:
            # The file exists on disk already; just return its
            # pathname.
            return self.filename

        if not self.tempFilename:
            # The file does not exist on disk already; we have to write it
            # to a temporary file.
            prefix = globalSongDB.CreateTempFileNamePrefix()
            basename = os.path.basename(self.filename)
            self.tempFilename = prefix + basename
            open(self.tempFilename, 'wb').write(self.data)
            
        return self.tempFilename
        

# This functor is declared globally.  It is assigned by
# SongDB.SelectSort(), so we can use bisect to search through
# the list also.  This is an ugly hack around the fact that bisect has
# no facility to receive a key parameter, like sort does.
fileSortKey = None

# SongStruct is used to store song details for the database. Separate
# Titles allow us to cut off the pathname, use ID3 tags (when
# supported) etc. For ZIP files there is an extra member - for the
# stored filename, which might be different from the title if the
# stored file is in a stored sub-dir, or is an ID tag.
class SongStruct:
    def __init__(self, Filepath, Title = None, Artist = None, ZipStoredName = None):
        self.Filepath = Filepath    # Full path to file or ZIP file
        self.Title = Title or ''    # (optional) Title for display in playlist
        self.Artist = Artist or ''  # (optional) Artist for display
        self.ZipStoredName = ZipStoredName # Filename stored in ZIP

        # If the file ends in '.', assume we got it via tab-completion
        # on a filename, and it really is meant to end in '.cdg'.
        if self.Filepath != '' and self.Filepath[-1] == '.':
            self.Filepath += 'cdg'

        if ZipStoredName:
            self.DisplayFilename = os.path.basename(ZipStoredName)
        else:
            self.DisplayFilename = os.path.basename(Filepath)
            

    def MakePlayer(self, errorNotifyCallback, doneCallback):
        """Creates and returns a player of the appropriate type to
        play this file, if possible; or returns None if the file
        cannot be played (in which case, the errorNotifyCallback will
        have already been called with the error message). """

        ext = os.path.splitext(self.DisplayFilename)[1]
        
        constructor = None
        
        if ext.lower() == ".cdg":
            constructor = player = pycdg.cdgPlayer
        elif (ext.lower() == ".kar") or (ext.lower() == ".mid"):
            constructor = player = pykar.midPlayer
        elif (ext.lower() == ".mpg") or (ext.lower() == ".mpeg"):
            constructor = player = pympg.mpgPlayer
        # TODO basic mp3/ogg player
        else:
            errorNotifyCallback("Unsupported file format " + ext)
            return None

        # Try to open the song file.
        try:
            player = constructor(self, errorNotifyCallback, doneCallback)
        except:
            errorNotifyCallback("Error opening file.\n%s\n%s" % (sys.exc_info()[0], sys.exc_info()[1]))
            return None

        return player

    def GetSongDatas(self):
        """Returns a list of SongData objects; see SongData.

        Usually there is only one element in the list: the file named
        by this SongStruct.  In the case of .cdg files, however, there
        may be more tuples; the first tuple will be the file named by
        this SongStruct, and the remaining tuples will correspond to
        other files with the same basenames but different extensions
        (so that the .mp3 or .ogg associated with a cdg file may be
        recovered)."""

        songDatas = []

        if not self.Filepath:
            return songDatas

        if not os.path.exists(self.Filepath):
            error = 'No such file: %s' % (self.Filepath)
            raise error

        dir = os.path.dirname(self.Filepath)
        if dir == "":
            dir = "."
        root, ext = os.path.splitext(self.Filepath)
        prefix = os.path.basename(root + ".")
        
        if self.ZipStoredName:
            # It's in a ZIP file; unpack it.
            zip = globalSongDB.GetZipFile(self.Filepath)
            filelist = [self.ZipStoredName]

            root, ext = os.path.splitext(self.ZipStoredName)
            prefix = os.path.basename(root + ".")
            
            if ext.lower() == ".cdg":
                # In addition to the .cdg file, we also have to get
                # out the mp3/ogg/whatever audio file comes with the
                # .cdg file.  Just extract out any files that have the
                # same basename.
                for name in zip.namelist():
                    if name != self.ZipStoredName and name.startswith(prefix):
                        filelist.append(name)

            # We'll continue looking for matching files outside the
            # zip, too.

            for file in filelist:
                data = zip.read(file)
                songDatas.append(SongData(file, data))
        else:
            # A non-zipped file; this is an easy case.
            songDatas.append(SongData(self.Filepath, None))

        if ext.lower() == ".cdg":
            # In addition to the .cdg file, we also have to find the
            # mp3/ogg/whatever audio file comes with the .cdg file,
            # just as above, when we were pulling them out of the zip
            # file.  This time we are just looking for loose files on
            # the disk.
            for file in os.listdir(dir):
                if file.startswith(prefix):
                    path = os.path.join(dir, file)
                    if path != self.Filepath:
                        songDatas.append(SongData(path, None))

        # Now we've found all the matching files.
        return songDatas


    def __cmp__(self, other):
        """Define a sorting order between SongStruct objects.  This is
        used in bisect, to quickly search for a SongStruct in a sorted
        list.  It relies on fileSortKey (above) having being filled in
        already. """
        global fileSortKey
        
        a = fileSortKey(self)
        b = fileSortKey(other)
        if a == b:
            return cmp(id(self), id(other))
        if a < b:
            return -1
        return 1

# SettingsStruct used as storage only for settings. The instance
# can be pickled to save all user's settings.
class SettingsStruct:
    def __init__(self):
        self.Version = pykversion.PYKARAOKE_VERSION_STRING
    
        # Set the default settings, in case none are stored on disk
        self.FolderList = []
        self.FileExtensions = [".cdg", ".mpg", ".mpeg", ".kar", ".mid"]
        self.LookInsideZips = True
        self.ReadTitlesTxt = True
        self.FullScreen = False
        self.DefaultCharset = "iso-8859-1"	# Default text charset in karaoke files



# Song database class with methods for building the database, searching etc
class SongDB:
    def __init__(self):
        # Filepaths and titles are stored in a list of SongStruct instances
        self.SongList = []

        # A cache of zip files.
        self.ZipFiles = []

        # Some databases may omit either or both of titles and
        # artists, relying on filenames instead.
        self.GotTitles = False
        self.GotArtists = False
    
        # Create a SettingsStruct instance for storing settings
        # in case none are stored.
        self.Settings = SettingsStruct()
        
        # All temporary files use this prefix
        self.TempFilePrefix = "00Pykar__"

        self.SaveDir = self.getSaveDirectory()
        self.TempDir = self.getTempDirectory()
        self.CleanupTempFiles()

    def getSaveDirectory(self):
        """ Returns the directory in which the settings files should
        be saved. """

        # If we have PYKARAOKE_DIR defined, use it.
        dir = os.getenv('PYKARAOKE_DIR')
        if dir:
            return dir

        # Without PYKARAOKE_DIR, use ~/.pykaraoke.  Try to figure that
        # out.
        homeDir = self.getHomeDirectory()
        return os.path.join(homeDir, ".pykaraoke")

    def getTempDirectory(self):
        """ Returns the directory in which temporary files should be
        saved. """
        dir = os.getenv('PYKARAOKE_TEMP_DIR')
        if dir:
            return dir

        dir = os.getenv('TEMP')
        if dir:
            return os.path.join(dir, 'pykaraoke')

        if env != ENV_WINDOWS:
            if os.path.exists('/tmp'):
                return '/tmp/pykaraoke'
        else:
            try:
                import win32api
                return os.path.join(win32api.GetTempPath(), 'pykaraoke')
            except:
                pass

        # If we can't find a good temp directory, use our save directory.
        return self.getSaveDirectory()

    def getHomeDirectory(self):
        """ Returns the user's home directory, if we can figure that
        out. """

        if env != ENV_GP2X:
            # First attempt: ask wx, if it's available.
            try:
                import wx
                return wx.GetHomeDir()
            except:
                pass

            # Second attempt: look in $HOME
            home = os.getenv('HOME')
            if home:
                return home

        # Give up and return the current directory.
        return '.'

    # Load settings and database if they are stored
    def LoadSettings (self, errorCallback):
        self.SongList = []
        
        # Load the settings file
        settings_filepath = os.path.join (self.SaveDir, "settings.dat")
        if os.path.exists (settings_filepath):
            file = open (settings_filepath, "rb")
            loadsettings = None
            try:
                loadsettings = cPickle.load (file)
            except:
                pass
            # Check settings are for the current version
            if (loadsettings and \
                loadsettings.Version == pykversion.PYKARAOKE_VERSION_STRING):
                self.Settings = loadsettings
            else:
                if errorCallback:
                   errorCallback("New version of PyKaraoke, clearing settings")
                   return
                
        # Load the database file
        db_filepath = os.path.join (self.SaveDir, "songdb.dat")
        if os.path.exists (db_filepath):
            file = open (db_filepath, "rb")
            self.SongList = cPickle.load (file)

        # Scan the songlist for titles and/or artists.
        for file in self.SongList:
            if file.Title:
                self.GotTitles = True
            if file.Artist:
                self.GotArtists = True


    # Save settings and database to the home/temp directory
    def SaveSettings (self):
        # Create the temp directory if it doesn't exist already
        if not os.path.exists (self.SaveDir):
            os.mkdir(self.SaveDir)
        # Save the settings file
        settings_filepath = os.path.join (self.SaveDir, "settings.dat")
        file = open (settings_filepath, "wb")
        cPickle.dump (self.Settings, file)

        # Save the database file
        db_filepath = os.path.join (self.SaveDir, "songdb.dat")
        file = open (db_filepath, "wb")
        cPickle.dump (self.SongList, file)
    
    def BuildSearchDatabase(self, yielder, busyDlg):
        # Zap the database and build again from scratch. Return False
        # if was cancelled.
        self.SongList = []

        return self.doSearch(self.Settings.FolderList, yielder, busyDlg)

    def AddFile(self, filename):
        """Adds just the indicated file to the DB.  If the file is a
        directory or a zip file, recursively scans within it and adds
        all the sub-files. """

        self.doSearch([filename], AppYielder(), BusyCancelDialog())

    def GetZipFile(self, filename):
        """Creates a ZipFile object corresponding to the indicated zip
        file on disk and returns it.  If there was already a ZipFile
        for this filename in the cache, just returns that one
        instead, saving on load time from repeatedly loading the same
        zip file. """

        for tuple in self.ZipFiles:
            cacheFilename, cacheZip = tuple
            if cacheFilename == filename:
                # Here is a zip file in the cache; move it to the
                # front of the list.
                self.ZipFiles.remove(tuple)
                self.ZipFiles.insert(0, tuple)
                return cacheZip

        # The zip file was not in the cache, create a new one and cache it.
        zip = zipfile.ZipFile(filename)
        if len(self.ZipFiles) >= MAX_ZIP_FILES:
            del self.ZipFiles[-1]
        self.ZipFiles.insert(0, (filename, zip))
        return zip

    def doSearch(self, fileList, yielder, busyDlg):
        """ This is the actual implementation of BuildSearchDatabase()
        and AddFile()."""
        
        cancelled = False
        self.BusyDlg = busyDlg
        self.BusyDlg.Show()

        self.titlesFiles = []
        self.filesByFullpath = {}
        for root_path in fileList:
            cancelled = self.fileScan (str(root_path), yielder)
            if cancelled == True:
                break

        # Now go back and read any titles.txt files we came across.
        # These will have meta-information about the files, such as
        # the title and/or artist.
        tmpfile_prefix = self.CreateTempFileNamePrefix()
        for fullpath, nameInZip in self.titlesFiles:
            if nameInZip != None:
                zip = self.GetZipFile(fullpath)
                lose, local_file = os.path.split(fullpath)
                tempfile = tmpfile_prefix + local_file
                unzipped_file = open (tempfile, "wb")
                unzipped_data = zip.read(nameInZip)
                unzipped_file.write(unzipped_data)
                unzipped_file.close()
                self.readTitles(tempfile, fullpath)
                try:
                    os.unlink(tempfile)
                except:
                    pass
            else:
                dirname, basename = os.path.split(fullpath)
                self.readTitles(fullpath, dirname)

        # These structures were just temporary, for use just while
        # scanning the directories.  Remove them now.
        del self.titlesFiles
        del self.filesByFullpath
            
        self.BusyDlg.Destroy()
        return cancelled

    def folderScan (self, FolderToScan, yielder):
        # Search for karaoke files inside the folder, looking inside ZIPs if
        # configured to do so. Function is recursive for subfolders.
        try:
            filedir_list = os.listdir(FolderToScan)
        except:
            print "Couldn't scan %s" % (FolderToScan)
            return False
        
        for item in filedir_list:
            if self.BusyDlg.Clicked == True:
                return (True)
            # Allow windows to refresh now and again while scanning
            yielder.ConsiderYield()
            full_path = os.path.join(FolderToScan, item)

            self.fileScan(full_path, yielder)

    def fileScan(self, full_path, yielder):
        # Recurse into subdirectories
        if os.path.isdir(full_path):
            cancelled = self.folderScan (full_path, yielder)
            if cancelled == True:
                return (True)
        # Store file details if it's a file type we're interested in
        else:
            root, ext = os.path.splitext(full_path)
            # Non-ZIP files
            if self.Settings.ReadTitlesTxt and full_path.endswith('titles.txt'):
                # Save this titles.txt file for reading later.
                self.titlesFiles.append((full_path, None))
            elif self.IsExtensionValid(ext):
                self.addSong(SongStruct(full_path))
            # Look inside ZIPs if configured to do so
            elif self.Settings.LookInsideZips and ext.lower() == ".zip":
                try:
                    if zipfile.is_zipfile(full_path):
                        zip = self.GetZipFile(full_path)
                        for filename in zip.namelist():
                            root, ext = os.path.splitext(filename)
                            if self.Settings.ReadTitlesTxt and filename.endswith('titles.txt'):
                                # Save this titles.txt file for reading later.
                                self.titlesFiles.append((full_path, filename))
                            elif self.IsExtensionValid(ext):
                                # Python zipfile only supports deflated and stored
                                info = zip.getinfo(filename)
                                if info.compress_type == zipfile.ZIP_STORED or info.compress_type == zipfile.ZIP_DEFLATED:
                                    #print ("Adding song %s in ZIP file %s"%(filename, full_path))
                                    self.addSong(SongStruct(full_path, ZipStoredName = filename))
                                else:
                                    print ("ZIP member %s compressed with unsupported type (%d)"%(filename,info.compress_type))
                except:
                    print "Error looking inside zip " + full_path
        return (False)

    def readTitles(self, catalogPathname, dirname):
        try:
            catalogFile = codecs.open(catalogPathname, "r", "utf-8")
        except:
            print "Could not open titles file %s" % (catalogPathname)
            return
        
        catalog = catalogFile.readlines()

        for line in catalog:
            line = line.strip()
            if line:
                tuple = line.split('\t')
                if len(tuple) == 2:
                    filename, title = tuple
                    artist = ''
                elif len(tuple) == 3:
                    filename, title, artist = tuple
                else:
                    print "Invalid line in %s:\n%s" % (catalogPathname, line)
                    continue

                # Allow a forward slash in the file to stand in for
                # whatever the OS's path separator is.
                filename = filename.replace('/', os.path.sep)

                pathname = os.path.join(dirname, filename)
                file = self.filesByFullpath.get(pathname, None)
                if file is None:
                    print "Unknown file in %s:\n%s" % (catalogPathname, filename)
                else:
                    file.Title = title.strip()
                    file.Artist = artist.strip()
                    if file.Title:
                        self.GotTitles = True
                    if file.Artist:
                        self.GotArtists = True

    # Add a folder to the database search list
    def FolderAdd (self, FolderPath):
        if FolderPath not in self.Settings.FolderList:
            self.Settings.FolderList.append(FolderPath)
        
    # Remove a folder from the database search list
    def FolderDel (self, FolderPath):
        self.Settings.FolderList.remove(FolderPath)
    
    # Get the list of folders currently set up for the database
    def GetFolderList (self):
        return self.Settings.FolderList

    # Search the database for occurrences of the search terms.
    # If there are multiple terms, all must exist for a match.
    # The search is case-insensitive and searches both the title
    # and the pathname.
    # Returns a list of SongStruct instances.
    def SearchDatabase (self, SearchTerms, yielder):
        # Display a busy cursor while searching, yielding now and again
        # to update the GUI.
        ResultsList = []
        LowerTerms = SearchTerms.lower()
        TermsList = LowerTerms.split()
        for song in self.SongList:
            yielder.ConsiderYield()
            LowerTitle = song.Title.lower()
            LowerArtist = song.Artist.lower()
            LowerPath = song.DisplayFilename.lower()
            # If it's a zip file, also include the zip filename
            if song.ZipStoredName:
                LowerZipName = os.path.basename(song.Filepath).lower()
            else:
                LowerZipName = "" 
            misses = 0
            for term in TermsList:
                if (term not in LowerTitle) and \
                   (term not in LowerArtist) and \
                   (term not in LowerZipName) and \
                   (term not in LowerPath):
                    misses = misses + 1
            if misses == 0:
                ResultsList.append(song)
        return ResultsList
        
    # Get the song database size (number of songs)
    def GetDatabaseSize (self):
        return len(self.SongList)

    # Check if the passed file extension is configured for this database
    def IsExtensionValid (self, extension):
        if extension.lower() in self.Settings.FileExtensions:
            return True
        else:
            return False

    # Change all file extensions (always compare in lower case)
    def FileExtensionsChange (self, extensionsList):
        self.Settings.FileExtensions = extensionsList
        for index in range (len(self.Settings.FileExtensions)):
            self.Settings.FileExtensions[index] = self.Settings.FileExtensions[index].lower()

    # Create a directory for use by PyKaraoke for temporary zip files
    # and for saving the song database and settings.
    # This will be under the Wx idea of the home directory.
    def CreateTempDir (self):
        if not os.path.exists(self.TempDir):
            os.mkdir (self.TempDir)

    # Create temporary filename prefix. Returns a path and filename
    # prefix which can be used as a base string for temporary files.
    # You must clean them up when done using CleanupTempFiles().
    # Also automatically creates a temporary directory if one doesn't
    # exist already.
    def CreateTempFileNamePrefix (self):
        self.CreateTempDir()
        full_prefix = os.path.join (self.TempDir, self.TempFilePrefix)
        return full_prefix
            
    # Clean up any temporary (unzipped) files on startup/exit/end of song
    def CleanupTempFiles (self):
        if os.path.exists (self.TempDir):
            filedir_list = os.listdir(self.TempDir)
            for item in filedir_list:
                if item.startswith(self.TempFilePrefix):
                    full_path = os.path.join (self.TempDir, item)
                    try:
                        os.unlink(full_path)
                    except:
                        pass

    def SelectSort(self, sort):
        """Sorts the list of songs in order according to the indicated
        key, which must be one of 'title', 'artist', or 'filename'.
        Also sets self.GetSongTuple to a functor which, when called, returns a
        3-tuple of strings suitable for displaying for each song,
        where the first string of each tuple is the sort key. """
        
        self.Sort = sort
        global fileSortKey
        
        if self.Sort == 'title':
            if self.GotArtists:
                self.GetSongTuple = self.getSongTupleTitleArtistFilename
                fileSortKey = self.getSongTupleTitleArtistFilenameSortKey
            else:
                self.GetSongTuple = self.getSongTupleTitleFilenameArtist
                fileSortKey = self.getSongTupleTitleFilenameArtistSortKey

        elif self.Sort == 'artist':
            if self.GotTitles:
                self.GetSongTuple = self.getSongTupleArtistTitleFilename
                fileSortKey = self.getSongTupleArtistTitleFilenameSortKey
            else:
                self.GetSongTuple = self.getSongTupleArtistFilenameTitle
                fileSortKey = self.getSongTupleArtistFilenameTitleSortKey

        elif self.Sort == 'filename':
            if self.GotTitles:
                self.GetSongTuple = self.getSongTupleFilenameTitleArtist
                fileSortKey = self.getSongTupleFilenameTitleArtistSortKey
            else:
                self.GetSongTuple = self.getSongTupleFilenameArtistTitle
                fileSortKey = self.getSongTupleFilenameArtistTitleSortKey

        self.SongList.sort(key = fileSortKey)

    def getSongTupleTitleArtistFilename(self, file):
        return (file.Title, file.Artist, file.DisplayFilename)

    def getSongTupleTitleFilenameArtist(self, file):
        return (file.Title, file.DisplayFilename, file.Artist)

    def getSongTupleArtistTitleFilename(self, file):
        return (file.Artist, file.Title, file.DisplayFilename)

    def getSongTupleArtistFilenameTitle(self, file):
        return (file.Artist, file.DisplayFilename, file.Title)

    def getSongTupleFilenameTitleArtist(self, file):
        return (file.DisplayFilename, file.Title, file.Artist)

    def getSongTupleFilenameArtistTitle(self, file):
        return (file.DisplayFilename, file.Artist, file.Title)

    def getSongTupleTitleArtistFilenameSortKey(self, file):
        return (file.Title.lower(), file.Artist.lower(), file.DisplayFilename.lower(), id(file))

    def getSongTupleTitleFilenameArtistSortKey(self, file):
        return (file.Title.lower(), file.DisplayFilename.lower(), file.Artist.lower(), id(file))

    def getSongTupleArtistTitleFilenameSortKey(self, file):
        return (file.Artist.lower(), file.Title.lower(), file.DisplayFilename.lower(), id(file))

    def getSongTupleArtistFilenameTitleSortKey(self, file):
        return (file.Artist.lower(), file.DisplayFilename.lower(), file.Title.lower(), id(file))

    def getSongTupleFilenameTitleArtistSortKey(self, file):
        return (file.DisplayFilename.lower(), file.Title.lower(), file.Artist.lower(), id(file))

    def getSongTupleFilenameArtistTitleSortKey(self, file):
        return (file.DisplayFilename.lower(), file.Artist.lower(), file.Title.lower(), id(file))

    def addSong(self, file):
        self.SongList.append(file)
        if file.Title:
            self.GotTitles = True
        if file.Artist:
            self.GotArtists = True

        # Also record the file in the temporary map by fullpath name,
        # so we can cross-reference it with a titles.txt file that
        # might reference it.
        fullpath = file.Filepath
        if file.ZipStoredName:
            fullpath = os.path.join(fullpath, file.ZipStoredName)
        self.filesByFullpath[fullpath] = file

globalSongDB = SongDB()
