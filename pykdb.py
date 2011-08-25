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

""" This module provides support for the PyKaraoke song database, as
well as the user's settings file. """

import pygame
from pykconstants import *
from pykenv import env
import pykar, pycdg, pympg
import os, cPickle, zipfile, codecs, sys, time
import types
from cStringIO import StringIO
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

# The amount of time to wait, in milliseconds, before yielding to the
# app for windowing updates during a long update process.
YIELD_INTERVAL = 1000

# The maximum number of zip files we will attempt to store in our zip
# file cache.
MAX_ZIP_FILES = 10

# Increment this version number whenever the settings version changes
# (which may not necessarily change with each PyKaraoke release).
# This will force users to re-enter their configuration information.
SETTINGS_VERSION = 6

# Increment this version number whenever the database version changes
# (which will also hopefully be infrequently).
DATABASE_VERSION = 2

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

    def SetProgress(self, label, progress):
        pass

    def Destroy(self):
        pass

class SongData:
    """This class is returned by SongStruct.GetSongDatas(), below.  It
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
            # Add the tempfile prefix as well as the time to make the
            # filename unique. This works around a bug
            # in pygame.mixer.music on Windows which stops us deleting
            # temp files until another song is loaded, preventing the
            # same song from being played twice in a row.
            self.tempFilename = prefix + str(time.time()) + basename
            open(self.tempFilename, 'wb').write(self.data)

        return self.tempFilename


# This functor is declared globally.  It is assigned by
# SongDB.SelectSort(), so we can use bisect to search through
# the list also.  This is an ugly hack around the fact that bisect has
# no facility to receive a key parameter, like sort does.
fileSortKey = None

class SongStruct:
    """ This corresponds to a single song file entry, e.g. a .kar
    file, or a .mp3/.cdg filename pair.  The file might correspond to
    a physical file on disk, or to a file within a zip file. """

    # Type codes.
    T_KAR = 0
    T_CDG = 1
    T_MPG = 2

    def __init__(self, Filepath, settings,
                 Title = None, Artist = None, ZipStoredName = None, DatabaseAdd = False):
        self.Filepath = Filepath    # Full path to file or ZIP file
        self.ZipStoredName = ZipStoredName # Filename stored in ZIP

        # Assume there will be no title/artist info found
        self.Title = Title or ''    # (optional) Title for display in playlist
        self.Artist = Artist or ''  # (optional) Artist for display
        self.Disc = '' # (optional) Disc for display
        self.Track = -1 # (optional) Track for display

        # Check to see if we are deriving song information from the filename
        if settings.CdgDeriveSongInformation:
            try:
                self.Title = self.ParseTitle(Filepath, settings)    # Title for display in playlist
                self.Artist = self.ParseArtist(Filepath, settings)  # Artist for display
                self.Disc = self.ParseDisc(Filepath, settings)      # Disc for display
                self.Track = self.ParseTrack(Filepath, settings)     # Track for display
            except:
                # Filename did not match requested scheme, set the title to the filepath
                # so that the structure is still created, but without any additional info
                #print "Filename format does not match requested scheme: %s" % Filepath
                self.Title = os.path.basename(Filepath)

                # If this SongStruct is being used to add to the database, and we are
                # configured to exclude non-matching files, raise an exception. Otherwise
                # allow it through. For database adds where we are not excluding such
                # files the song will still be added to the database. For non-database
                # adds we don't care anyway, we just want a SongStruct for passing around.
                if DatabaseAdd and settings.ExcludeNonMatchingFilenames:
                    raise KeyError, "Excluding non-matching file: %s" % self.Title

        # This is a list of other song files that share the same
        # artist and title data.
        self.sameSongs = []

        # This is a pointer to the TitleStruct object that defined
        # this song file, or None if it was not defined.
        self.titles = None

        # If the file ends in '.', assume we got it via tab-completion
        # on a filename, and it really is meant to end in '.cdg'.
        if self.Filepath != '' and self.Filepath[-1] == '.':
            self.Filepath += 'cdg'

        if ZipStoredName:
            self.DisplayFilename = os.path.basename(ZipStoredName)
            if isinstance(self.DisplayFilename, types.StringType):
                self.DisplayFilename = self.DisplayFilename.decode(settings.ZipfileCoding)
        else:
            self.DisplayFilename = os.path.basename(Filepath)
            if isinstance(self.DisplayFilename, types.StringType):
                self.DisplayFilename = self.DisplayFilename.decode(settings.FilesystemCoding)

        # Check the file type based on extension.
        self.Type = None
        ext = os.path.splitext(self.DisplayFilename)[1].lower()
        if ext in settings.KarExtensions:
            self.Type = self.T_KAR
        elif ext in settings.CdgExtensions:
            self.Type = self.T_CDG
        elif ext in settings.MpgExtensions:
            self.Type = self.T_MPG
            if ext == '.mpg' or ext == '.mpeg':
                self.MpgType = 'mpg'
            else:
                self.MpgType = ext[1:]

    def ParseTitle(self, filepath, settings):
        """ Parses the file path and returns the title of the song. If the filepath cannot be parsed a KeyError exception is thrown. If the settings contains a file naming scheme that we do not support a KeyError exception is thrown."""
        title = ''
        # Make sure we are to parse information
        if settings.CdgDeriveSongInformation:
            if settings.CdgFileNameType == 0: # Disc-Track-Artist-Title.Ext
                # Make sure we can parse the filepath
                if len(filepath.split("-")) == 4:
                    title = filepath.split("-")[3] # Find the Title in the filename
                else:
                    raise KeyError, "Invalid type for file: %s!" % filepath
            elif settings.CdgFileNameType == 1: # DiscTrack-Artist-Title.Ext
                # Make sure we can parse the filepath
                if len(filepath.split("-")) == 3:
                    title = filepath.split("-")[2] # Find the Title in the filename
                else:
                    raise KeyError, "Invalid type for file: %s!" % filepath
            elif settings.CdgFileNameType == 2: # Disc-Artist-Title.Ext
                # Make sure we can parse the filepath
                if len(filepath.split("-")) == 3:
                    title = filepath.split("-")[2] # Find the Title in the filename
                else:
                    raise KeyError, "Invalid type for file: %s!" % filepath
            elif settings.CdgFileNameType == 3: # Artist-Title.Ext
                # Make sure we can parse the filepath
                if len(filepath.split("-")) == 2:
                    title = filepath.split("-")[1] # Find the Title in the filename
                else:
                    raise KeyError, "Invalid type for file: %s!" % filepath
            else:
                raise KeyError, "File name type is invalid!"
            # Remove the first and last space
            title = title.strip(" ")
            # Remove the filename extension
            title = os.path.splitext(title)[0]
        #print "Title parsed: %s" % title
        return title

    def ParseArtist(self, filepath, settings):
        """ Parses the filepath and returns the artist of the song. """
        artist = ''
        # Make sure we are to parse information
        if settings.CdgDeriveSongInformation:
            if settings.CdgFileNameType == 0: # Disc-Track-Artist-Title.Ext
                artist = filepath.split("-")[2] # Find the Artist in the filename
            elif settings.CdgFileNameType == 1: # DiscTrack-Artist-Title.Ext
                artist = filepath.split("-")[1] # Find the Artist in the filename
            elif settings.CdgFileNameType == 2: # Disc-Artist-Title.Ext
                artist = filepath.split("-")[1] # Find the Artist in the filename
            elif settings.CdgFileNameType == 3: # Artist-Title.Ext
                artist = filepath.split("-")[0] # Find the Artist in the filename
                artist = os.path.basename(artist)
            else:
                raise KeyError, "File name type is invalid!"
            # Remove the first and last space
            artist = artist.strip(" ")
        #print "Artist parsed: %s" % artist
        return artist

    def ParseDisc(self, filepath, settings):
        """ Parses the filepath and returns the disc name of the song. """
        disc = ''
        # Make sure we are to parse information
        if settings.CdgDeriveSongInformation:
            if settings.CdgFileNameType == 0: # Disc-Track-Artist-Title.Ext
                disc = filepath.split("-")[0] # Find the Disc in the filename
            elif settings.CdgFileNameType == 1: # DiscTrack-Artist-Title.Ext
                disc = filepath.mid(0, filepath.length - 2) # Find the Disc in the filename
            elif settings.CdgFileNameType == 2: # Disc-Artist-Title.Ext
                disc = filepath.split("-")[0] # Find the Disc in the filename
            elif settings.CdgFileNameType == 3: # Artist-Title.Ext
                disc = ''
            else:
                raise KeyError, "File name type is invalid!"
            # Remove the first and last space
            disc = disc.strip(" ")
            # Remove the filename path
            disc = os.path.basename(disc)
        #print "Disc parsed: %s" % disc
        return disc

    def ParseTrack(self, filepath, settings):
        """ Parses the file path and returns the track for the song. """
        track = ''
        # Make sure we are to parse information
        if settings.CdgDeriveSongInformation:
            if settings.CdgFileNameType == 0: # Disc-Track-Artist-Title.Ext
                track = filepath.split("-")[1] # Find the Track in the filename
            elif settings.CdgFileNameType == 1: # DiscTrack-Artist-Title.Ext
                track = filepath.mid(filepath.length - 2, 2) # Find the Track in the filename
            elif settings.CdgFileNameType == 2: # Disc-Artist-Title.Ext
                track = ''
            elif settings.CdgFileNameType == 3: # Artist-Title.Ext
                track = ''
            else:
                raise KeyError, "File name type is invalid!"
            # Remove the first and last space
            #track = track.strip(" ")
        #print "Track parsed: %s" % track
        return track

    def MakeSortKey(self, str):
        """ Returns a suitable key to use for sorting, by lowercasing
        and removing articles from the indicated string. """
        str = str.strip().lower()
        if str:
            # Remove a leading parenthetical phrase.
            if str[0] == '(':
                rparen = str.index(')')
                if rparen != ')':
                    str = str[rparen + 1:].strip()

        if str:
            # Remove a leading article.
            firstWord = str.split()[0]
            if firstWord in ['a', 'an', 'the']:
                str = str[len(firstWord):].strip()
                
        return str

    def MakePlayer(self, songDb, errorNotifyCallback, doneCallback):
        """Creates and returns a player of the appropriate type to
        play this file, if possible; or returns None if the file
        cannot be played (in which case, the errorNotifyCallback will
        have already been called with the error message). """

        settings = songDb.Settings
        constructor = None

        if self.Type == self.T_CDG:
            constructor = pycdg.cdgPlayer
        elif self.Type == self.T_KAR:
            constructor = pykar.midPlayer
        elif self.Type == self.T_MPG:
            if self.MpgType == 'mpg' and settings.MpgNative and pympg.movie:
                # Mpg files can be played internally.
                constructor = pympg.mpgPlayer
            else:
                # Other kinds of movies require an external player.
                constructor = pympg.externalPlayer
        else:
            ext = os.path.splitext(self.DisplayFilename)[1]
            errorNotifyCallback("Unsupported file format " + ext)
            return None

        # Try to open the song file.
        try:
            player = constructor(self, songDb, errorNotifyCallback,
                                 doneCallback)
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
            raise ValueError(error)

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

            if self.Type == self.T_CDG:
                # In addition to the .cdg file, we also have to get
                # out the mp3/ogg/whatever audio file that comes with
                # the .cdg file.  Just extract out any files that have
                # the same basename.
                for name in zip.namelist():
                    if name != self.ZipStoredName and name.startswith(prefix):
                        filelist.append(name)

            # We'll continue looking for matching files outside the
            # zip, too.

            for file in filelist:
                try:
                    data = zip.read(file)
                    songDatas.append(SongData(file, data))
                except:
                    print "Error in ZIP containing " + file
        else:
            # A non-zipped file; this is an easy case.
            songDatas.append(SongData(self.Filepath, None))

        if self.Type == self.T_CDG:
            # In addition to the .cdg file, we also have to find the
            # mp3/ogg/whatever audio file that comes with the .cdg
            # file, just as above, when we were pulling them out of
            # the zip file.  This time we are just looking for loose
            # files on the disk.
            for file in os.listdir(dir):
                # Handle potential byte-strings with invalid characters
                # that startswith() will not handle.
                try:
                    file = unicode(file)
                except UnicodeDecodeError:
                    file = file.decode("ascii", "replace")
                try:
                    prefix = unicode(prefix)
                except UnicodeDecodeError:
                    prefix = prefix.decode("ascii", "replace")

                # Check for a file which matches the prefix
                if file.startswith(prefix):
                    path = os.path.join(dir, file)
                    if path != self.Filepath:
                        songDatas.append(SongData(path, None))

        # Now we've found all the matching files.
        return songDatas

    def getTextColour(self, selected):
        """ Returns a suitable colour to use when rendering the text
        of this song line in the pykaraoke_mini song index. """

        if selected:
            fg = (255, 255, 255)

        else:
            # Determine the color of the text.
            fg = (180, 180, 180)
            if self.Type == self.T_KAR:
                # Midi file: color it red.
                fg = (180, 72, 72)

            elif self.Type == self.T_CDG:
                # CDG+MP3: color it blue.
                fg = (72, 72, 180)

            elif self.Type == self.T_MPG:
                # MPEG file: color it yellow.
                fg = (180, 180, 72)

        return fg


    def getBackgroundColour(self, selected):
        """ Returns a suitable colour to use when rendering the
        background of this song line in the pykaraoke_mini song
        index. """

        if not selected:
            bg = (0, 0, 0)

        else:
            if self.Type == self.T_KAR:
                # Midi file: color it red.
                bg = (120, 0, 0)

            elif self.Type == self.T_CDG:
                # CDG+MP3: color it blue.
                bg = (0, 0, 120)

            elif self.Type == self.T_MPG:
                # MPEG file: color it yellow.
                bg = (120, 120, 0)

        return bg

    def getDisplayFilenames(self):
        """ Returns the list of all of the filenames that share the
        same artist/title with this song file.  The list is formatted
        as a single comma-delimited string. """

        if self.sameSongs:
            return ', '.join(map(lambda f: f.DisplayFilename, self.sameSongs))
        return self.DisplayFilename

    def getTypeSort(self):
        """Defines a sorting order by type, for sorting the sameSongs
        list. """

        # We negate self.Type, so that the sort order is: mpg, cdg,
        # kar.  This means that MPG files have priority over CDG which
        # have priority over KAR, for the purposes of coloring the
        # files in the mini index.
        return (-self.Type, self.DisplayFilename)

    def getMarkKey(self):
        """ Returns a key for indexing into markedSongs, for uniquely
        identifying this particular song file. """
        return (self.Filepath, self.ZipStoredName)

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

class TitleStruct:
    """ This represents a single titles.txt file.  Its filename is
    preserved so it can be rewritten later, to modify a title and/or
    artist associated with a song. """

    def __init__(self,  Filepath, ZipStoredName = None):
        self.Filepath = Filepath    # Full path to file or ZIP file
        self.ZipStoredName = ZipStoredName # Filename stored in ZIP
        self.songs = []

        # This is false unless the titles file has been locally
        # modified and needs to be flushed.
        self.dirty = False

    def read(self, songDb):
        """ Reads the titles.txt file, and stores the results in the
        indicated db.  This is intended to be called during db
        scan. """

        if self.ZipStoredName != None:
            zip = songDb.GetZipFile(self.Filepath)
            unzipped_data = zip.read(self.ZipStoredName)
            sfile = StringIO(unzipped_data)
            self.__readTitles(songDb, sfile,
                              os.path.join(self.Filepath, self.ZipStoredName))
        else:
            self.__readTitles(songDb, None, self.Filepath)

    def rewrite(self, songDb):
        """ Rewrites the titles.txt file with the current data. """
        if self.ZipStoredName != None:
            sfile = StringIO()
            self.__writeTitles(songDb, sfile,
                               os.path.join(self.Filepath, self.ZipStoredName))
            unzipped_data = sfile.getvalue()
            songDb.DropZipFile(self.Filepath)
            zip = zipfile.ZipFile(self.Filepath, 'a', zipfile.ZIP_DEFLATED)

            # Since the lame Python zipfile.py implementation won't
            # replace an existing file, we have to rename it out of
            # the way.
            self.__renameZipElement(zip, self.ZipStoredName)

            zip.writestr(self.ZipStoredName, unzipped_data)
            zip.close()
        else:
            self.__writeTitles(songDb, None, self.Filepath)

    def __renameZipElement(self, zip, name1, name2 = None):
        """ Renames the file within the archive named "name1" to
        "name2".  To avoid major rewriting of the archive, it is
        required that len(name1) == len(name2).

        If name2 is omitted or None, a new, unique name is
        generated based on the old name.
        """

        zinfo = zip.getinfo(name1)
        zip._writecheck(zinfo)

        if name2 is None:
            # Replace the last letters with digits.
            i = 0
            n = str(i)
            name2 = name1[:-len(n)] + n
            while name2 in zip.NameToInfo:
                i += 1
                n = str(i)
                name2 = name1[:-len(n)] + n

        if len(name1) != len(name2):
            raise RuntimeError, \
                  "Cannot change length of name with rename()."

        filepos = zip.fp.tell()

        zip.fp.seek(zinfo.header_offset + 30, 0)
        zip.fp.write(name2)
        zinfo.filename = name2

        zip.fp.seek(filepos, 0)

    def __readTitles(self, songDb, catalogFile, catalogPathname):
        self.songs = []
        dirname = os.path.split(catalogPathname)[0]

        if catalogFile == None:
            # Open the file for reading.
            try:
                catalogFile = open(catalogPathname, "rU")
            except:
                print "Could not open titles file %s" % (repr(catalogPathname))
                return

        for line in catalogFile:
            try:
                line = line.decode('utf-8').strip()
            except UnicodeDecodeError:
                line = line.decode('utf-8', 'replace')
                print "Invalid characters in %s:\n%s" % (repr(catalogPathname), line)

            if line:
                tuple = line.split('\t')
                if len(tuple) == 2:
                    filename, title = tuple
                    artist = ''
                elif len(tuple) == 3:
                    filename, title, artist = tuple
                else:
                    print "Invalid line in %s:\n%s" % (repr(catalogPathname), line)
                    continue

                # Allow a forward slash in the file to stand in for
                # whatever the OS's path separator is.
                filename = filename.replace('/', os.path.sep)

                pathname = os.path.join(dirname, filename)
                song = songDb.filesByFullpath.get(pathname, None)
                if song is None:
                    print "Unknown file in %s:\n%s" % (repr(catalogPathname), repr(filename))
                else:
                    song.titles = self
                    self.songs.append(song)

                    song.Title = title.strip()
                    song.Artist = artist.strip()
                    if song.Title:
                        songDb.GotTitles = True
                    if song.Artist:
                        songDb.GotArtists = True

    def __makeRelTo(self, filename, relTo):
        """ Returns the filename expressed as a relative path to
        relTo.  Both file paths should be full paths; relTo should
        already have had normcase and normpath applied to it, and
        should end with a slash. """

        filename = os.path.normpath(filename)
        norm = os.path.normcase(filename)
        prefix = os.path.commonprefix((norm, relTo))

        # The common prefix must end with a slash.
        slash = prefix.rfind(os.sep)
        if slash != -1:
            prefix = prefix[:slash + 1]

        filename = filename[len(prefix):]
        relTo = relTo[len(prefix):]

        numSlashes = relTo.count(os.sep)
        if numSlashes > 1:
            backup = '..' + os.sep
            filename = backup * (numSlashes - 1) + filename

        return filename

    def __writeTitles(self, songDb, catalogFile, catalogPathname):
        dirname = os.path.split(catalogPathname)[0]

        if catalogFile == None:
            # Open the file for writing.
            try:
                catalogFile = open(catalogPathname, "w")
            except:
                print "Could not rewrite titles file %s" % (repr(catalogPathname))
                return

        relTo = os.path.normcase(os.path.normpath(catalogPathname))
        if relTo[-1] != os.sep:
            relTo += os.sep

        for song in self.songs:
            filename = song.Filepath
            if song.ZipStoredName:
                filename = os.path.join(filename, song.ZipStoredName)

            filename = self.__makeRelTo(filename, relTo)

            # Use forward slashes instead of the native separator, to
            # make a more platform-independent titles.txt file.
            filename = filename.replace(os.sep, '/')

            line = filename
            if songDb.GotTitles or songDb.GotArtists:
                line += '\t' + song.Title
            if songDb.GotArtists:
                line += '\t' + song.Artist

            line = line.encode('utf-8')
            catalogFile.write(line + '\n')

class FontData:
    """ This stores the font description selected by the user.
    Hopefully it is enough information to be used both in wx and in
    pygame to reference a unique font on the system. """

    def __init__(self, name = None, size = None, bold = False, italic = False):
        # name may be either a system font name (if size != None) or a
        # filename (if size == None).
        self.name = name
        self.size = size
        self.bold = bold
        self.italic = italic

    def __repr__(self):
        if not self.size:
            return "FontData(%s)" % (repr(self.name))
        else:
            return "FontData(%s, %s, %s, %s)" % (
                repr(self.name), repr(self.size), repr(self.bold), repr(self.italic))

    def getDescription(self):
        desc = self.name
        if self.size:
            desc += ',%spt' % (self.size)
        if self.bold:
            desc += ',bold'
        if self.italic:
            desc += ',italic'

        return desc



# SettingsStruct used as storage only for settings. The instance
# can be pickled to save all user's settings.
class SettingsStruct:

    # This is the list of the encoding strings we offer the user to
    # select from.  You can also type your own.
    Encodings = [
        'cp1252',
        'iso-8859-1',
        'iso-8859-2',
        'iso-8859-5',
        'iso-8859-7',
        'utf-8',
        ]

    # This is the set of CDG zoom modes.
    Zoom = [
        'quick', 'int', 'full', 'soft', 'none',
        ]
    ZoomDesc = {
        'quick' : 'a pixelly scale, maintaining aspect ratio',
        'int' : 'like quick, reducing artifacts a little',
        'full' : 'like quick, but stretches to fill the entire window',
        'soft' : 'a high-quality scale, but may be slow on some hardware',
        'none' : 'keep the display in its original size',
        }

    # Some audio cards seem to support only a limited set of sample
    # rates.  Here are the suggested offerings.
    SampleRates = [
        48000,
        44100,
        22050,
        11025,
        5512,
        ]

    # A list of possible file name deriving combinations.
    # The combination order is stored and used in the parsing algorithm.
    # Track is assumed to be exactly 2 digits.
    FileNameCombinations = [
        'Disc-Track-Artist-Title',
        'DiscTrack-Artist-Title',
        'Disc-Artist-Title',
        'Artist-Title'
        ]

    def __init__(self):
        self.Version = SETTINGS_VERSION

        # Set the default settings, in case none are stored on disk
        self.FolderList = []
        self.CdgExtensions = [ '.cdg' ]
        self.KarExtensions = [ '.kar', '.mid' ]
        self.MpgExtensions = [ '.mpg', '.mpeg', '.avi' ]
        self.IgnoredExtensions = []
        self.LookInsideZips = True
        self.ReadTitlesTxt = True
        self.CheckHashes = False
        self.DeleteIdentical = False
        if env == ENV_WINDOWS:
            self.FilesystemCoding = 'cp1252'
        else:
            self.FilesystemCoding = 'iso-8859-1'
        self.ZipfileCoding = 'cp1252'

        self.WindowSize = (640, 480) # Size of the window for PyKaraoke
        self.FullScreen = False # Determines if the karaoke player should be full screen
        self.NoFrame = False # Determies if the karaoke player should have a window frame.

        # SDL specific parameters; some settings may work better on
        # certain hardware than others
        self.DoubleBuf = True
        self.HardwareSurface = True
        
        self.PlayerSize = (640, 480) # Size of the karaoke player
        self.PlayerPosition = None # Initial position of the karaoke player
        
        self.SplitVertically = True
        self.AutoPlayList = True # Enables or disables the auto play on the play-list
        self.DoubleClickPlayList = True # Enables or disables the double click for playing from the play-list
        self.ClearFromPlayList = True # Enables or disables clearing the playlist with a right click on the play list
        self.Kamikaze = False # Enables or disables the kamikaze button
        self.UsePerformerName = False # Enables or disables the prompting for a performers name.
        self.PlayFromSearchList = True # Enables or disables the playing of a song from the search list
        self.DisplayArtistTitleCols = False # Enables or disables display of artist/title columns

        self.SampleRate = 44100
        self.NumChannels = 2
        self.BufferMs = 50
        self.UseMp3Settings = True

        # This value is a time in milliseconds that will be used to
        # shift the time of the lyrics display relative to the video.
        # It is adjusted by the user pressing the left and right
        # arrows during singing, and is persistent during a session.
        # Positive values make the lyrics anticipate the music,
        # negative values delay them.
        self.SyncDelayMs = 0

        # KAR/MID options
        self.KarEncoding = 'cp1252'  # Default text encoding in karaoke files
        self.KarFont = FontData("DejaVuSans.ttf")
        self.KarBackgroundColour = (0, 0, 0)
        self.KarReadyColour = (255,50,50)
        self.KarSweepColour = (255,255,255)
        self.KarInfoColour = (0, 0, 200)
        self.KarTitleColour = (100, 100, 255)
        self.MIDISampleRate = 44100

        # CDG options
        self.CdgZoom = 'int'
        self.CdgUseC = True
        self.CdgDeriveSongInformation = False # Determines if we should parse file names for song information
        self.CdgFileNameType = -1 # The style index we are using for the file name parsing
        self.ExcludeNonMatchingFilenames = False # Exclude songs from database if can't derive song info

        # MPEG options
        self.MpgNative = True
        self.MpgExternalThreaded = True
        self.MpgExternal = 'mplayer -fs "%(file)s"'

        if env == ENV_WINDOWS:
            self.MpgExternal = '"C:\\Program Files\\Windows Media Player\\wmplayer.exe" "%(file)s" /play /close /fullscreen'
        elif env == ENV_GP2X:
            self.FullScreen = True
            self.PlayerSize = (320, 240)
            self.CdgZoom = 'none'
            # Reduce the default sample rate on the GP2x to save time.
            self.MIDISampleRate = 11025
            self.MpgExternal = './mplayer_cmdline "%(file)s"'
            self.MpgExternalThreaded = False
            self.BufferMs = 250

            # Define the CPU speed for various activities.  We're
            # conservative here and avoid overclocking by default.
            # The user can push these values higher if he knows his
            # GP2X can handle it.
            self.CPUSpeed_startup = 240
            self.CPUSpeed_wait = 33
            self.CPUSpeed_menu_idle = 33
            self.CPUSpeed_menu_slow = 100
            self.CPUSpeed_menu_fast = 240
            self.CPUSpeed_load = 240
            self.CPUSpeed_cdg = 200
            self.CPUSpeed_kar = 240
            self.CPUSpeed_mpg = 200

# This is a trivial class used to wrap the song database with a
# version number.
class DBStruct:
    def __init__(self):
        self.Version = DATABASE_VERSION
        pass

# Song database class with methods for building the database, searching etc
class SongDB:
    def __init__(self):
        # Filepaths and titles are stored in a list of SongStruct instances
        self.FullSongList = []

        # This is the same list, with songs of the same artist/title
        # removed.
        self.UniqueSongList = []

        # Here's those lists again, cached into various different
        # sorts.
        self.SortedLists = {}

        # And this is just the currently-active song list, according
        # to selected sort.
        self.SongList = []

        # The list of TitlesFiles we have found in our scan.
        self.TitlesFiles = []

        # A cache of zip files.
        self.ZipFiles = []

        # Set true if there are local changes to the database that
        # need to be saved to disk.
        self.databaseDirty = False

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

        if env == ENV_GP2X:
            # On the GP2X, just save db files in the root directory.
            # Makes it easier to find them, and avoids directory
            # clutter.
            return '.'

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

    def makeSongStruct(self, filename):
        """ Creates a quick SongStruct representing the indicated
        filename.  The file may be embedded within a zip file; treat
        the zip filename as a directory in this case. """

        # Is this a file within a zip file?
        zipStoredName = None
        z = filename.find('.zip/')
        if z == -1:
            z = filename.find('.zip' + os.path.sep)
        if z != -1:
            zipStoredName = filename[z + 5:]
            filename = filename[:z + 4]

        song = SongStruct(filename, self.Settings,
                          ZipStoredName = zipStoredName)
        return song


    def chooseTitles(self, song):
        """ Chooses an appropriate titles file to represent the
        indicated song file.  If there is no appropriate titles file,
        creates one.  Applies the song to the new titles file. """

        if song.titles:
            # This song already has a titles file.
            return

        songPath = song.Filepath
        if song.ZipStoredName:
            songPath = os.path.join(songPath, song.ZipStoredName)

        relTo = os.path.normcase(os.path.normpath(songPath))

        # Look for the titles file, in a directory above the song,
        # with the longest prefix in common with the song.  This will
        # be the best titles file.
        bestTitles = None
        bestPrefix = ''
        for titles in self.TitlesFiles:
            titlesPath = titles.Filepath
            if titles.ZipStoredName:
                titlesPath = os.path.join(titlesPath, titles.ZipStoredName)
            norm = os.path.normcase(os.path.normpath(titlesPath))

            prefix = os.path.commonprefix((norm, relTo))
            # The common prefix must end with a slash.
            slash = prefix.rfind(os.sep)
            if slash != -1:
                prefix = prefix[:slash + 1]

            norm = norm[len(prefix):]
            if os.path.sep in norm:
                # This titles file is in a subordinate directory.
                # Skip it.
                continue

            if len(prefix) > len(bestPrefix):
                bestTitles = titles
                bestPrefix = prefix

        if not bestTitles:
            # Didn't find a good candidate.  Create a new titles file,
            # in the root of whichever directory contains the song.
            bestDir = None
            for dir in self.Settings.FolderList:
                norm = os.path.normcase(os.path.normpath(dir))
                if relTo.startswith(norm):
                    bestDir = dir
                    break

            if not bestDir:
                # No folder!  Put it with the song itself.
                bestDir = os.path.splitext(song.Filepath)[0]

            bestTitles = TitleStruct(os.path.join(bestDir, 'titles.txt'))
            self.TitlesFiles.append(bestTitles)

        bestTitles.songs.append(song)
        song.titles = bestTitles
        bestTitles.dirty = True
        self.databaseDirty = True

    def LoadSettings (self, errorCallback):
        """ Load the personal settings (but not yet the database). """

        # Load the settings file
        settings_filepath = os.path.join (self.SaveDir, "settings.dat")
        if os.path.exists (settings_filepath):
            file = open(settings_filepath, "rU")
            loadsettings = SettingsStruct()
            # We use eval to evaluate the settings file.  This is
            # very easy and powerful, though it does mean we
            # execute whatever arbitrary Python code a malicious
            # user might have put in there.  On the other hand,
            # it's the user's own machine, and this isn't any less
            # secure than using cPickle to decode the file (which
            # basically does the same thing anyway).
            for line in file:
                if '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()

                # Ignore any definitions for keys we don't already
                # have.  This allows us to phase out old config values
                # we no longer use.
                if not hasattr(loadsettings, key):
                    continue

                try:
                    value = eval(value)
                except:
                    # Ignore anything that isn't valid Python.
                    print "Invalid value for %s" % (key)
                    continue

                setattr(loadsettings, key, value)

            # Check settings are for the current version.
            message = None
            if loadsettings:
                if loadsettings.Version == SETTINGS_VERSION:
                    self.Settings = loadsettings
                else:
                    message = "New version of PyKaraoke, clearing settings"

            if message:
                if errorCallback:
                    errorCallback(message)
                else:
                    print message

    def LoadDatabase(self, errorCallback):
        """ Load the saved database. """

        self.FullSongList = []
        self.UniqueSongList = []
        self.TitlesFiles = []
        self.GotTitles = False
        self.GotArtists = False

        # Load the database file
        db_filepath = os.path.join (self.SaveDir, "songdb.dat")
        if os.path.exists (db_filepath):
            file = open (db_filepath, "rb")
            loaddb = None
            try:
                loaddb = cPickle.load (file)
            except:
                pass
            if (getattr(loaddb, 'Version', None) == DATABASE_VERSION):
                self.FullSongList = loaddb.FullSongList
                self.SongList = loaddb.FullSongList
                self.UniqueSongList = loaddb.UniqueSongList
                self.TitlesFiles = loaddb.TitlesFiles
                self.GotTitles = loaddb.GotTitles
                self.GotArtists = loaddb.GotArtists
            else:
                if errorCallback:
                   errorCallback("New version of PyKaraoke, clearing database")

        self.databaseDirty = False

##         # This forces the titles files to be rewritten at the next
##         # "save" operation.
##         for titles in self.TitlesFiles:
##             titles.dirty = True
##         self.databaseDirty = True

    def SaveSettings (self):
        """ Save user settings to the home directory. """

        # Create the temp directory if it doesn't exist already
        if not os.path.exists (self.SaveDir):
            os.mkdir(self.SaveDir)

        # Save the settings file
        settings_filepath = os.path.join (self.SaveDir, "settings.dat")
        try:
            file = open (settings_filepath, "w")
        except IOError, message:
            print message
        else:
            # We don't use pickle to dump out the settings anymore.
            # Instead, we write them in this human-readable and
            # human-editable format.
            keys = self.Settings.__dict__.keys()
            keys.sort()
            for k in keys:
                if not k.startswith('__'):
                    value = getattr(self.Settings, k)
                    print >> file, "%s = %s" % (k, repr(value))

    def SaveDatabase(self):
        """ Save the database to the appropriate directory. """

        if not self.databaseDirty:
            return

        try:
            # Create the temp directory if it doesn't exist already
            if not os.path.exists (self.SaveDir):
                os.mkdir(self.SaveDir)

            # Write out any titles files that have changed.
            for titles in self.TitlesFiles:
                if titles.dirty:
                    titles.rewrite(self)
                    titles.dirty = False

            # Check for newly unique files
            self.makeUniqueSongs()

            # Save the database file
            db_filepath = os.path.join (self.SaveDir, "songdb.dat")
            file = open (db_filepath, "wb")

            loaddb = DBStruct()
            loaddb.FullSongList = self.FullSongList
            loaddb.UniqueSongList = self.UniqueSongList
            loaddb.TitlesFiles = self.TitlesFiles
            loaddb.GotTitles = self.GotTitles
            loaddb.GotArtists = self.GotArtists

            cPickle.dump (loaddb, file, cPickle.HIGHEST_PROTOCOL)
        except IOError, message:
            print message
        self.databaseDirty = False

    def GetSong(self, index):
        """ This returns the song stored in index in the database. """
        return self.FullSongList[index]

    def BuildSearchDatabase(self, yielder, busyDlg):
        # Zap the database and build again from scratch. Return True
        # if was cancelled.
        self.FullSongList = []
        self.TitlesFiles = []

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

    def DropZipFile(self, filename):
        """Releases an opened zip file by the indicated filename, if any. """

        for tuple in self.ZipFiles:
            cacheFilename, cacheZip = tuple
            if cacheFilename == filename:
                # Here is the zip file in the cache; remove it.
                self.ZipFiles.remove(tuple)
                return

    def doSearch(self, fileList, yielder, busyDlg):
        """ This is the actual implementation of BuildSearchDatabase()
        and AddFile()."""

        self.BusyDlg = busyDlg
        self.BusyDlg.SetProgress("Scanning", 0.0)
        yielder.Yield()
        self.BusyDlg.Show()

        self.lastBusyUpdate = time.time()
        self.filesByFullpath = {}

        for i in range(len(fileList)):
            root_path = fileList[i]

            # Assemble a stack of progress amounts through the various
            # directory levels.  This way we can update a progress bar
            # without knowing exactly how many directories we are
            # going to traverse.  We give each directory equal weight
            # regardless of the number of files within it.
            progress = [(i, len(fileList))]
            self.fileScan(root_path, progress, yielder)
            if self.BusyDlg.Clicked:
                break

        if self.TitlesFiles and not self.BusyDlg.Clicked:
            self.BusyDlg.SetProgress("Reading titles files", 0.0)
            yielder.Yield()
            self.lastBusyUpdate = time.time()

            # Now go back and read any titles.txt files we came across.
            # These will have meta-information about the files, such as
            # the title and/or artist.
            for i in range(len(self.TitlesFiles)):
                if self.BusyDlg.Clicked:
                    break
                now = time.time()
                if now - self.lastBusyUpdate > 0.1:
                    # Every so often, update the current path on the display.
                    self.BusyDlg.SetProgress(
                        "Reading titles files",
                        float(i) / float(len(self.TitlesFiles)))
                    yielder.Yield()
                    self.lastBusyUpdate = now
                self.TitlesFiles[i].read(self)

        if self.Settings.CheckHashes:
            self.checkFileHashes(yielder)

        self.BusyDlg.SetProgress("Finalizing", 1.0)
        yielder.Yield()

        # This structure was just temporary, for use just while
        # scanning the directories.  Remove it now.
        del self.filesByFullpath

        self.makeUniqueSongs()
        self.databaseDirty = True

        cancelled = self.BusyDlg.Clicked
        self.BusyDlg.Destroy()

        return cancelled

    def folderScan (self, FolderToScan, progress, yielder):
        # Search for karaoke files inside the folder, looking inside ZIPs if
        # configured to do so. Function is recursive for subfolders.
        try:
            filedir_list = os.listdir(FolderToScan)
        except:
            print "Couldn't scan %s" % (repr(FolderToScan))
            return False

        # Sort the list, using printable strings for the sort key to
        # prevent issues with unicode characters in non-unicode strings
        # in the list
        filedir_list.sort(key=repr)

        # Loop through the list
        for i in range(len(filedir_list)):
            item = filedir_list[i]
            if self.BusyDlg.Clicked:
                return True

            # Allow windows to refresh now and again while scanning
            yielder.ConsiderYield()

            # Build the full file path. Check file types match, as
            # os.listdir() can return non-unicode while the folder
            # is still unicode.
            if (type(FolderToScan) != type(item)):
                full_path = os.path.join(str(FolderToScan), str(item))
                print "Folder %s and file %s do not match types" % (repr(FolderToScan), repr(item))
            else:
                full_path = os.path.join(FolderToScan, item)

            nextProgress = progress + [(i, len(filedir_list))]
            self.fileScan(full_path, nextProgress, yielder)
            if self.BusyDlg.Clicked:
                return

    def __computeProgressValue(self, progress):
        """ Returns a floating-point value in the range 0 to 1 that
        corresponds to the progress list we have built up while
        traversing the directory structure hierarchically.  This is
        used to update the progress bar linearly while we traverse the
        hierarchy. """

        # The progress list is a list of tuples of the form [(i0,
        # len0), (i1, len1), (i2, len2), ..., (in, lenn)].  There is
        # one entry for each directory level we have visited.

        # We need to boil this down into a single nondecreasing
        # number.  A simple mathematical series.

        range = 1.0
        result = 0.0
        for i, len in progress:
            if len > 1:
                result += range * (float(i) / float(len))
                range = range * (1.0 / float(len))
        return result

    def fileScan(self, full_path, progress, yielder):
        now = time.time()
        if now - self.lastBusyUpdate > 0.1:
            # Every so often, update the progress bar.
            basename = os.path.split(full_path)[1]
            # Sanitise byte-strings
            try:
                basename = unicode(basename)
            except UnicodeDecodeError:
                basename = basename.decode("ascii", "replace")
            self.BusyDlg.SetProgress(
                "Scanning %s" % basename,
                self.__computeProgressValue(progress))
            yielder.Yield()
            self.lastBusyUpdate = now

        # Recurse into subdirectories
        if os.path.isdir(full_path):
            basename = os.path.split(full_path)[1]
            if basename == 'CVS' or basename == '.svn':
                # But skip over these bogus directories.
                pass
            else:
                self.folderScan(full_path, progress, yielder)
            if self.BusyDlg.Clicked:
                return
        # Store file details if it's a file type we're interested in
        else:
            root, ext = os.path.splitext(full_path)
            # Non-ZIP files
            if self.Settings.ReadTitlesTxt and full_path.endswith('titles.txt'):
                # Save this titles.txt file for reading later.
                self.TitlesFiles.append(TitleStruct(full_path))
            elif self.IsExtensionValid(ext):
                try:
                    self.addSong(SongStruct(full_path, self.Settings, DatabaseAdd = True))
                except KeyError:
                    print "Excluding filename with unexpected format: %s " % repr(os.path.basename(full_path))
            # Look inside ZIPs if configured to do so
            elif self.Settings.LookInsideZips and ext.lower() == ".zip":
                try:
                    if zipfile.is_zipfile(full_path):
                        zip = self.GetZipFile(full_path)
                        namelist = zip.namelist()
                        for i in range(len(namelist)):
                            filename = namelist[i]

                            now = time.time()
                            if now - self.lastBusyUpdate > 0.1:
                                # Every so often, update the progress bar.
                                nextProgress = progress + [(i, len(namelist))]
                                basename = os.path.split(full_path)[1]
                                # Sanitise byte-strings
                                try:
                                    basename = unicode(basename)
                                except UnicodeDecodeError:
                                    basename = basename.decode("ascii", "replace")
                                self.BusyDlg.SetProgress(
                                    "Scanning %s" % basename,
                                    self.__computeProgressValue(nextProgress))
                                yielder.Yield()
                                self.lastBusyUpdate = now

                            root, ext = os.path.splitext(filename)
                            if self.Settings.ReadTitlesTxt and filename.endswith('titles.txt'):
                                # Save this titles.txt file for reading later.
                                self.TitlesFiles.append(TitleStruct(full_path, ZipStoredName = filename))
                            elif self.IsExtensionValid(ext):
                                # Python zipfile only supports deflated and stored
                                info = zip.getinfo(filename)
                                if info.compress_type == zipfile.ZIP_STORED or info.compress_type == zipfile.ZIP_DEFLATED:
                                    #print ("Adding song %s in ZIP file %s"%(repr(filename), repr(full_path)))
                                    try:
                                        self.addSong(SongStruct(full_path, self.Settings, ZipStoredName = filename, DatabaseAdd = True))
                                    except KeyError:
                                        print "Excluding filename with unexpected format: %s " % repr(os.path.basename(full_path))
                                else:
                                    print ("ZIP member compressed with unsupported type (%d): %s"%(info.compress_type, repr(full_path)))
                    else:
                        print "Cannot parse ZIP file: " + repr(full_path)
                except:
                    print "Error looking inside zip " + repr(full_path)

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
        for song in self.FullSongList:
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
                try:
                    if (term not in LowerTitle) and \
                       (term not in LowerArtist) and \
                       (term not in LowerZipName) and \
                       (term not in LowerPath):
                        misses = misses + 1
                except UnicodeDecodeError:
                    print "Unicode error looking up %s in %s" % (repr(term), repr(LowerZipName))
                    misses = misses + 1 
            if misses == 0:
                ResultsList.append(song)
        return ResultsList

    # Get the song database size (number of songs)
    def GetDatabaseSize (self):
        return len(self.FullSongList)

    # Check if the passed file extension is configured for this database
    def IsExtensionValid (self, extension):
        ext = extension.lower()
        if ext in self.Settings.IgnoredExtensions:
            return False
        if ext in self.Settings.KarExtensions or \
           ext in self.Settings.CdgExtensions or \
           ext in self.Settings.MpgExtensions:
            return True
        return False

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
                        # The unlink can fail on Windows due to a bug in
                        # pygame.mixer.music which does not release the
                        # file handle until you load another music file.
                        pass

    def SelectSort(self, sort, allowResort = True):
        """Sorts the list of songs in order according to the indicated
        key, which must be one of 'title', 'artist', or 'filename'.
        Also sets self.GetSongTuple to a functor which, when called, returns a
        3-tuple of strings suitable for displaying for each song,
        where the first string of each tuple is the sort key.

        This may require re-sorting the list on-the-fly.  If
        allowResort is False, then the list will never be re-sorted;
        rather, the method will return True if the sort was
        successfully applied, or False if a re-sort was necessary but
        not performed, in which case the list retains its original
        sort. """

        if sort == 'title' and self.GotTitles:
            if self.GotArtists:
                getSongTuple = self.getSongTupleTitleArtistFilename
                sortKeys = ('title', 'artist', 'filename')
                getSortKey = self.getSongTupleTitleArtistFilenameSortKey
            else:
                getSongTuple = self.getSongTupleTitleFilenameArtist
                sortKeys = ('title', 'filename')
                getSortKey = self.getSongTupleTitleFilenameArtistSortKey

        elif sort == 'artist' and self.GotArtists:
            if self.GotTitles:
                getSongTuple = self.getSongTupleArtistTitleFilename
                sortKeys = ('artist', 'title', 'filename')
                getSortKey = self.getSongTupleArtistTitleFilenameSortKey
            else:
                getSongTuple = self.getSongTupleArtistFilenameTitle
                sortKeys = ('artist', 'filename')
                getSortKey = self.getSongTupleArtistFilenameTitleSortKey

        else: # filename
            sort = 'filename'
            if self.GotTitles and self.GotArtists:
                getSongTuple = self.getSongTupleFilenameTitleArtist
                sortKeys = ('filename', 'title', 'artist')
                getSortKey = self.getSongTupleFilenameTitleArtistSortKey
            elif self.GotTitles:
                getSongTuple = self.getSongTupleFilenameTitleArtist
                sortKeys = ('filename', 'title')
                getSortKey = self.getSongTupleFilenameTitleArtistSortKey
            elif self.GotArtists:
                getSongTuple = self.getSongTupleFilenameArtistTitle
                sortKeys = ('filename', 'artist')
                getSortKey = self.getSongTupleFilenameArtistTitleSortKey
            else:
                getSongTuple = self.getSongTupleFilenameArtistTitle
                sortKeys = ('filename',)
                getSortKey = self.getSongTupleFilenameArtistTitleSortKey

        list = self.SortedLists.get(getSortKey, None)
        if list is None:
            if not allowResort:
                # Return False to indicate that a sort was not applied.
                return False
            
            # We haven't asked for this sort key before; we have to
            # sort the list now.  Once sorted, we can keep it around
            # for future requests.
            if sort == 'filename':
                list = self.FullSongList[:]
            else:
                list = self.UniqueSongList[:]
            list.sort(key = getSortKey)
            self.SortedLists[getSortKey] = list

        global fileSortKey
        fileSortKey = getSortKey

        self.Sort = sort
        self.SortKeys = sortKeys
        self.GetSongTuple = getSongTuple
        self.GetSortKey = getSortKey

        self.SongList = list

        return True

    def getSongTupleTitleArtistFilename(self, file):
        return (file.Title, file.Artist, file.getDisplayFilenames())

    def getSongTupleTitleFilenameArtist(self, file):
        return (file.Title, file.getDisplayFilenames(), file.Artist)

    def getSongTupleArtistTitleFilename(self, file):
        return (file.Artist, file.Title, file.getDisplayFilenames())

    def getSongTupleArtistFilenameTitle(self, file):
        return (file.Artist, file.getDisplayFilenames(), file.Title)

    def getSongTupleFilenameTitleArtist(self, file):
        return (file.DisplayFilename, file.Title, file.Artist)

    def getSongTupleFilenameArtistTitle(self, file):
        return (file.DisplayFilename, file.Artist, file.Title)

    def getSongTupleTitleArtistFilenameSortKey(self, file):
        return (file.MakeSortKey(file.Title), file.MakeSortKey(file.Artist), file.getDisplayFilenames().lower(), id(file))

    def getSongTupleTitleFilenameArtistSortKey(self, file):
        return (file.MakeSortKey(file.Title), file.DisplayFilename.lower(), file.MakeSortKey(file.Artist), id(file))

    def getSongTupleArtistTitleFilenameSortKey(self, file):
        return (file.MakeSortKey(file.Artist), file.MakeSortKey(file.Title), file.DisplayFilename.lower(), id(file))

    def getSongTupleArtistFilenameTitleSortKey(self, file):
        return (file.MakeSortKey(file.Artist), file.DisplayFilename.lower(), file.MakeSortKey(file.Title), id(file))

    def getSongTupleFilenameTitleArtistSortKey(self, file):
        return (file.DisplayFilename.lower(), file.MakeSortKey(file.Title), file.MakeSortKey(file.Artist), id(file))

    def getSongTupleFilenameArtistTitleSortKey(self, file):
        return (file.DisplayFilename.lower(), file.MakeSortKey(file.Artist), file.MakeSortKey(file.Title), id(file))

    def addSong(self, file):
        self.FullSongList.append(file)
        if file.Title:
            self.GotTitles = True
        if file.Artist:
            self.GotArtists = True

        if hasattr(self, 'filesByFullpath'):
            # Also record the file in the temporary map by fullpath name,
            # so we can cross-reference it with a titles.txt file that
            # might reference it.
            fullpath = file.Filepath
            if file.ZipStoredName:
                name = file.ZipStoredName.replace('/', os.path.sep)
                fullpath = os.path.join(fullpath, name)
            self.filesByFullpath[fullpath] = file

    def checkFileHashes(self, yielder):
        """ Walks through self.FullSongList, checking for md5 hashes
        to see if any files are duplicated. """

        self.BusyDlg.SetProgress("Checking file hashes", 0.0)
        yielder.Yield()
        self.lastBusyUpdate = time.time()
        numDuplicates = 0

        # Check the md5's of each file, to see if there are any
        # duplicates.
        fileHashes = {}
        numFiles = len(self.FullSongList)
        for i in range(numFiles):
            now = time.time()
            if now - self.lastBusyUpdate > 0.1:
                # Every so often, update the progress bar.
                label = "Checking file hashes"
                if numDuplicates:
                    label = "%s duplicates found" % (numDuplicates)
                self.BusyDlg.SetProgress(
                    label, float(i) / float(numFiles))
                yielder.Yield()
                self.lastBusyUpdate = now

            if self.BusyDlg.Clicked:
                return


            # Calculate the MD5 hash of the songfile.
            m = md5()

            # Get details of the associated files
            song = self.FullSongList[i]
            datas = song.GetSongDatas()
            if len(datas) > 0:
                song_data = datas[0]
                # If the data has already been read in, use it directly.
                # Otherwise read the file off disk for temporary use.
                if song_data.data != None:
                    m.update(song_data.data)
                else:
                    f = open(song_data.filename)
                    if f != None:
                        while True:
                            data = f.read(64*1024)
                            if not data:
                                break
                            m.update(data)
                list = fileHashes.setdefault(m.digest(), [])
                if list:
                    numDuplicates += 1
                list.append(i)

        # Remove the identical files from the database.  If specified,
        # remove them from disk too.
        removeIndexes = {}
        for list in fileHashes.values():
            if len(list) > 1:
                filenames = map(lambda i: self.FullSongList[i].DisplayFilename, list)
                print "Identical songs: %s" % repr((', '.join(filenames)))
                for i in list[1:]:
                    extra = self.FullSongList[i]
                    removeIndexes[i] = True
                    if extra.titles:
                        extra.titles.dirty = True
                    if self.Settings.DeleteIdentical:
                        if extra.ZipStoredName:
                            # Can't delete a song within a zip, sorry.
                            pass
                        else:
                            os.remove(extra.Filepath)

        # Now rebuild the FullSongList without the removed files.
        newSongList = []
        for i in range(numFiles):
            if i not in removeIndexes:
                newSongList.append(self.FullSongList[i])
        self.FullSongList = newSongList

    def makeUniqueSongs(self):
        """ Walks through self.FullSongList, and builds up
        self.UniqueSongList, which collects only those songs who have
        the same artist/title combination. """

        if not self.GotArtists and not self.GotTitles:
            # A special case: titles.txt files aren't in use.
            self.UniqueSongList = self.FullSongList
            return

        songsByArtistTitle = {}

        for song in self.FullSongList:
            tuple = (song.Artist.lower(), song.Title.lower())
            songList = songsByArtistTitle.setdefault(tuple, [])
            songList.append(song)

        # Now go through and sort each songList into order by type.

        self.UniqueSongList = []
        for songList in songsByArtistTitle.values():
            songList.sort(key = SongStruct.getTypeSort)
            for song in songList:
                song.sameSongs = songList
            self.UniqueSongList.append(songList[0])

globalSongDB = SongDB()
