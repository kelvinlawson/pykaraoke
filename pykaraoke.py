#!/usr/bin/env python

# pykaraoke - Karaoke Player Frontend
#
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


# OVERVIEW
#
# pykaraoke is a frontend for the pycdg and pympg karaoke players. It provides
# a search engine to find your songs, a file/folder browser to pick songs from
# disk, as well as a playlist.
#
# The default view is the search engine - you add your folders that contain
# karaoke songs, and hit the Scan button to build the database. The search
# engine can also look inside ZIP files for karaoke tracks.
#
# This frontend uses the WxPython library (www.wxpython.org) to provide the
# GUI. The CDG and MPG player functionality is handled by the external
# pycdg and pympg libraries (which use the pygame library (www.pygame.org)
# for audio/video).
#
# The frontend and player libraries run on any operating system that run pygame
# and WxPython (currently Linux, Windows and OSX).


# REQUIREMENTS
#
# pykaraoke requires the following to be installed on your system:
# . WxPython (www.wxpython.org)
# . Python (www.python.org)
# . Pygame (www.pygame.org)


# USAGE INSTRUCTIONS
#
# To start the player, run the following from the command line:
#       python pykaraoke.py
#
# The player starts in Search View. From here you can search for songs in
# your song database. You need to first set up the database, however, by
# clicking "Add Songs".
#
# To set up the database, add the folders that contain your karaoke songs.
# Select which type of files you are interested in adding to the search
# database (CDG, MPG etc). Click "Look Inside Zips" if you also want to
# search inside any ZIP files found in the folders for more karaoke songs.
#
# When you have finished adding folders, and setting your preferences,
# click "Scan Now" to start building the database. This can take some time
# but only needs to be done once. The search engine then searches your
# database, rather than searching the hard disk every time you search for
# a song.
#
# Once you have set up your database, clicking "Save" will save the database
# and settings for the next time you run the program. (The information is
# saved in a .pykaraoke folder in your home directory).
#
# If you get more karaoke files, don't forget to rescan the hard disk and
# build the database again. Otherwise the new files won't be visible in
# the search engine.
#
# With your database set up, you are ready to start searching for and
# playing your karaoke songs. From the main window, enter the name of the
# song you would like to find and click "Search". This will populate the
# Search Results panel below with the matching song files. From here
# double-clicking a song plays it directly. You can also add the song to
# your playlist by right-clicking on the song and using the popup menu.
#
# There is also a simple explorer-like interface that can be selected using
# a drop-down box on the main window ("Folder View"). Using this you can
# also play songs directly or add them to the playlist, by right-clicking
# on the song and using the popup menu.
#
# In the right-hand side of the window you will find your playlist. Songs
# can be added from the search results or folder browser, until you have
# built up your playlist. Once ready, click on the song you would like to
# start with. When the song is finished playing, the next song down the
# playlist will automatically start playing. You can also delete single
# songs, or clear the entire playlist by right-clicking on an item in
# the playlist.
#
# This is an early release of pykaraoke. Please let us know if there are
# any features you would like to see added, or you have any other
# suggestions or bug reports. Contact the project at
# kelvinl@users.sourceforge.net.


# IMPLEMENTATION DETAILS
#
# pykaraoke is a python module that implements a frontend for
# the external pycdg and pympg player modules. The frontend
# is implemented using WxPython.
#
# Everything is kicked off by the PyKaraokeMgr class, which
# instantiates the main window (PyKaraokeWindow class). It
# also handles calling the player modules and managing the
# playlist.
#
# All panels, windows and controls tend to be sub-classed from the
# base WxPython classes.
#
# The players are started by instantiating the class exported by
# their modules (e.g. pycdg.cdgPlayer()). They can then be
# controlled by calling their methods (Play(), Close() etc). The
# player modules do not take over the main loop, so the GUI is still
# usable while the songs are playing, allowing the user to
# continue adding to the playlist etc.

import sys

# Ensure that we have at least wx version 2.6, but also protect
# wxversion against py2exe (wxversion requires actual wx directories
# on-disk, so it doesn't work in the py2exe-compiled version used for
# Windows distribution).
if not hasattr(sys, 'frozen'):
    import wxversion
    wxversion.ensureMinimal('2.6')

import os, string, wx, time, copy, types
from pykconstants import *
from pykenv import env
import pycdg, pympg, pykar, pykversion, pykdb
import codecs
import cPickle
from pykmanager import manager
import random
import performer_prompt as PerformerPrompt

# Constants
PLAY_COL_TITLE =      "Title"
PLAY_COL_ARTIST =     "Artist"
PLAY_COL_FILENAME =   "Filename"
PLAY_COL_PERFORMER =  "Performer"


class wxAppYielder(pykdb.AppYielder):
    def Yield(self):
        wx.GetApp().Yield()

# Popup busy window with cancel button
class wxBusyCancelDialog(wx.ProgressDialog, pykdb.BusyCancelDialog):
    def __init__(self, parent, title):
        pykdb.BusyCancelDialog.__init__(self)
        wx.ProgressDialog.__init__(
            self, title, title, style = wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)

    def SetProgress(self, label, progress):
        """ Called from time to time to update the progress display. """

        cont = self.Update(int(progress * 100), label)
        if isinstance(cont, types.TupleType):
            # Later versions of wxPython return a tuple from the above.
            cont, skip = cont

        if not cont:
            # Cancel clicked
            self.Clicked = True

# Popup settings window for adding song folders, requesting a
# new folder scan to fill the database etc.
class DatabaseSetupWindow (wx.Frame):
    def __init__(self,parent,id,title,KaraokeMgr):
        wx.Frame.__init__(self,parent,wx.ID_ANY, title,
                          style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.KaraokeMgr = KaraokeMgr

        self.panel = wx.Panel(self)

        # Help text
        self._HelpText = wx.StaticText (self.panel, wx.ID_ANY,
                "Add folders to build a searchable database of your karaoke songs\n",
                style = wx.ALIGN_CENTER)

        # Add the folder list
        self.FolderList = wx.ListBox(self.panel, -1, style=wx.LB_SINGLE)
        for item in self.KaraokeMgr.SongDB.GetFolderList():
            self.FolderList.Append(item)

        # Add the buttons
        self.AddFolderButtonID = wx.NewId()
        self.DelFolderButtonID = wx.NewId()
        self.AddFolderButton = wx.Button(self.panel, self.AddFolderButtonID, "Add Folder")
        self.DelFolderButton = wx.Button(self.panel, self.DelFolderButtonID, "Delete Folder")
        self.FolderButtonsSizer = wx.BoxSizer(wx.VERTICAL)
        self.FolderButtonsSizer.Add(self.AddFolderButton, 0, wx.ALIGN_LEFT, 3)
        self.FolderButtonsSizer.Add(self.DelFolderButton, 0, wx.ALIGN_LEFT, 3)
        wx.EVT_BUTTON(self, self.AddFolderButtonID, self.OnAddFolderClicked)
        wx.EVT_BUTTON(self, self.DelFolderButtonID, self.OnDelFolderClicked)

        # Create a sizer for the folder list and folder buttons
        self.FolderSizer = wx.BoxSizer (wx.HORIZONTAL)
        self.FolderSizer.Add (self.FolderList, 1, wx.EXPAND, 3)
        self.FolderSizer.Add (self.FolderButtonsSizer, 0, wx.ALL, 3)

        # Create the settings controls
        self.FileExtensionID = wx.NewId()
        self.FiletypesText = wx.StaticText (self.panel, wx.ID_ANY, "Include File Types: ")
        self.FiletypesSizer = wx.BoxSizer (wx.HORIZONTAL)

        settings = self.KaraokeMgr.SongDB.Settings
        self.extCheckBoxes = {}
        for ext in settings.KarExtensions + settings.CdgExtensions + settings.MpgExtensions:
            cb = wx.CheckBox(self.panel, self.FileExtensionID, ext[1:])
            cb.SetValue(self.KaraokeMgr.SongDB.IsExtensionValid(ext))
            self.FiletypesSizer.Add(cb, 0, wx.ALL | wx.RIGHT, border = 2)
            self.extCheckBoxes[ext] = cb

        wx.EVT_CHECKBOX (self, self.FileExtensionID, self.OnFileExtChanged)

        # Create the ZIP file setting checkbox
        self.zipID = wx.NewId()
        self.zipText = wx.StaticText (self.panel, wx.ID_ANY, "Look Inside ZIPs: ")
        self.zipCheckBox = wx.CheckBox(self.panel, self.zipID, "Enabled")
        self.zipCheckBox.SetValue(settings.LookInsideZips)
        self.ZipSizer = wx.BoxSizer (wx.HORIZONTAL)
        self.ZipSizer.Add (self.zipCheckBox, 0, wx.ALL)
        wx.EVT_CHECKBOX (self, self.zipID, self.OnZipChanged)

        # Create the titles.txt file setting checkbox
        self.titlesID = wx.NewId()
        self.titlesText = wx.StaticText (self.panel, wx.ID_ANY, "Read titles.txt files: ")
        self.titlesCheckBox = wx.CheckBox(self.panel, self.titlesID, "Enabled")
        self.titlesCheckBox.SetValue(self.KaraokeMgr.SongDB.Settings.ReadTitlesTxt)
        self.TitlesSizer = wx.BoxSizer (wx.HORIZONTAL)
        self.TitlesSizer.Add (self.titlesCheckBox, 0, wx.ALL)
        wx.EVT_CHECKBOX (self, self.titlesID, self.OnTitlesChanged)

        # Create the filesystem and zip file coding boxes.
        fsCodingText = wx.StaticText(self.panel, -1, "System filename encoding:")
        self.fsCoding = wx.ComboBox(
            self.panel, -1, value = settings.FilesystemCoding,
            choices = settings.Encodings)
        zipCodingText = wx.StaticText(self.panel, -1, "Filename encoding within zips:")
        self.zipCoding = wx.ComboBox(
            self.panel, -1, value = settings.ZipfileCoding,
            choices = settings.Encodings)

        # Create the hash-check options
        self.hashCheckBox = wx.CheckBox(self.panel, -1, "Check for identical files (by comparing MD5 hash)")
        self.hashCheckBox.SetValue(self.KaraokeMgr.SongDB.Settings.CheckHashes)
        self.Bind(wx.EVT_CHECKBOX, self.OnHashChanged, self.hashCheckBox)
        self.deleteIdenticalCheckBox = wx.CheckBox(self.panel, -1, "Delete duplicate identical files from disk")
        self.deleteIdenticalCheckBox.SetValue(self.KaraokeMgr.SongDB.Settings.DeleteIdentical)
        self.deleteIdenticalCheckBox.Enable(self.KaraokeMgr.SongDB.Settings.CheckHashes)
        self.Bind(wx.EVT_CHECKBOX, self.OnDeleteIdenticalChanged, self.deleteIdenticalCheckBox)

        # Create the scan folders button
        self.ScanText = wx.StaticText (self.panel, wx.ID_ANY, "Rescan all folders: ")
        self.ScanFoldersButtonID = wx.NewId()
        self.ScanFoldersButton = wx.Button(self.panel, self.ScanFoldersButtonID, "Scan Now")
        wx.EVT_BUTTON(self, self.ScanFoldersButtonID, self.OnScanFoldersClicked)

        # Create the save settings button
        self.SaveText = wx.StaticText (self.panel, wx.ID_ANY, "Save settings and song database: ")
        self.SaveSettingsButtonID = wx.NewId()
        self.SaveSettingsButton = wx.Button(self.panel, self.SaveSettingsButtonID, "Save and Close")
        wx.EVT_BUTTON(self, self.SaveSettingsButtonID, self.OnSaveSettingsClicked)

        # Create the settings and buttons grid
        self.LowerSizer = wx.FlexGridSizer(cols = 2, vgap = 3, hgap = 3)
        self.LowerSizer.Add(self.FiletypesText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.FiletypesSizer, 1, wx.ALL, 3)
        self.LowerSizer.Add(self.zipText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.ZipSizer, 1, wx.ALL, 3)
        self.LowerSizer.Add(self.titlesText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.TitlesSizer, 1, wx.ALL, 3)
        self.LowerSizer.Add(fsCodingText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.fsCoding, 1, wx.ALL, 3)
        self.LowerSizer.Add(zipCodingText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.zipCoding, 1, wx.ALL, 3)
        self.LowerSizer.Add((0, 0))
        self.LowerSizer.Add(self.hashCheckBox, 1, wx.LEFT | wx.RIGHT | wx.TOP, 3)
        self.LowerSizer.Add((0, 0))
        self.LowerSizer.Add(self.deleteIdenticalCheckBox, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM, 3)
        self.LowerSizer.Add(self.ScanText, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        self.LowerSizer.Add(self.ScanFoldersButton, 1, wx.ALL, 3)
        self.LowerSizer.Add(self.SaveText, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        self.LowerSizer.Add(self.SaveSettingsButton, 1, wx.ALL, 3)

        # Create the main sizer
        self.MainSizer = wx.BoxSizer(wx.VERTICAL)
        self.MainSizer.Add(self._HelpText, 0, wx.EXPAND | wx.TOP, 3)
        self.MainSizer.Add(self.FolderSizer, 1, wx.EXPAND, 3)
        self.MainSizer.Add(self.LowerSizer, 0, wx.ALL, 3)

        # Add a close handler to ask the user if they want to rescan folders
        self.ScanNeeded = False
        self.SaveNeeded = False
        wx.EVT_CLOSE(self, self.ExitHandler)

        self.panel.SetSizer(self.MainSizer)

        psizer = wx.BoxSizer(wx.VERTICAL)
        psizer.Add(self.panel, flag = wx.EXPAND, proportion = 1)
        self.SetSizerAndFit(psizer)

        pos = parent.GetPosition()
        parentSize = parent.GetSize()
        thisSize = self.GetSize()
        pos[0] += (parentSize[0] / 2) - (thisSize[0] / 2)
        pos[1] += (parentSize[1] / 2) - (thisSize[1] / 2)
        self.SetPosition(pos)

        self.Show()

    # User wants to add a folder
    def OnAddFolderClicked(self, event):
        dirDlg = wx.DirDialog(self)
        retval = dirDlg.ShowModal()
        FolderPath = dirDlg.GetPath()
        dirDlg.Destroy()

        if retval == wx.ID_OK:
            # User made a valid selection
            folder_list = self.KaraokeMgr.SongDB.GetFolderList()
            # Add it to the list control and song DB if not already in
            if FolderPath not in folder_list:
                self.KaraokeMgr.SongDB.FolderAdd(FolderPath)
                self.FolderList.Append(FolderPath)
                self.ScanNeeded = True
                self.SaveNeeded = True

    # User wants to delete a folder, get the selection in the folder list
    def OnDelFolderClicked(self, event):
        index = self.FolderList.GetSelection()
        Folder = self.FolderList.GetString(index)
        self.KaraokeMgr.SongDB.FolderDel(Folder)
        self.FolderList.Delete(index)
        self.ScanNeeded = True
        self.SaveNeeded = True

    def __getCodings(self):
        # Extract the filesystem and zip file encodings.  These aren't
        # captured as they are changed, unlike the other parameters
        # here, because that's just a nuisance.
        settings = self.KaraokeMgr.SongDB.Settings

        FilesystemCoding = self.fsCoding.GetValue()
        if FilesystemCoding != settings.FilesystemCoding:
            settings.FilesystemCoding = FilesystemCoding
            self.ScanNeeded = True
            self.SaveNeeded = True

        ZipfileCoding = self.zipCoding.GetValue()
        if ZipfileCoding != settings.ZipfileCoding:
            settings.ZipfileCoding = ZipfileCoding
            self.ScanNeeded = True
            self.SaveNeeded = True

    # User wants to rescan all folders
    def OnScanFoldersClicked(self, event):
        self.__getCodings()
        # Create a temporary SongDatabase we can use to initiate the
        # scanning.  This way, if the user cancels out halfway
        # through, we can abandon it instead of being stuck with a
        # halfway-scanned database.
        songDb = pykdb.SongDB()
        songDb.Settings = self.KaraokeMgr.SongDB.Settings
        cancelled = songDb.BuildSearchDatabase(
            wxAppYielder(), wxBusyCancelDialog(self.KaraokeMgr.Frame, "Searching"))
        if not cancelled:
            # The user didn't cancel, so make the new database the
            # effective one.

            self.KaraokeMgr.SongDB = songDb
            pykdb.globalSongDB = songDb
            self.ScanNeeded = False
            self.SaveNeeded = True

    # User wants to save all settings
    def OnSaveSettingsClicked(self, event):
        self.__getCodings()
        self.Show(False)
        self.KaraokeMgr.SongDB.SaveSettings()
        self.KaraokeMgr.SongDB.SaveDatabase()
        self.SaveNeeded = False
        self.Destroy()

    # User changed a checkbox, just do them all again
    def OnFileExtChanged(self, event):
        ignored_ext_list = []
        for ext, cb in self.extCheckBoxes.items():
            if not cb.IsChecked():
                ignored_ext_list.append(ext)
        self.KaraokeMgr.SongDB.Settings.IgnoredExtensions = ignored_ext_list
        self.ScanNeeded = True
        self.SaveNeeded = True

    # User changed the zip checkbox, enable it
    def OnZipChanged(self, event):
        self.KaraokeMgr.SongDB.Settings.LookInsideZips = self.zipCheckBox.IsChecked()
        self.ScanNeeded = True
        self.SaveNeeded = True

    # User changed the titles.txt checkbox, enable it
    def OnTitlesChanged(self, event):
        self.KaraokeMgr.SongDB.Settings.ReadTitlesTxt = self.titlesCheckBox.IsChecked()
        self.ScanNeeded = True
        self.SaveNeeded = True

    # User changed the hash checkbox, enable it
    def OnHashChanged(self, event):
        self.KaraokeMgr.SongDB.Settings.CheckHashes = self.hashCheckBox.IsChecked()
        self.deleteIdenticalCheckBox.Enable(self.KaraokeMgr.SongDB.Settings.CheckHashes)
        self.ScanNeeded = True
        self.SaveNeeded = True

    # User changed the delete identical checkbox, enable it
    def OnDeleteIdenticalChanged(self, event):
        self.KaraokeMgr.SongDB.Settings.DeleteIdentical = self.deleteIdenticalCheckBox.IsChecked()
        self.ScanNeeded = True
        self.SaveNeeded = True

    # Popup asking if want to rescan the database after changing settings
    def ExitHandler(self, event):
        self.__getCodings()
        if self.ScanNeeded:
            changedString = "You have changed settings, would you like to rescan your folders now?"
            answer = wx.MessageBox(changedString, "Rescan folders now?", wx.YES_NO | wx.ICON_QUESTION)
            if answer == wx.YES:
                cancelled = self.KaraokeMgr.SongDB.BuildSearchDatabase(
                    wxAppYielder(), wxBusyCancelDialog(self.KaraokeMgr.Frame, "Searching"))
                if not cancelled:
                    self.SaveNeeded = True
        if self.SaveNeeded:
            saveString = "You have made changes, would you like to save your settings and database now?"
            answer = wx.MessageBox(saveString, "Save changes?", wx.YES_NO | wx.ICON_QUESTION)
            if answer == wx.YES:
                self.Show(False)
                self.KaraokeMgr.SongDB.SaveSettings()
                self.KaraokeMgr.SongDB.SaveDatabase()
        self.Destroy()


# Popup config window for setting full-screen mode etc
class ConfigWindow (wx.Frame):
    def __init__(self,parent,id,title,KaraokeMgr):
        wx.Frame.__init__(self, parent, -1, title,
                          style = wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.parent = parent
        self.panel = wx.Panel(self)
        self.KaraokeMgr = KaraokeMgr

        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.panel)

        self.__layoutDisplayPage()
        self.__layoutAudioPage()
        self.__layoutKarPage()
        self.__layoutCdgPage()
        self.__layoutMpgPage()

        vsizer.Add(self.notebook, flag = wx.EXPAND | wx.ALL,
                   proportion = 1, border = 5)

        # Make the OK and Cancel buttons.

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        b = wx.Button(self.panel, wx.ID_OK, 'OK')
        self.Bind(wx.EVT_BUTTON, self.clickedOK, b)
        hsizer.Add(b, flag = wx.EXPAND | wx.RIGHT | wx.LEFT, border = 10)

        b = wx.Button(self.panel, wx.ID_CANCEL, 'Cancel')
        self.Bind(wx.EVT_BUTTON, self.clickedCancel, b)
        hsizer.Add(b, flag = wx.EXPAND | wx.RIGHT, border = 10)
        vsizer.Add(hsizer, flag = wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM,
                   border = 10)

        self.panel.SetSizer(vsizer)

        psizer = wx.BoxSizer(wx.VERTICAL)
        psizer.Add(self.panel, flag = wx.EXPAND, proportion = 1)
        self.SetSizerAndFit(psizer)

        pos = parent.GetPosition()
        parentSize = parent.GetSize()
        thisSize = self.GetSize()
        pos[0] += (parentSize[0] / 2) - (thisSize[0] / 2)
        pos[1] += max((parentSize[1] / 2) - (thisSize[1] / 2), 0)
        self.SetPosition(pos)

        self.Show()

    def __layoutDisplayPage(self):
        """ Creates the page for the display config options """

        settings = self.KaraokeMgr.SongDB.Settings

        panel = wx.Panel(self.notebook)
        dispsizer = wx.BoxSizer(wx.VERTICAL)

        self.FSCheckBox = wx.CheckBox(panel, -1, "Enable Player Full-Screen Mode")
        self.FSCheckBox.SetValue(settings.FullScreen)
        dispsizer.Add(self.FSCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)
        self.NoFrameCheckBox = wx.CheckBox(panel, -1, "Enable Player With No Frame")
        self.NoFrameCheckBox.SetValue(settings.NoFrame)
        dispsizer.Add(self.NoFrameCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        self.DoubleBufCheckBox = wx.CheckBox(panel, -1, "Use double-buffered rendering (recommended)")
        self.DoubleBufCheckBox.SetValue(settings.DoubleBuf)
        dispsizer.Add(self.DoubleBufCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)
        self.HardwareSurfaceCheckBox = wx.CheckBox(panel, -1, "Request a hardware surface (recommended)")
        self.HardwareSurfaceCheckBox.SetValue(settings.HardwareSurface)
        dispsizer.Add(self.HardwareSurfaceCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        gsizer = wx.FlexGridSizer(0, 4, 2, 0)
        text = wx.StaticText(panel, -1, "Player Window Size:")
        gsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        self.PlayerSizeX = wx.TextCtrl(panel, -1, value = str(settings.PlayerSize[0]))
        gsizer.Add(self.PlayerSizeX, flag = wx.EXPAND | wx.RIGHT, border = 5)
        self.PlayerSizeY = wx.TextCtrl(panel, -1, value = str(settings.PlayerSize[1]))
        gsizer.Add(self.PlayerSizeY, flag = wx.EXPAND | wx.RIGHT, border = 10)
        gsizer.Add((0, 0))

        # Window placement only seems to work reliably on Linux.  Only
        # offer it there.
        self.DefaultPosCheckBox = None
        if env == ENV_POSIX:
            text = wx.StaticText(panel, -1, "Player Placement:")
            gsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
            pos_x = pos_y = ''
            if settings.PlayerPosition:
                pos_x, pos_y = settings.PlayerPosition
            self.PlayerPositionX = wx.TextCtrl(panel, -1, value = str(pos_x))
            gsizer.Add(self.PlayerPositionX, flag = wx.EXPAND | wx.RIGHT, border = 5)
            self.PlayerPositionY = wx.TextCtrl(panel, -1, value = str(pos_y))
            gsizer.Add(self.PlayerPositionY, flag = wx.EXPAND | wx.RIGHT, border = 10)

            self.DefaultPosCheckBox = wx.CheckBox(panel, -1, "Default placement")
            self.Bind(wx.EVT_CHECKBOX, self.clickedDefaultPos, self.DefaultPosCheckBox)
            self.DefaultPosCheckBox.SetValue(settings.PlayerPosition is None)
            self.clickedDefaultPos(None)

            gsizer.Add(self.DefaultPosCheckBox, flag = wx.EXPAND)
        dispsizer.Add(gsizer, flag = wx.EXPAND | wx.ALL, border = 10)

        self.SplitVerticallyCheckBox = wx.CheckBox(panel, -1, "Split play-list window vertically")
        self.SplitVerticallyCheckBox.SetValue(settings.SplitVertically)
        dispsizer.Add(self.SplitVerticallyCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        # Enables or disables the auto play-list functionality
        self.AutoPlayCheckBox = wx.CheckBox(panel, -1, "Enable play-list continuous play")
        self.AutoPlayCheckBox.SetValue(settings.AutoPlayList)
        dispsizer.Add(self.AutoPlayCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        # Enables or disables the double-click playing from the play-list
        self.DoubleClickPlayCheckBox = wx.CheckBox(panel, -1, "Enable playing from play-list")
        self.DoubleClickPlayCheckBox.SetValue(settings.DoubleClickPlayList)
        dispsizer.Add(self.DoubleClickPlayCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        # Enables or disables the clearing of the play-list from teh list
        self.ClearFromPlayListCheckBox = wx.CheckBox(panel, -1, "Enable playlist clearing from play-list")
        self.ClearFromPlayListCheckBox.SetValue(settings.ClearFromPlayList)
        dispsizer.Add(self.ClearFromPlayListCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        # Enables or disables playing from a search list functionality
        self.PlayFromSearchListCheckBox = wx.CheckBox(panel, -1, "Enable playing from search-list")
        self.PlayFromSearchListCheckBox.SetValue(settings.PlayFromSearchList)
        dispsizer.Add(self.PlayFromSearchListCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        # Enables or disables the kamikaze funtionality
        self.KamikazeCheckBox = wx.CheckBox(panel, -1, "Enable kamikaze play")
        self.KamikazeCheckBox.SetValue(settings.Kamikaze)
        dispsizer.Add(self.KamikazeCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        # Enables or disables the performer functionality
        self.PerformerCheckBox = wx.CheckBox(panel, -1, "Enable performer enquiry")
        self.PerformerCheckBox.SetValue(settings.UsePerformerName)
        dispsizer.Add(self.PerformerCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        # Enables or disables the performer functionality
        self.ArtistTitleCheckBox = wx.CheckBox(panel, -1, "Display derived Artist/Title columns")
        self.ArtistTitleCheckBox.SetValue(settings.DisplayArtistTitleCols)
        dispsizer.Add(self.ArtistTitleCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        panel.SetSizer(dispsizer)
        self.notebook.AddPage(panel, "Display")


    def __layoutAudioPage(self):
        """ Creates the page for the audio config options """

        settings = self.KaraokeMgr.SongDB.Settings

        panel = wx.Panel(self.notebook)
        audsizer = wx.BoxSizer(wx.VERTICAL)

        self.StereoCheckBox = wx.CheckBox(panel, -1, "Stereo")
        self.StereoCheckBox.SetValue(settings.NumChannels > 1)
        audsizer.Add(self.StereoCheckBox, flag = wx.ALL, border = 10)

        self.UseMp3SettingsCheckBox = wx.CheckBox(panel, -1, "Use source sample rate if possible")
        self.UseMp3SettingsCheckBox.SetValue(settings.UseMp3Settings)
        audsizer.Add(self.UseMp3SettingsCheckBox, flag = wx.EXPAND | wx.LEFT, border = 10)

        gsizer = wx.FlexGridSizer(0, 2, 2, 0)
        text = wx.StaticText(panel, -1, "Sample rate:")
        gsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        self.SampleRate = wx.ComboBox(
            panel, -1, value = str(settings.SampleRate),
            choices = map(str, settings.SampleRates))
        gsizer.Add(self.SampleRate, flag = wx.EXPAND)

        text = wx.StaticText(panel, -1, "Buffer size (ms):")
        gsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        self.BufferSize = wx.TextCtrl(panel, -1,
                                      value = str(settings.BufferMs))
        gsizer.Add(self.BufferSize, flag = wx.EXPAND)

        text = wx.StaticText(panel, -1, "Sync delay (ms):")
        gsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        self.SyncDelay = wx.TextCtrl(panel, -1,
                                     value = str(settings.SyncDelayMs))
        gsizer.Add(self.SyncDelay, flag = wx.EXPAND)

        audsizer.Add(gsizer, flag = wx.EXPAND | wx.ALL, border = 10)
        panel.SetSizer(audsizer)

        self.notebook.AddPage(panel, "Audio")


    def __layoutKarPage(self):
        """ Creates the page for the kar-file config options """

        settings = self.KaraokeMgr.SongDB.Settings

        panel = wx.Panel(self.notebook)
        karsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(panel, -1, "Encoding:")
        hsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        self.KarEncoding = wx.ComboBox(
            panel, -1, value = settings.KarEncoding,
            choices = settings.Encodings)
        hsizer.Add(self.KarEncoding, flag = wx.EXPAND, proportion = 1)
        karsizer.Add(hsizer, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(panel, -1, "Font:")
        hsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        self.KarFont = copy.copy(settings.KarFont)
        self.KarFontLabel = wx.StaticText(panel, -1, self.KarFont.getDescription())
        # Make sure the label has enough space to include big font names.
        w, h = self.KarFontLabel.GetSize()
        self.KarFontLabel.SetMinSize((max(w, 100), h))
        hsizer.Add(self.KarFontLabel, flag = wx.ALIGN_CENTER_VERTICAL, proportion = 1)
        b = wx.Button(panel, -1, 'Select')
        self.Bind(wx.EVT_BUTTON, self.clickedFontSelect, b)
        hsizer.Add(b, flag = wx.EXPAND | wx.LEFT, border = 10)
        b = wx.Button(panel, -1, 'Browse')
        self.Bind(wx.EVT_BUTTON, self.clickedFontBrowse, b)
        hsizer.Add(b, flag = wx.EXPAND | wx.LEFT, border = 10)

        karsizer.Add(hsizer, flag = wx.EXPAND | wx.ALL, border = 10)

        gsizer = wx.FlexGridSizer(0, 2, 2, 0)
        gsizer.AddGrowableCol(1, 1)
        text = wx.StaticText(panel, -1, "MIDI Sample rate:")
        gsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        self.MIDISampleRate = wx.ComboBox(
            panel, -1, value = str(settings.MIDISampleRate),
            choices = map(str, settings.SampleRates))
        gsizer.Add(self.MIDISampleRate, flag = wx.EXPAND)
        karsizer.Add(gsizer, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = 10)


        self.Colours = {}
        self.ColourSamples = {}
        gsizer = wx.FlexGridSizer(0, 3, 2, 0)
        gsizer.AddGrowableCol(1, 1)
        for attribName in ['Ready', 'Sweep', 'Info', 'Title', 'Background']:
            text = wx.StaticText(panel, -1, "%s colour:" % (attribName))
            gsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
            colour = getattr(settings, 'Kar%sColour' % (attribName))
            sample = wx.Panel(panel)
            sample.SetSize((50, 10))
            sample.SetBackgroundColour(colour)
            gsizer.Add(sample, flag = wx.EXPAND, proportion = 1)
            b = wx.Button(panel, -1, 'Select')
            self.Bind(wx.EVT_BUTTON, lambda evt, attribName = attribName: self.clickedColourSelect(attribName), b)
            gsizer.Add(b, flag = wx.EXPAND | wx.LEFT, border = 10)

            self.Colours[attribName] = colour
            self.ColourSamples[attribName] = sample
        karsizer.Add(gsizer, flag = wx.EXPAND | wx.ALL, border = 10)

        panel.SetSizer(karsizer)
        self.notebook.AddPage(panel, 'Kar (MIDI)')


    def __layoutCdgPage(self):
        """ Creates the page for the cdg-file config options """

        settings = self.KaraokeMgr.SongDB.Settings

        panel = wx.Panel(self.notebook)
        cdgsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(panel, -1, "Zoom:")
        hsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        selection = settings.Zoom.index(settings.CdgZoom)
        choices = map(lambda z: '%s: %s' % (z, settings.ZoomDesc[z]), settings.Zoom)
        self.CdgZoom = wx.Choice(panel, -1, choices = choices)
        self.CdgZoom.SetSelection(selection)
        hsizer.Add(self.CdgZoom, flag = wx.EXPAND, proportion = 1)
        cdgsizer.Add(hsizer, flag = wx.EXPAND | wx.ALL, border = 10)

        # Enable/disable optimised C implementation of CDG decoder
        self.CdgUseCCheckBox = wx.CheckBox(panel, -1, "Use optimised (C-based) implementation")
        self.CdgUseCCheckBox.SetValue(settings.CdgUseC)
        # Check that the C implementation is available.
        if not pycdg.aux_c:
            self.CdgUseCCheckBox.SetValue(False)
            self.CdgUseCCheckBox.Enable(False)
        cdgsizer.Add(self.CdgUseCCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        # Scan song information from the file names.
        infoSizer = wx.BoxSizer(wx.VERTICAL)
        # Add checkbox for song-derivation enable/disable
        self.SongInfoCheckBoxID = wx.NewId()
        self.SongInfoCheckBox = wx.CheckBox(panel, self.SongInfoCheckBoxID, "Derive song information from file names?")
        wx.EVT_CHECKBOX(self, self.SongInfoCheckBoxID, self.setSongInfoCheckBox)
        infoSizer.Add(self.SongInfoCheckBox, flag = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border = 7)
        # Add sub-options for song-derivation
        infoOptionsSizer = wx.BoxSizer(wx.VERTICAL)
        # Add combo-box for choosing filename scheme
        infoFormatSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.FileNameStylesText = wx.StaticText(panel, -1, "File naming scheme: ")
        infoFormatSizer.Add(self.FileNameStylesText, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT, border = 7)
        self.FileNameStyles = wx.ComboBox(panel, -1, choices = settings.FileNameCombinations, style = wx.CB_READONLY)
        infoFormatSizer.Add(self.FileNameStyles, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, proportion = 1, border = 7)
        infoOptionsSizer.Add(infoFormatSizer, flag = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND, proportion = 1, border = 7)
        # Add checkbox for exclusion of songs from database of files not matching the above scheme
        self.ExcludeNonMatchingCheckBox = wx.CheckBox(panel, -1, "Exclude from search results files not matching naming scheme")
        self.ExcludeNonMatchingCheckBox.SetValue(settings.ExcludeNonMatchingFilenames)
        infoOptionsSizer.Add(self.ExcludeNonMatchingCheckBox, border = 7)
        infoSizer.Add(infoOptionsSizer, flag = wx.ALIGN_RIGHT, border = 7)
        # Add the sizer with all info-related options to the main page sizer
        cdgsizer.Add(infoSizer, flag = wx.EXPAND | wx.ALL, border = 10)

        # Update the display to match whether derivation enabled (grey out options if not)
        if settings.CdgDeriveSongInformation:
            self.SongInfoCheckBox.SetValue(True)
            self.FileNameStyles.Enable(True)
            self.FileNameStylesText.Enable(True)
            self.FileNameStyles.SetSelection(settings.CdgFileNameType)
            self.ExcludeNonMatchingCheckBox.Enable (True)
        else:
            self.FileNameStyles.Enable(False)
            self.FileNameStylesText.Enable(False)
            self.ExcludeNonMatchingCheckBox.Enable (False)

        # Now add final sizer to panel
        panel.SetSizer(cdgsizer)
        self.notebook.AddPage(panel, 'CDG+MP3/OGG')


    def __layoutMpgPage(self):
        """ Creates the page for the mpg-file config options """

        settings = self.KaraokeMgr.SongDB.Settings

        panel = wx.Panel(self.notebook)
        mpgsizer = wx.BoxSizer(wx.VERTICAL)

        self.MpgNativeCheckBox = wx.CheckBox(
            panel, -1, "Use native viewer for mpg files")
        self.MpgNativeCheckBox.SetValue(settings.MpgNative)
        if not pympg.movie:
            self.MpgNativeCheckBox.SetValue(False)
            self.MpgNativeCheckBox.Enable(False)

        mpgsizer.Add(self.MpgNativeCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(panel, -1, "External viewer:")
        hsizer.Add(text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        self.MpgExternal = wx.TextCtrl(panel, -1, value = settings.MpgExternal)
        hsizer.Add(self.MpgExternal, flag = wx.EXPAND, proportion = 1)

        b = wx.Button(panel, -1, 'Browse')
        self.Bind(wx.EVT_BUTTON, self.clickedExternalBrowse, b)
        hsizer.Add(b, flag = wx.EXPAND | wx.LEFT, border = 10)
        mpgsizer.Add(hsizer, flag = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        self.MpgExternalThreadedCheckBox = wx.CheckBox(
            panel, -1, "Use a sub-thread to wait for external viewer")
        self.MpgExternalThreadedCheckBox.SetValue(settings.MpgExternalThreaded)
        mpgsizer.Add(self.MpgExternalThreadedCheckBox, flag = wx.LEFT | wx.RIGHT | wx.TOP, border = 10)

        panel.SetSizer(mpgsizer)
        self.notebook.AddPage(panel, 'MPG/AVI')


    def clickedFontSelect(self, event):
        fontData = wx.FontData()
        if self.KarFont.size:
            font = self.findWxFont(self.KarFont)
            if font:
                fontData.SetInitialFont(font)

        dlg = wx.FontDialog(self, fontData)
        result = dlg.ShowModal()
        if result != wx.ID_OK:
            dlg.Destroy()
            return

        font = dlg.GetFontData().GetChosenFont()
        self.KarFont = pykdb.FontData(font.GetFaceName(),
                                      font.GetPointSize(),
                                      (font.GetWeight() == wx.FONTWEIGHT_BOLD),
                                      (font.GetStyle() == wx.FONTSTYLE_ITALIC))
        dlg.Destroy()

        self.KarFontLabel.SetLabel(self.KarFont.getDescription())

    def clickedFontBrowse(self, event):
        defaultDir = manager.FontPath
        defaultFile = ''
        if not self.KarFont.size:
            defaultDir, defaultFile = os.path.split(self.KarFont.name)
            if defaultDir == '':
                defaultDir = manager.FontPath

        dlg = wx.FileDialog(self, 'Font file',
                            defaultDir = defaultDir, defaultFile = defaultFile,
                            wildcard = 'True Type Fonts (*.ttf)|*.ttf|All files|*')
        result = dlg.ShowModal()
        if result != wx.ID_OK:
            dlg.Destroy()
            return

        filename = dlg.GetPath()
        dlg.Destroy()

        # Is it a file within the font directory?
        pathname, basename = os.path.split(filename)

        if os.path.normcase(os.path.realpath(pathname)) == os.path.normcase(os.path.realpath(manager.FontPath)):
            # Yes, it is a file within the font directory.  In this
            # case, just store the basename.
            filename = basename

        self.KarFont = pykdb.FontData(filename)

        self.KarFontLabel.SetLabel(self.KarFont.getDescription())

    def clickedColourSelect(self, attribName):
        colour = self.Colours[attribName]
        colourData = wx.ColourData()
        colourData.SetColour(colour)

        dlg = wx.ColourDialog(self, colourData)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        data = dlg.GetColourData()
        r, g, b = data.GetColour()
        dlg.Destroy()

        colour = (r, g, b)
        self.Colours[attribName] = colour
        sample = self.ColourSamples[attribName]
        sample.SetBackgroundColour(colour)
        sample.ClearBackground()

    def setSongInfoCheckBox(self, event):
        """ This enables and disables the ability to derive song information from file names"""
        if self.SongInfoCheckBox.IsChecked():
            self.FileNameStyles.Enable(True)
            self.FileNameStylesText.Enable(True)
            self.FileNameStyles.SetSelection(0)
            self.ExcludeNonMatchingCheckBox.Enable (True)
        else:
            self.FileNameStyles.Enable(False)
            self.FileNameStylesText.Enable(False)
            self.ExcludeNonMatchingCheckBox.Enable (False)

    def clickedCancel(self, event):
        self.Show(False)
        self.Destroy()

    def clickedDefaultPos(self, event):
        # Changing this checkbox changes the enabled state of the
        # window position fields.
        checked = self.DefaultPosCheckBox.IsChecked()
        self.PlayerPositionX.Enable(not checked)
        self.PlayerPositionY.Enable(not checked)

    def clickedExternalBrowse(self, event):
        # Pop up a file browser to find the appropriate external program.

        if env == ENV_WINDOWS:
            wildcard = 'Executable Programs (*.exe)|*.exe'
        else:
            wildcast = 'All files|*'
        dlg = wx.FileDialog(self, 'External Movie Player',
                            wildcard = wildcard)
        result = dlg.ShowModal()
        if result != wx.ID_OK:
            dlg.Destroy()
            return

        self.MpgExternal.SetValue(dlg.GetPath())
        dlg.Destroy()

    def clickedOK(self, event):
        self.Show(False)
        settings = self.KaraokeMgr.SongDB.Settings

        settings.FullScreen = self.FSCheckBox.IsChecked()
        settings.NoFrame = self.NoFrameCheckBox.IsChecked()
        settings.DoubleBuf = self.DoubleBufCheckBox.IsChecked()
        settings.HardwareSurface = self.HardwareSurfaceCheckBox.IsChecked()
        settings.PlayerPosition = None

        splitVertically = self.SplitVerticallyCheckBox.IsChecked()
        if splitVertically != settings.SplitVertically:
            settings.SplitVertically = splitVertically
            # Re-split the main window.
            parent = self.parent
            parent.splitter.Unsplit()
            if splitVertically:
                parent.splitter.SplitVertically(parent.leftPanel, parent.rightPanel, 0.5)
            else:
                parent.splitter.SplitHorizontally(parent.leftPanel, parent.rightPanel, 0.5)

        # Save the auto play option
        if self.AutoPlayCheckBox.IsChecked():
            settings.AutoPlayList = True
            self.parent.playlistButton.SetLabel('Start')
        else:
            settings.AutoPlayList = False
            self.parent.playlistButton.SetLabel('Play')

        # Save the double-click play option
        if self.DoubleClickPlayCheckBox.IsChecked():
            settings.DoubleClickPlayList = True
        else:
            settings.DoubleClickPlayList = False

        # Save the playlist clear option
        if self.ClearFromPlayListCheckBox.IsChecked():
            settings.ClearFromPlayList = True
        else:
            settings.ClearFromPlayList = False

        # Save the kamikaze option
        if self.KamikazeCheckBox.IsChecked():
            settings.Kamikaze = True
            self.parent.playButton.SetLabel('Kamikaze')
            self.parent.Unbind(wx.EVT_BUTTON, self.parent.playButton)
            self.parent.Bind(wx.EVT_BUTTON, self.parent.OnKamikazeClicked, self.parent.playButton)
        else:
            settings.Kamikaze = False
            self.parent.playButton.SetLabel('Play')
            self.parent.Unbind(wx.EVT_BUTTON, self.parent.playButton)
            self.parent.Bind(wx.EVT_BUTTON, self.parent.OnPlayClicked, self.parent.playButton)

        # Save the performer option
        if self.PerformerCheckBox.IsChecked() != settings.UsePerformerName:
            if self.PerformerCheckBox.IsChecked():
                settings.UsePerformerName = True
            else:
                settings.UsePerformerName = False
            # Delete and reinitialise the display columns
            self.parent.PlaylistPanel.DeleteColumns()
            self.parent.PlaylistPanel.CreateColumns()
            self.parent.PlaylistPanel.ReloadData()
 
        # Save the Artist/Title display option
        if self.ArtistTitleCheckBox.IsChecked() != settings.DisplayArtistTitleCols:
            # Store the new setting
            if self.ArtistTitleCheckBox.IsChecked():
                settings.DisplayArtistTitleCols = True
            else:
                settings.DisplayArtistTitleCols = False
            # Delete and reinitialise the display columns
            self.parent.PlaylistPanel.DeleteColumns()
            self.parent.PlaylistPanel.CreateColumns()
            self.parent.PlaylistPanel.ReloadData()

        # Save the search list playing option
        if self.PlayFromSearchListCheckBox.IsChecked():
            settings.PlayFromSearchList = True
        else:
            settings.PlayFromSearchList = False

        if self.DefaultPosCheckBox:
            if not self.DefaultPosCheckBox.IsChecked():
                try:
                    pos_x = int(self.PlayerPositionX.GetValue())
                    pos_y = int(self.PlayerPositionY.GetValue())
                    settings.PlayerPosition = (pos_x, pos_y)
                except:
                    pass

        try:
            size_x = int(self.PlayerSizeX.GetValue())
            size_y = int(self.PlayerSizeY.GetValue())
            settings.PlayerSize = (size_x, size_y)
        except:
            pass

        settings.NumChannels = 1
        if self.StereoCheckBox.IsChecked():
            settings.NumChannels = 2

        settings.UseMp3Settings = self.UseMp3SettingsCheckBox.IsChecked()

        try:
            rate = int(self.SampleRate.GetValue())
            settings.SampleRate = rate
        except:
            pass

        try:
            rate = int(self.MIDISampleRate.GetValue())
            settings.MIDISampleRate = rate
        except:
            pass

        try:
            buffer = int(self.BufferSize.GetValue())
            settings.BufferMs = buffer
        except:
            pass

        try:
            sync = int(self.SyncDelay.GetValue())
            settings.SyncDelayMs = sync
        except:
            pass

        settings.KarEncoding = self.KarEncoding.GetValue()
        settings.KarFont = self.KarFont
        settings.KarReadyColour = self.Colours['Ready']
        settings.KarSweepColour = self.Colours['Sweep']
        settings.KarInfoColour = self.Colours['Info']
        settings.KarTitleColour = self.Colours['Title']
        settings.KarBackgroundColour = self.Colours['Background']

        selection = self.CdgZoom.GetSelection()
        settings.CdgZoom = settings.Zoom[selection]
        settings.CdgUseC = self.CdgUseCCheckBox.IsChecked()
        # Check to see if we will need to update the database
        if ((self.SongInfoCheckBox.IsChecked() == settings.CdgDeriveSongInformation) 
            and (settings.CdgFileNameType == self.FileNameStyles.GetCurrentSelection())
            and (settings.ExcludeNonMatchingFilenames == self.ExcludeNonMatchingCheckBox.IsChecked())):
            needDabaseRescan = False
        else:
            needDabaseRescan = True
            # Update cdg file scanning settings
            if self.SongInfoCheckBox.IsChecked() or (settings.CdgFileNameType != self.FileNameStyles.GetCurrentSelection()):
                settings.CdgDeriveSongInformation = True
                settings.CdgFileNameType = self.FileNameStyles.GetCurrentSelection()
            else:
                settings.CdgDeriveSongInformation = False
                settings.CdgFileNameType = -1
            settings.ExcludeNonMatchingFilenames = self.ExcludeNonMatchingCheckBox.IsChecked()

        settings.MpgNative = self.MpgNativeCheckBox.IsChecked()
        settings.MpgExternal = self.MpgExternal.GetValue()
        settings.MpgExternalThreaded = self.MpgExternalThreadedCheckBox.IsChecked()

        self.KaraokeMgr.SongDB.SaveSettings()
        # Update our song database if we need to.
        if needDabaseRescan:
            if self.reScanDatabase():
                # update our list panel
                self.parent.SearchPanel.UpdateListLayout()
            else: # User cancelled database scan return file name deriving to previous settings
                if self.SongInfoCheckBox.IsChecked():
                    settings.CdgDeriveSongInformation = False
                    settings.CdgFileNameType = -1
                else:
                    settings.CdgDeriveSongInformation = True
                    settings.CdgFileNameType = self.FileNameStyles.GetCurrentSelection()
                self.KaraokeMgr.SongDB.SaveSettings()

        self.Destroy()

    def reScanDatabase(self):
        """ This rescans the database when the CDG naming convention changes. """
        # Create a temporary SongDatabase we can use to initiate the
        # scanning.  This way, if the user cancels out halfway
        # through, we can abandon it instead of being stuck with a
        # halfway-scanned database.
        songDb = pykdb.SongDB()
        songDb.Settings = self.KaraokeMgr.SongDB.Settings
        cancelled = songDb.BuildSearchDatabase(
            wxAppYielder(), wxBusyCancelDialog(self.KaraokeMgr.Frame, "Re-Scanning Database"))
        if not cancelled:
            # The user didn't cancel, so make the new database the
            # effective one.

            self.KaraokeMgr.SongDB = songDb
            pykdb.globalSongDB = songDb
            self.KaraokeMgr.SongDB.SaveDatabase()
            return True
        else:
            return False

    def findWxFont(self, fontData):
        """ Returns a wx.Font selected by this data. """

        size = fontData.size or 10
        family = wx.FONTFAMILY_DEFAULT
        style = wx.FONTSTYLE_NORMAL
        if fontData.italic:
            style = wx.FONTSTYLE_ITALIC
        weight = wx.FONTWEIGHT_NORMAL
        if fontData.bold:
            weight = wx.FONTWEIGHT_BOLD
        name = fontData.name or ''

        font = wx.TheFontList.FindOrCreateFont(
            size, family, style, weight, False, name)

        return font

class Wx26AboutWindow(wx.Frame):

    """ Shows the friendly little "about" window. Wx2.6 version only. """

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, 'About PyKaraoke',
                          style = wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.parent = parent
        self.__layoutWindow()

        pos = parent.GetPosition()
        parentSize = parent.GetSize()
        thisSize = self.GetSize()
        pos[0] += (parentSize[0] / 2) - (thisSize[0] / 2)
        pos[1] += (parentSize[1] / 2) - (thisSize[1] / 2)
        self.SetPosition(pos)

        self.Show()

    def __layoutWindow(self):
        self.panel = wx.Panel(self)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        font = self.GetFont()
        topFont = wx.TheFontList.FindOrCreateFont(
            24,
            family = font.GetFamily(),
            style = wx.FONTSTYLE_ITALIC,
            weight = wx.FONTWEIGHT_BOLD)
        versionFont = wx.TheFontList.FindOrCreateFont(
            10,
            family = font.GetFamily(),
            style = font.GetStyle(),
            weight = wx.FONTWEIGHT_NORMAL)


        text = wx.StaticText(self.panel, -1, 'PyKaraoke')
        text.SetFont(topFont)
        vsizer.Add(text, flag = wx.ALIGN_CENTER)

        fullpath = self.parent.BigIconPath
        image = wx.Image(fullpath)
        image.ConvertAlphaToMask()
        bitmap = wx.BitmapFromImage(image)

        label = wx.StaticBitmap(self.panel, -1, bitmap)
        vsizer.Add(label, flag = wx.ALIGN_CENTER | wx.TOP, border = 10)

        text = wx.StaticText(self.panel, -1, 'PyKaraoke version %s' % (
            pykversion.PYKARAOKE_VERSION_STRING))
        text.SetFont(versionFont)
        vsizer.Add(text, flag = wx.ALIGN_CENTER | wx.TOP, border = 10)
        text = wx.StaticText(self.panel, -1, 'wxPython version %s' % (
            wx.VERSION_STRING))
        text.SetFont(versionFont)
        vsizer.Add(text, flag = wx.ALIGN_CENTER)

        pyver = sys.version
        if ' ' in pyver:
            pyver = pyver[:pyver.index(' ')]
        text = wx.StaticText(self.panel, -1, 'Python version %s\n' % (pyver))
        text.SetFont(versionFont)
        vsizer.Add(text, flag = wx.ALIGN_CENTER)

        # Add License information
        text = wx.StaticText(self.panel, -1, " PyKaraoke is free software; you can redistribute it and/or modify it under\n the terms of the GNU Lesser General Public License as published by the\n Free Software Foundation; either version 2.1 of the License, or (at your\n option) any later version.\n \n PyKaraoke is distributed in the hope that it will be useful, but WITHOUT\n ANY WARRANTY; without even the implied warranty of MERCHANTABILITY\n or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General\n Public License for more details.\n \n You should have received a copy of the GNU Lesser General Public\n License along with this library; if not, write to the\n Free Software Foundation, Inc.\n 59 Temple Place, Suite 330\n Boston, MA  02111-1307  USA")
        text.SetFont(versionFont)
        vsizer.Add(text, flag = wx.ALIGN_CENTER)

        b = wx.Button(self.panel, wx.ID_OK, 'OK')
        self.Bind(wx.EVT_BUTTON, self.clickedOK, b)
        vsizer.Add(b, flag = wx.ALIGN_CENTER | wx.TOP, border = 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(vsizer, flag = wx.EXPAND | wx.ALL, border = 10,
                   proportion = 1)

        self.panel.SetSizerAndFit(hsizer)
        self.Fit()

    def clickedOK(self, event):
        self.Show(False)
        self.Destroy()

class ExportWindow(wx.Frame):

    """ Shows the dialog for exporting the song list. """

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, 'Export song list',
                          style = wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.parent = parent
        self.__layoutWindow()

        pos = parent.GetPosition()
        parentSize = parent.GetSize()
        thisSize = self.GetSize()
        pos[0] += (parentSize[0] / 2) - (thisSize[0] / 2)
        pos[1] += (parentSize[1] / 2) - (thisSize[1] / 2)
        self.SetPosition(pos)

        self.Show()

    def __layoutWindow(self):
        self.panel = wx.Panel(self)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        text = wx.StaticText(self.panel, -1,
                             'This will save the entire song list as a tab-delimited text file, which can\n'
                             'then be imported into a spreadsheet or other database program.  It\n'
                             'writes a file which is essentially similar to the titles.txt file.')
        vsizer.Add(text, flag = wx.ALIGN_CENTER)

        cb = wx.CheckBox(self.panel, -1, 'Write identical artist/title files to one line')
        self.sameSongOneLine = cb
        vsizer.Add(cb, flag = wx.TOP, border = 10)

        songDb = self.parent.KaraokeMgr.SongDB
        if not songDb.GotTitles and not songDb.GotArtists:
            # No songs/titles, so can't unify.
            cb.Enable(False)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        b = wx.Button(self.panel, wx.ID_OK, 'Export')
        self.Bind(wx.EVT_BUTTON, self.clickedOK, b)
        hsizer.Add(b, flag = 0)
        b = wx.Button(self.panel, wx.ID_CANCEL, 'Cancel')
        self.Bind(wx.EVT_BUTTON, self.clickedCancel, b)
        hsizer.Add(b, flag = wx.LEFT, border = 10)
        vsizer.Add(hsizer, flag = wx.ALIGN_CENTER | wx.TOP | wx.LEFT | wx.RIGHT, border = 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(vsizer, flag = wx.EXPAND | wx.ALL, border = 10,
                   proportion = 1)

        self.panel.SetSizerAndFit(hsizer)
        self.Fit()

    def clickedOK(self, event):
        oneLine = self.sameSongOneLine.IsChecked()
        self.Show(False)

        dlg = wx.FileDialog(self, 'Export file',
                            wildcard = 'Text Files (*.txt)|*.txt|All files|*',
                            style = wx.SAVE | wx.OVERWRITE_PROMPT)
        result = dlg.ShowModal()
        if result != wx.ID_OK:
            dlg.Destroy()
            self.Destroy()
            return

        filename = dlg.GetPath()
        dlg.Destroy()

        file = codecs.open(filename, 'w', 'utf-8')

        songDb = self.parent.KaraokeMgr.SongDB
        if oneLine:
            songDb.SelectSort('title')
        else:
            songDb.SelectSort('filename')

        for song in songDb.SongList:
            if oneLine:
                file.write(song.getDisplayFilenames())
            else:
                file.write(song.DisplayFilename)
            if songDb.GotTitles:
                file.write('\t%s' % song.Title)
            if songDb.GotArtists:
                file.write('\t%s' % song.Artist)
            file.write('\n')

        self.Destroy()

    def clickedCancel(self, event):
        self.Show(False)
        self.Destroy()

class EditTitlesWindow(wx.Frame):

    """ The dialog that allows the user to edit artists and titles
    on-the-fly. """

    def __init__(self, parent, KaraokeMgr, songs):
        wx.Frame.__init__(self, parent, -1, 'Edit artists / titles',
                          style = wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.parent = parent
        self.KaraokeMgr = KaraokeMgr
        self.songs = songs

        # Look for a common title and/or artist.
        title = self.songs[0].Title
        artist = self.songs[0].Artist
        for song in self.songs:
            if title != song.Title:
                title = None
            if artist != song.Artist:
                artist = None
        self.commonTitle = title
        self.commonArtist = artist

        self.__layoutWindow()

        pos = parent.GetPosition()
        parentSize = parent.GetSize()
        thisSize = self.GetSize()
        pos[0] += (parentSize[0] / 2) - (thisSize[0] / 2)
        pos[1] += (parentSize[1] / 2) - (thisSize[1] / 2)
        self.SetPosition(pos)

        self.Show()

    def __layoutWindow(self):
        self.panel = wx.Panel(self)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        text = wx.StaticText(self.panel, -1,
                             'This will rewrite the titles.txt file(s) to reflect the changes to title\n'
                             'and/or artist that you indicate.')
        vsizer.Add(text, flag = wx.ALIGN_CENTER | wx.BOTTOM, border = 10)

        text = wx.StaticText(self.panel, -1,
                             '%s song(s) selected.' % (len(self.songs)))
        vsizer.Add(text, flag = wx.ALIGN_CENTER | wx.BOTTOM, border = 10)

        gsizer = wx.FlexGridSizer(0, 2, 2, 0)
        gsizer.AddGrowableCol(1, 1)
        label = wx.StaticText(self.panel, -1, 'Title:')
        gsizer.Add(label, flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = 5)

        field = wx.TextCtrl(self.panel, -1)
        if self.commonTitle is None:
            field.SetValue('(Varies)')
            field.Enable(False)
        else:
            field.SetValue(self.commonTitle)
        gsizer.Add(field, flag = wx.EXPAND)
        self.titleField = field

        label = wx.StaticText(self.panel, -1, 'Artist:')
        gsizer.Add(label, flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = 5)

        field = wx.TextCtrl(self.panel, -1)
        if self.commonArtist is None:
            field.SetValue('(Varies)')
            field.Enable(False)
        else:
            field.SetValue(self.commonArtist)
        gsizer.Add(field, flag = wx.EXPAND)
        self.artistField = field

        vsizer.Add(gsizer, flag = wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        b = wx.Button(self.panel, wx.ID_OK, 'OK')
        self.Bind(wx.EVT_BUTTON, self.clickedOK, b)
        hsizer.Add(b, flag = 0)
        if self.commonArtist is None and self.commonTitle is None:
            # Not possible to change anything, so gray out the modify button.
            b.Enable(False)

        b = wx.Button(self.panel, wx.ID_CANCEL, 'Cancel')
        self.Bind(wx.EVT_BUTTON, self.clickedCancel, b)
        hsizer.Add(b, flag = wx.LEFT, border = 10)
        vsizer.Add(hsizer, flag = wx.ALIGN_CENTER | wx.TOP | wx.LEFT | wx.RIGHT, border = 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(vsizer, flag = wx.EXPAND | wx.ALL, border = 10,
                   proportion = 1)

        self.panel.SetSizerAndFit(hsizer)
        self.Fit()

    def clickedOK(self, event):
        title = self.titleField.GetValue()
        artist = self.artistField.GetValue()
        songDb = self.KaraokeMgr.SongDB

        for song in self.songs:
            dirty = False
            if self.commonTitle is not None:
                if song.Title != title:
                    song.Title = title
                    songDb.GotTitles = True
                    dirty = True

            if self.commonArtist is not None:
                if song.Artist != artist:
                    song.Artist = artist
                    songDb.GotArtists = True
                    dirty = True

            if dirty:
                # This song has been changed.  Flag the appropriate
                # titles file for rewrite.
                song.needsRefresh = True
                songDb.chooseTitles(song)
                song.titles.dirty = True
                songDb.databaseDirty = True

        # Refresh the listbox onscreen.
        searchPanel = self.parent.SearchPanel
        listPanel = searchPanel.ListPanel
        for index in range(listPanel.GetItemCount()):
            si = listPanel.GetItemData(index)
            song = searchPanel.SongStructList[si]
            if not getattr(song, 'needsRefresh', False):
                continue

            # Song will no longer need a refresh.
            del song.needsRefresh

            # Update this song in the listbox.
            item = wx.ListItem()
            item.SetId(index)

            item.SetColumn(searchPanel.TitleCol)
            try:
                item.SetText(song.Title)
            except UnicodeError:
                item.SetText(song.Title.encode('UTF-8', 'replace'))
            item.SetData(si)
            searchPanel.ListPanel.SetItem(item)

            item.SetColumn(searchPanel.ArtistCol)
            try:
                item.SetText(song.Artist)
            except UnicodeError:
                item.SetText(song.Artist.encode('UTF-8', 'replace'))
            item.SetData(si)
            searchPanel.ListPanel.SetItem(item)

        self.Destroy()

    def clickedCancel(self, event):
        self.Show(False)
        self.Destroy()

# Generic function for popping up errors
def ErrorPopup (ErrorString):
    wx.MessageBox(ErrorString, "Error", wx.OK | wx.ICON_ERROR)


# Folder View class subclassed from WxPanel, containing a WxTreeCtrl.
# There is no built in file browser with WxPython, so this was
# implemented using just a basic tree control.
class FileTree (wx.Panel):
    def __init__(self, parent, id, KaraokeMgr, x, y):
        wx.Panel.__init__(self, parent, id)
        self.KaraokeMgr = KaraokeMgr

        # Create the tree control
        TreeStyle = wx.TR_NO_LINES|wx.TR_HAS_BUTTONS|wx.SUNKEN_BORDER|wx.TR_MULTIPLE
        self.FileTree = wx.TreeCtrl(self, -1, wx.Point(x, y), style=TreeStyle)
        # Find the correct icons path. If fully installed on Linux this will
        # be sys.prefix/share/pykaraoke/icons. Otherwise look for it in the
        # current directory.
        if (os.path.isfile("icons/folder_open_16.png")):
            iconspath = "icons"
        else:
            iconspath = os.path.join(sys.prefix, "share/pykaraoke/icons")
        self.FolderOpenIcon = wx.Bitmap(os.path.join(iconspath, "folder_open_16.png"))
        self.FolderClosedIcon = wx.Bitmap(os.path.join(iconspath, "folder_close_16.png"))
        self.FileIcon = wx.Bitmap(os.path.join(iconspath, "audio_16.png"))
        self.ImageList = wx.ImageList(16, 16)
        self.FolderOpenIconIndex = self.ImageList.Add(self.FolderOpenIcon)
        self.FolderClosedIconIndex = self.ImageList.Add(self.FolderClosedIcon)
        self.FileIconIndex = self.ImageList.Add(self.FileIcon)
        self.FileTree.AssignImageList(self.ImageList)
        self.CreateTreeRoot()
        wx.EVT_TREE_ITEM_EXPANDING(self, wx.ID_ANY, self.OnFileExpand)
        wx.EVT_TREE_ITEM_COLLAPSING(self, wx.ID_ANY, self.OnFileCollapse)
        wx.EVT_TREE_ITEM_ACTIVATED(self, wx.ID_ANY, self.OnFileSelected)

        # Create the status bar
        self.StatusBar = wx.StatusBar(self, -1)
        self.StatusBar.SetStatusText ("File Browser View")

        # Create a sizer for the tree view and status bar
        self.VertSizer = wx.BoxSizer(wx.VERTICAL)
        self.VertSizer.Add(self.FileTree, 1, wx.EXPAND, 5)
        self.VertSizer.Add(self.StatusBar, 0, wx.EXPAND, 5)
        self.SetSizer(self.VertSizer)
        self.Show(True)

        # Add handlers for right-click in the results box
        wx.EVT_TREE_ITEM_RIGHT_CLICK(self, wx.ID_ANY, self.OnRightClick)

        # Create IDs for popup menu
        self.menuPlayId = wx.NewId()
        self.menuPlaylistAddId = wx.NewId()
        self.menuFileDetailsId = wx.NewId()

        # Set up drag into the playlist
        self.FileTree.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnBeginDrag)

    # Create the top-level filesystem entry. This is just root directory on Linux
    # but on Windows we have to find out the drive letters and show those as
    # multiple roots. There doesn't seem to be a portable way to do this with
    # WxPython, so this had to check the OS and use the Win32 API if necessary.
    def CreateTreeRoot(self):
        # Get a drive list on Windows otherwise start at root
        if env == ENV_WINDOWS:
            try:
                import win32api
                drives = string.split(win32api.GetLogicalDriveStrings(),'\0')[:-1]
            except ImportError:
                # No win32api installed.  Just look for all the likely drive
                # names exhaustively, excluding A and B (which are
                # usually floppy drives and cause an annoying dialog
                # to pop up).
                drives = []
                for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                    drive = '%s:\\' % (letter)
                    if os.path.isdir(drive):
                        drives.append(drive)

            self.TreeRoot = self.FileTree.AddRoot("")
            self.RootFolder = ""
            for drive in drives:
                node = self.FileTree.AppendItem(self.TreeRoot, drive, image=self.FolderClosedIconIndex)
                self.FileTree.SetItemHasChildren(node, True)
        else:
            self.TreeRoot = self.FileTree.AddRoot("/")
            self.RootFolder = "/"
            # Populate the tree control for the root dir
            self.PopulateFolder (self.TreeRoot)
        # Start expanded
        # Windows ? Alternatively traverse everything by hand as we know what's under root
        self.FileTree.Expand(self.TreeRoot)

    # Take a directory or file item in the tree and walk upwards to
    # generate the full path-string
    def GetFullPathForNode(self, tree_node):
        full_path = self.FileTree.GetItemText(tree_node)
        node = self.FileTree.GetItemParent(tree_node)
        while node and node != self.FileTree.GetRootItem():
            parent_text = self.FileTree.GetItemText(node)
            full_path = os.path.join (parent_text, full_path)
            node = self.FileTree.GetItemParent(node)
        # Now add on the relevant root folder if necessary ("/" on Linux,
        # nothing on Windows, the drive letter node is first ("g:\\")
        full_path = os.path.join (self.RootFolder, full_path)
        return full_path

    # Fill up a folder with the files and subfolders it contains
    def PopulateFolder(self, root_node):
        # If was already expanded once, delete all children and rescan.
        # Could just show the current files if this is inefficient.
        self.FileTree.DeleteChildren(root_node)
        # Make a sorted list of directories and one for files
        full_path = self.GetFullPathForNode(root_node)
        filedir_list = os.listdir(full_path)
        dir_list = []
        file_list = []
        for item in filedir_list:
            if os.path.isdir (os.path.join (full_path, item)):
                dir_list.append(item)
            else:
                root, ext = os.path.splitext(item)
                if self.KaraokeMgr.SongDB.IsExtensionValid(ext):
                    file_list.append(item)
        dir_list.sort()
        file_list.sort()

        settings = self.KaraokeMgr.SongDB.Settings

        # Populate the tree control, directories then files
        for item in dir_list:
            if isinstance(item, types.StringType):
                item = item.decode(settings.FilesystemCoding)
            try:
                node = self.FileTree.AppendItem(root_node, item, image=self.FolderClosedIconIndex)
            except UnicodeError:
                node = self.FileTree.AppendItem(root_node, item.encode('UTF-8', 'replace'), image=self.FolderClosedIconIndex)

            self.FileTree.SetItemHasChildren(node, True)
        for item in file_list:
            if isinstance(item, types.StringType):
                item = item.decode(settings.FilesystemCoding)
            try:
                node = self.FileTree.AppendItem(root_node, item, image=self.FileIconIndex)
            except UnicodeError:
                node = self.FileTree.AppendItem(root_node, item.encode('UTF-8', 'replace'), image=self.FileIconIndex)
            self.FileTree.SetItemBold(node)

    def getSelectedSongs(self):
        """ Returns a list of the selected songs. """

        settings = self.KaraokeMgr.SongDB.Settings

        songs = []
        for selected_node in self.FileTree.GetSelections():
            filename = self.FileTree.GetItemText(selected_node)
            fullpath = self.GetFullPathForNode(selected_node)

            song = pykdb.SongStruct(fullpath, settings, filename)
            songs.append(song)

        return songs

    # Handle a folder expand event
    def OnFileExpand(self, event):
        expanded_node = event.GetItem()
        self.PopulateFolder (expanded_node)
        self.FileTree.SetItemImage(expanded_node, self.FolderOpenIconIndex)

    # Handle a folder collapse event
    def OnFileCollapse(self, event):
        collapsed_node = event.GetItem()
        self.FileTree.SetItemImage(collapsed_node, self.FolderClosedIconIndex)

    # Handle a file selected event. Behaviour is different between Windows and
    # Linux - on Linux a folder can be expanded by double-clicking it. On
    # Windows the + box must be clicked to expand.
    def OnFileSelected(self, event):
        selected_node = event.GetItem()
        filename = self.FileTree.GetItemText(selected_node)
        full_path = self.GetFullPathForNode(selected_node)
        if os.path.isdir(full_path):
            if self.FileTree.IsExpanded(selected_node):
                self.FileTree.Collapse(selected_node)
                self.FileTree.SetItemImage(selected_node, self.FolderClosedIconIndex)
            else:
                self.PopulateFolder(selected_node)
                # Windows ?
                self.FileTree.Expand(selected_node)
                self.FileTree.SetItemImage(selected_node, self.FolderOpenIconIndex)
        else:
            root, ext = os.path.splitext(filename)
            if self.KaraokeMgr.SongDB.IsExtensionValid(ext) and os.path.isfile (full_path):
                # Create a SongStruct because that's what karaoke mgr wants
                settings = self.KaraokeMgr.SongDB.Settings
                song = pykdb.SongStruct(full_path, settings, filename)
                self.KaraokeMgr.PlayWithoutPlaylist(song)

    # Handle a right-click on an item (show a popup)
    def OnRightClick(self, event):
        selected_node = event.GetItem()
        self.PopupFilename = self.FileTree.GetItemText(selected_node)
        self.PopupFullPath = self.GetFullPathForNode(selected_node)
        # Only do a popup if it's not a directory (must be a karaoke song then
        # due to the filtering)
        if not os.path.isdir(self.PopupFullPath):
            menu = wx.Menu()
            menu.Append( self.menuPlayId, "Play song" )
            wx.EVT_MENU( menu, self.menuPlayId, self.OnMenuSelection )
            menu.Append( self.menuPlaylistAddId, "Add selected to playlist" )
            wx.EVT_MENU( menu, self.menuPlaylistAddId, self.OnMenuSelection )
            menu.Append( self.menuFileDetailsId, "File Details" )
            wx.EVT_MENU( menu, self.menuFileDetailsId, self.OnMenuSelection )
            self.PopupMenu( menu, event.GetPoint() )

    # Handle the popup menu events
    def OnMenuSelection( self, event ):
        root, ext = os.path.splitext(self.PopupFilename)
        if self.KaraokeMgr.SongDB.IsExtensionValid(ext) and os.path.isfile (self.PopupFullPath):
            # Create a SongStruct because that's what karaoke mgr wants
            settings = self.KaraokeMgr.SongDB.Settings
            song = pykdb.SongStruct(self.PopupFullPath, settings, self.PopupFilename)
            # Now respond to the menu choice
            if event.GetId() == self.menuPlayId:
                self.KaraokeMgr.PlayWithoutPlaylist(song)
            elif event.GetId() == self.menuPlaylistAddId:
                for song in self.getSelectedSongs():
                    self.KaraokeMgr.AddToPlaylist(song, self)
            elif event.GetId() == self.menuFileDetailsId:
                wx.MessageBox("File: " + self.PopupFullPath, "File details", wx.OK)

    # Start drag handler. Code from WxPython Wiki
    def OnBeginDrag(self, event):
        songs = self.getSelectedSongs()

        if songs:
            def DoDragDrop(songs = songs):
                # Convert the songs list to a string. No extra data necessary
                # for drag-drop from here, just the song struct.
                data = SongStructDataObject(songs, None)

                # Also store this data object in the globalDragObject pointer,
                # to work around a wxPython bug.
                global globalDragObject
                globalDragObject = data

                # Create drop source and begin drag-and-drop.
                dropSource = wx.DropSource(self.FileTree)
                dropSource.SetData(data)

                # The docs say the parameter here should be one of
                # wx.DragCopy/DragMove/etc., but in practice it appears that
                # only wx.DragNone works on Windows.
                if env == ENV_WINDOWS:
                    res = dropSource.DoDragDrop(wx.DragNone)
                else:
                    res = dropSource.DoDragDrop(wx.DragCopy)

            # Can't call dropSource.DoDragDrop here..
            wx.CallAfter(DoDragDrop)


# This defines a custom "format" for our local drag-and-drop data
# type: a list of SongStruct objects.
songStructListFormat = wx.CustomDataFormat('SongStructList')

class SongStructDataObject(wx.PyDataObjectSimple):
    """This class is used to encapsulate a list of SongStruct objects,
    moving through the drag-and-drop system.  We use a custom
    DataObject class instead of using PyTextDataObject, so wxPython
    will know that we are specifically dragging SongStruct objects
    only, and won't crash if someone tries to drag an arbitrary text
    string into the playlist window. """

    def __init__(self, songs = None, extra_data = None):
        wx.PyDataObjectSimple.__init__(self)
        self.SetFormat(songStructListFormat)

        # Store a list of songs
        self.songs = songs

        # Store any extra data, which may be used to pass performer info
        # or any other additional info.
        self.extra_data = extra_data

        # Pickle both songs and extra_data
        self.data = cPickle.dumps((self.songs, self.extra_data))

    def GetDataSize(self):
        """Returns number of bytes required to store the data in the
        object.  This must be defined so the C++ implementation can
        reserve space before calling GetDataHere()."""
        return len(self.data)

    def GetDataHere(self):
        """Returns the data in the object, encoded as a string. """
        return self.data

    def SetData(self, data):
        """Accepts new data in the object, represented as a string. """

        # Note that this method doesn't appear to be called by the
        # current version of wxPython.  We work around this by also
        # passing the current drag-and-drop object in the variable
        # globalDragObject.

        # Cast the data object explicitly to a str type, in case the
        # drag-and-drop operation elevated it to a unicode string.
        self.data = str(data)
        self.songs, self.extra_data = cPickle.loads(self.data)

# We store the object currently being dragged here, to work around an
# apparent bug in wxPython that does not call
# DataObject.SetData() for custom data object formats.  Or, maybe
# I'm just misunderstanding some key interface, but documentation is
# sparse.  In any case, this works fine, since we are only interested
# in drag-and-drop within this process anyway.
globalDragObject = None

# Drag-and-drop target for lists. Code from WxPython Wiki
class ListDrop(wx.PyDropTarget):

    def __init__(self, setFn):
        wx.PyDropTarget.__init__(self)
        self.setFn = setFn

        # Create a data object to receive drops (and also,
        # incidentally, to specify the kind of data object we can
        # receive).
        self.data = SongStructDataObject()
        self.SetDataObject(self.data)

    # Called when OnDrop returns True.  We need to get the data and
    # do something with it.
    def OnData(self, x, y, drag_result):
        # copy the data from the drag source to our data object
        songs = None
        if self.GetData():
           songs = self.data.songs
           extra_data = self.data.extra_data

        if songs is None:
            # If GetData() failed, copy the data in by hand, working
            # around that wxPython bug.
            if globalDragObject:
                songs = globalDragObject.songs
                extra_data = globalDragObject.extra_data

        if songs:
            self.setFn(x, y, songs, extra_data, drag_result)

        # what is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return drag_result

class SearchResultsPanel (wx.Panel):
    """Implement the Search Results panel and list box"""

    def __init__(self, parent, mainWindow, id, KaraokeMgr, x, y):
        wx.Panel.__init__(self, parent, id)
        self.KaraokeMgr = KaraokeMgr

        self.parent = parent
        self.mainWindow = mainWindow

        self.SearchText = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        self.SearchButton = wx.Button(self, -1, "Search")
        self.SearchSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SearchSizer.Add(self.SearchText, 1, wx.EXPAND, 5)
        self.SearchSizer.Add(self.SearchButton, 0, wx.EXPAND, 5)

        self.ListPanel = wx.ListCtrl(self, -1, style = wx.LC_REPORT | wx.SUNKEN_BORDER | wx.LC_SORT_ASCENDING)
        self.ListPanel.Show(True)

        # If we have derived the song information display the disc information else use the file name information.
        if self.KaraokeMgr.SongDB.Settings.CdgDeriveSongInformation:
            self.TitleCol = 0
            self.ArtistCol = 1
            self.DiscCol = 2
            self.FilenameCol = None
            self.ListPanel.InsertColumn (self.TitleCol, "Title", width=100)
            self.ListPanel.InsertColumn (self.ArtistCol, "Artist", width=100)
            self.ListPanel.InsertColumn (self.DiscCol, "Disc", width=75)
        else:
            self.FilenameCol = 0
            self.TitleCol = 1
            self.ArtistCol = 2
            self.DiscCol = None
            self.ListPanel.InsertColumn (self.FilenameCol, "Filename", width=100)
            self.ListPanel.InsertColumn (self.TitleCol, "Title", width=100)
            self.ListPanel.InsertColumn (self.ArtistCol, "Artist", width=100)

        wx.EVT_LIST_COL_CLICK(self.ListPanel, wx.ID_ANY, self.OnColumnClicked)

        self.StatusBar = wx.StatusBar(self, -1)
        self.StatusBar.SetStatusText ("No Search Performed")

        self.VertSizer = wx.BoxSizer(wx.VERTICAL)
        self.InterGap = 0
        self.VertSizer.Add(self.SearchSizer, 0, wx.EXPAND, self.InterGap)
        self.VertSizer.Add(self.ListPanel, 1, wx.EXPAND, self.InterGap)
        self.VertSizer.Add(self.StatusBar, 0, wx.EXPAND, self.InterGap)
        self.SetSizer(self.VertSizer)
        self.Show(True)

        wx.EVT_LIST_ITEM_ACTIVATED(self, wx.ID_ANY, self.OnFileSelected)
        wx.EVT_BUTTON(self, wx.ID_ANY, self.OnSearchClicked)
        wx.EVT_TEXT_ENTER(self, wx.ID_ANY, self.OnSearchClicked)

        # Add handlers for right-click in the results box
        self.RightClickedItemIndex = -1
        wx.EVT_LIST_ITEM_RIGHT_CLICK(self.ListPanel, wx.ID_ANY, self.OnRightClick)

        # Resize column width to the same as list width (or longest title, whichever bigger)
        wx.EVT_SIZE(self.ListPanel, self.onResize)
        # Store the width (in pixels not chars) of the longest column entries
        self.MaxFilenameWidth = 0
        self.MaxTitleWidth = 0
        self.MaxArtistWidth = 0

        # Create IDs for popup menu
        self.menuPlayId = wx.NewId()
        self.menuPlaylistAddId = wx.NewId()
        self.menuPlaylistEditTitlesId = wx.NewId()
        self.menuFileDetailsId = wx.NewId()

        # Set up drag and drop
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._startDrag)

    def UpdateListLayout(self):
        """ This updates the list panel layout when the database settings has been changed."""
        self.ListPanel.ClearAll()
        if self.KaraokeMgr.SongDB.Settings.CdgDeriveSongInformation:
            self.FilenameCol = None
            self.TitleCol = 0
            self.ArtistCol = 1
            self.DiscCol = 2
            self.ListPanel.InsertColumn (self.TitleCol, "Title", width=100)
            self.ListPanel.InsertColumn (self.ArtistCol, "Artist", width=100)
            self.ListPanel.InsertColumn (self.DiscCol, "Disc", width=75)
        else:
            self.DiscCol = None
            self.FilenameCol = 0
            self.TitleCol = 1
            self.ArtistCol = 2
            self.ListPanel.InsertColumn (self.FilenameCol, "Filename", width=100)
            self.ListPanel.InsertColumn (self.TitleCol, "Title", width=100)
            self.ListPanel.InsertColumn (self.ArtistCol, "Artist", width=100)

    def OnFileSelected(self, event):
        """ Handles a file selected event (double-click). Will play directly (not add to playlist) if PlayFromSearchList is true, else it will add the file to the playlist."""
        if self.KaraokeMgr.SongDB.Settings.PlayFromSearchList:
            # The SongStruct is stored as data - get it and pass to karaoke mgr
            selected_index = self.ListPanel.GetItemData(event.GetIndex())
            song = self.SongStructList[selected_index]
            self.KaraokeMgr.PlayWithoutPlaylist(song)
        else:
            # Add song to the playlist
            for song in self.getSelectedSongs():
                self.KaraokeMgr.AddToPlaylist(song, self)

    def OnSearchClicked(self, event):
        """ Handle the search button clicked event """
        # Check to see if it will load the entire database
        if self.SearchText.GetValue() == "":
            return
        elif self.SearchText.GetValue() == "*":
            answer = wx.MessageBox("This will load the entire song database into the search results!\nThis may take a long time to complete depending on the number of songs listed in the database.", "Load Database", wx.YES_NO | wx.ICON_QUESTION)
            self.SearchText.SetValue("")
            # Abort if the user does not wish to load the entire database.
            if answer == wx.NO or answer == wx.CANCEL:
                return
        # Empty the previous results and perform a new search
        self.StatusBar.SetStatusText ("Please Wait... Searching")
        songList = self.KaraokeMgr.SongDB.SearchDatabase(
            self.SearchText.GetValue(), wxAppYielder())
        if self.KaraokeMgr.SongDB.GetDatabaseSize() == 0:
            setupString = "You do not have any songs in your database. Would you like to add folders now?"
            answer = wx.MessageBox(setupString, "Setup database now?", wx.YES_NO | wx.ICON_QUESTION)
            if answer == wx.YES:
                # Open up the database setup dialog
                self.DBFrame = DatabaseSetupWindow(self.parent, -1, "Database Setup", self.KaraokeMgr)
                self.StatusBar.SetStatusText ("No Search Performed")
            else:
                self.StatusBar.SetStatusText ("No Songs In Song Database")
        elif len(songList) == 0:
            ErrorPopup("No Matches Found For " + self.SearchText.GetValue())
            self.StatusBar.SetStatusText ("No Matches Found")
        else:
            self.ListPanel.DeleteAllItems()
            self.MaxFilenameWidth = 0
            self.MaxTitleWidth = 0
            self.MaxArtistWidth = 0
            index = 0
            for song in songList:
                # Add the three columns to the table.
                if not self.KaraokeMgr.SongDB.Settings.CdgDeriveSongInformation: # Only add the Filename if we have not derived the song information
                    item = wx.ListItem()
                    item.SetId(index)
                    item.SetColumn(self.FilenameCol)
                    try:
                        item.SetText(song.DisplayFilename)
                    except UnicodeError:
                        item.SetText(song.DisplayFilename.encode('UTF-8', 'replace'))
                    item.SetData(index)
                    self.ListPanel.InsertItem(item)
                item = wx.ListItem()
                item.SetId(index)
                item.SetColumn(self.TitleCol)
                try:
                    item.SetText(song.Title)
                except UnicodeError:
                    item.SetText(song.Title.encode('UTF-8', 'replace'))
                item.SetData(index)
                if not self.KaraokeMgr.SongDB.Settings.CdgDeriveSongInformation: # Need to add the item if we have derived the song information.
                    self.ListPanel.SetItem(item)
                else:
                    self.ListPanel.InsertItem(item)

                item = wx.ListItem()
                item.SetId(index)
                item.SetColumn(self.ArtistCol)
                try:
                    item.SetText(song.Artist)
                except UnicodeError:
                    item.SetText(song.Artist.encode('UTF-8', 'replace'))
                item.SetData(index)
                self.ListPanel.SetItem(item)

                if self.KaraokeMgr.SongDB.Settings.CdgDeriveSongInformation: # Add the disc information if we have derived the song information
                    item = wx.ListItem()
                    item.SetId(index)
                    item.SetColumn(self.DiscCol)
                    try:
                        item.SetText(song.Disc)
                    except UnicodeError:
                        item.SetText(song.Disc.encode('UTF-8', 'replace'))
                    item.SetData(index)
                    self.ListPanel.SetItem(item)

                index = index + 1

                # Adjust the max widths of each column
                if (len(song.DisplayFilename) * self.GetCharWidth()) > self.MaxFilenameWidth:
                    self.MaxFilenameWidth = (len(song.DisplayFilename) * self.GetCharWidth())
                if (len(song.Title) * self.GetCharWidth()) > self.MaxTitleWidth:
                    self.MaxTitleWidth = (len(song.Title) * self.GetCharWidth())
                if (len(song.Artist) * self.GetCharWidth()) > self.MaxArtistWidth:
                    self.MaxArtistWidth = (len(song.Artist) * self.GetCharWidth())

            # Make sure each column is at least wide enough to display the title
            self.MaxFilenameWidth = max ([self.MaxFilenameWidth,
                                         len("Filename") * self.GetCharWidth()])
            self.MaxTitleWidth = max ([self.MaxTitleWidth,
                                       len("Title") * self.GetCharWidth()])
            self.MaxArtistWidth = max ([self.MaxArtistWidth,
                                        len("Artist") * self.GetCharWidth()])

            # Keep a copy of all the SongStructs in a list, accessible via item index
            self.SongStructList = songList
            self.StatusBar.SetStatusText ("%d Songs Found" % index)
            # Set the column width now we've added some titles
            self.doResize()

    # User clicked on a search column header.
    def OnColumnClicked(self, event):
        """The user has clicked on one of the column headers in the
        results list; sort the results by the indicated column. """

        column = event.GetColumn()
        if column == self.FilenameCol:
            # Sort by filename
            self.ListPanel.SortItems(lambda a, b: cmp(self.SongStructList[a].DisplayFilename.lower(), self.SongStructList[b].DisplayFilename.lower()))
        elif column == self.TitleCol:
            # Sort by title
            self.ListPanel.SortItems(lambda a, b: cmp(self.SongStructList[a].Title.lower(), self.SongStructList[b].Title.lower()))
        elif column == self.ArtistCol:
            # Sort by artist
            self.ListPanel.SortItems(lambda a, b: cmp(self.SongStructList[a].Artist.lower(), self.SongStructList[b].Artist.lower()))
        elif column == self.DiscCol:
            # Sort by disc
            self.ListPanel.SortItems(lambda a, b: cmp(self.SongStructList[a].Disc.lower(), self.SongStructList[b].Disc.lower()))

        # Indicate what column is doing the sorting
        if (self.FilenameCol != None) and column == self.FilenameCol:
            filenameItem = wx.ListItem()
            filenameItem.SetText("* Filename")
            self.ListPanel.SetColumn(self.FilenameCol, filenameItem)
        elif (self.FilenameCol != None):
            filenameItem = wx.ListItem()
            filenameItem.SetText("Filename")
            self.ListPanel.SetColumn(self.FilenameCol, filenameItem)
        elif (self.DiscCol != None) and column == self.DiscCol:
            discItem = wx.ListItem()
            discItem.SetText("* Disc")
            self.ListPanel.SetColumn(self.DiscCol, discItem)
        elif (self.DiscCol != None):
            discItem = wx.ListItem()
            discItem.SetText("Disc")
            self.ListPanel.SetColumn(self.DiscCol, discItem)
        titleItem = wx.ListItem()
        if column == self.TitleCol:
            titleItem.SetText("* Title")
        else:
            titleItem.SetText("Title")
        artistItem = wx.ListItem()
        if column == self.ArtistCol:
            artistItem.SetText("* Artist")
        else:
            artistItem.SetText("Artist")
        self.ListPanel.SetColumn(self.TitleCol, titleItem)
        self.ListPanel.SetColumn(self.ArtistCol, artistItem)

    def getSelectedSongs(self):
        """ Returns a list of the selected songs. """
        songs = []
        index = self.ListPanel.GetNextItem(-1, wx.LIST_NEXT_ALL,
                                           wx.LIST_STATE_SELECTED)
        while index != -1:
            si = self.ListPanel.GetItemData(index)
            song = self.SongStructList[si]
            songs.append(song)
            index = self.ListPanel.GetNextItem(index, wx.LIST_NEXT_ALL,
                                               wx.LIST_STATE_SELECTED)
        return songs

    # Handle right-click on a search results item (show the popup menu)
    def OnRightClick(self, event):
        self.RightClickedItemIndex = event.GetIndex()
        # Doesn't bring up a popup if no items are in the list
        if self.ListPanel.GetItemCount() > 0:
            menu = wx.Menu()
            menu.Append( self.menuPlayId, "Play song" )
            wx.EVT_MENU( menu, self.menuPlayId, self.OnMenuSelection )
            menu.Append( self.menuPlaylistAddId, "Add selected to playlist" )
            wx.EVT_MENU( menu, self.menuPlaylistAddId, self.OnMenuSelection )
            menu.Append( self.menuPlaylistEditTitlesId, "Edit selected titles / artists" )
            wx.EVT_MENU( menu, self.menuPlaylistEditTitlesId, self.OnMenuSelection )
            menu.Append( self.menuFileDetailsId, "File Details" )
            wx.EVT_MENU( menu, self.menuFileDetailsId, self.OnMenuSelection )
            self.ListPanel.SetItemState(
                    self.RightClickedItemIndex,
                    wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED,
                    wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED)
            self.ListPanel.PopupMenu( menu, event.GetPoint() )

    # Handle popup menu selection events
    def OnMenuSelection( self, event ):
        song = self.SongStructList[self.ListPanel.GetItemData(self.RightClickedItemIndex)]
        if event.GetId() == self.menuPlayId:
            self.KaraokeMgr.PlayWithoutPlaylist(song)
        elif event.GetId() == self.menuPlaylistAddId:
            for song in self.getSelectedSongs():
                self.KaraokeMgr.AddToPlaylist(song, self)
        elif event.GetId() == self.menuPlaylistEditTitlesId:
            EditTitlesWindow(self.mainWindow, self.KaraokeMgr, self.getSelectedSongs())
        elif event.GetId() == self.menuFileDetailsId:
            detailsString = ''

            if song.Title:
                detailsString += 'Title: ' + song.Title + '\n'
            if song.Artist:
                detailsString += 'Artist: ' + song.Artist + '\n'
            if song.Title or song.Artist:
                detailsString += '\n'

            if song.ZipStoredName:
                detailsString += 'File: ' + song.ZipStoredName + '\nInside ZIP: ' + song.Filepath + '\n'
            else:
                detailsString += 'File: ' + song.Filepath + '\n'

            if song.titles:
                titles = song.titles
                if titles.ZipStoredName:
                    detailsString += '\nTitles file: ' + titles.ZipStoredName + '\nInside ZIP: ' + titles.Filepath + '\n'
                else:
                    detailsString += '\nTitles file: ' + titles.Filepath + '\n'

            # Display string, handle non-unicode filenames that are byte-strings
            try:
                wx.MessageBox(detailsString, song.DisplayFilename, wx.OK)
            except UnicodeDecodeError:
                wx.MessageBox(detailsString.decode('ascii', 'replace'), song.DisplayFilename, wx.OK)

    def onResize(self, event):
        self.doResize(resize_event = True)
        event.Skip()

    # Common handler for SIZE events and our own resize requests
    def doResize(self, resize_event = False):
        # Get the listctrl's width
        listWidth = self.ListPanel.GetClientSize().width
        # We're showing the vertical scrollbar -> allow for scrollbar width
        # NOTE: on GTK, the scrollbar is included in the client size, but on
        # Windows it is not included
        if wx.Platform != '__WXMSW__':
            if self.ListPanel.GetItemCount() > self.ListPanel.GetCountPerPage():
                scrollWidth = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
                listWidth = listWidth - scrollWidth

        # Set up initial sizes when list is built, not when window is resized
        if (resize_event == False):

            # For some reason the last column becomes shorter than expected,
            # so ask for a bit more from artist column than we need.
            self.MaxArtistWidth = self.MaxArtistWidth + self.GetCharWidth()

            # If we haven't filled the space, extend the filename (bias towards this)
            totalWidth = (self.MaxFilenameWidth + self.MaxTitleWidth + self.MaxArtistWidth)
            if (totalWidth <= listWidth):
                 padding = listWidth - totalWidth
                 fileWidth = self.MaxFilenameWidth + padding
                 titleWidth = self.MaxTitleWidth
                 artistWidth = self.MaxArtistWidth

            # If we have too much to fill the list space, then resize so that all columns
            # can be seen on screen.
            else:
                fileWidth = max ([(listWidth / 2), \
                                 (listWidth - self.MaxTitleWidth - self.MaxArtistWidth)])
                fileWidth = min ([fileWidth, self.MaxFilenameWidth])
                titleWidth = max ([(listWidth / 4), \
                                  (listWidth - self.MaxFilenameWidth - self.MaxArtistWidth)])
                titleWidth = min ([titleWidth, self.MaxTitleWidth])
                artistWidth =  max ([(listWidth / 4), \
                                    (listWidth - self.MaxFilenameWidth - self.MaxTitleWidth)])
                artistWidth = min ([artistWidth, self.MaxArtistWidth])
            # The derived information display has different needs than the title.txt
            if not self.KaraokeMgr.SongDB.Settings.CdgDeriveSongInformation:
                self.ListPanel.SetColumnWidth(self.FilenameCol, fileWidth)
                self.ListPanel.SetColumnWidth(self.ArtistCol, artistWidth)
                self.ListPanel.SetColumnWidth(self.TitleCol, titleWidth)
            else:
                self.ListPanel.SetColumnWidth(self.ArtistCol, artistWidth)
                self.ListPanel.SetColumnWidth(self.TitleCol, fileWidth)

        # For resize events (user changed the window size) keep their column width
        # settings, but resize the Artist column to match whatever space is left.
        else:
            if not self.KaraokeMgr.SongDB.Settings.CdgDeriveSongInformation:
                fileWidth = self.ListPanel.GetColumnWidth(self.FilenameCol)
                titleWidth = self.ListPanel.GetColumnWidth(self.TitleCol)
                artistWidth = listWidth - fileWidth - titleWidth
                self.ListPanel.SetColumnWidth(self.ArtistCol, artistWidth)
            else:
                discWidth = self.ListPanel.GetColumnWidth(self.DiscCol)
                width = (listWidth - discWidth) / 2 # With derived information title and artist are of equal importance.
                self.ListPanel.SetColumnWidth(self.TitleCol, width)
                self.ListPanel.SetColumnWidth(self.ArtistCol, width)

    def GetSelections(self, state =  wx.LIST_STATE_SELECTED):
        indices = []
        found = 1
        lastFound = -1
        while found:
            index = self.ListPanel.GetNextItem(lastFound, wx.LIST_NEXT_ALL, state)
            if index == -1:
                break
            else:
                lastFound = index
                indices.append( index )
        return indices

    # Get the song from the requested index in the song struct list
    def GetSongStruct (self, index):
        return self.SongStructList[index]

    # Put together a data object for drag-and-drop _from_ this list
    # Code from WxPython Wiki
    def _startDrag(self, event):
        # Wrap the songs in a DataObject. We don't pass any
        # extra_data, only the song struct is required.
        songs = self.getSelectedSongs()
        data = SongStructDataObject(songs, None)

        # Also store this data object in the globalDragObject pointer,
        # to work around a wxPython bug.
        global globalDragObject
        globalDragObject = data

        # Create drop source and begin drag-and-drop.
        dropSource = wx.DropSource(self.ListPanel)
        dropSource.SetData(data)

        # The docs say the parameter here should be one of
        # wx.DragCopy/DragMove/etc., but in practice it appears that
        # only wx.DragNone works on Windows.
        if env == ENV_WINDOWS:
            res = dropSource.DoDragDrop(wx.DragNone)
        else:
            res = dropSource.DoDragDrop(wx.DragCopy)

        # Let's not remove items from the search results list, even if
        # the drag-and-drop says the user thought he was "moving" it.

        return True


# Class to manage the playlist panel and list box
class Playlist (wx.Panel):
    def __init__(self, parent, id, KaraokeMgr, x, y):
        wx.Panel.__init__(self, parent, id)
        self.KaraokeMgr = KaraokeMgr
        self.parent = parent

        # Create the playlist control
        self.PlaylistId = wx.NewId()
        self.Playlist = wx.ListCtrl(self, self.PlaylistId, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.SUNKEN_BORDER)

        # Create the columns based on the view configuration
        self.CreateColumns()

        # Create the status bar
        self.StatusBar = wx.StatusBar(self, -1)
        self.StatusBar.SetStatusText ("Currently Not Playing A Song")

        # Create a sizer for the tree view and status bar
        self.InterGap = 0
        self.VertSizer = wx.BoxSizer(wx.VERTICAL)
        self.VertSizer.Add(self.Playlist, 1, wx.EXPAND, self.InterGap)
        self.VertSizer.Add(self.StatusBar, 0, wx.EXPAND, self.InterGap)
        self.SetSizer(self.VertSizer)
        self.Show(True)

        # Add handlers for right-click in the listbox
        wx.EVT_LIST_ITEM_ACTIVATED(self, wx.ID_ANY, self.OnFileSelected)
        wx.EVT_LIST_ITEM_RIGHT_CLICK(self.Playlist, wx.ID_ANY, self.OnRightClick)
        self.RightClickedItemIndex = -1

        # Store the width (in pixels not chars) of the longest title
        self.MaxTitleWidth = 0
        self.MaxArtistWidth = 0
        self.MaxFilenameWidth = 0
        self.MaxPerformerWidth = 0

        # Resize column width to the same as list width (or max title width, which larger)
        wx.EVT_SIZE(self.Playlist, self.onResize)

        # Create IDs for popup menu
        self.menuPlayId = wx.NewId()
        self.menuDeleteId = wx.NewId()
        self.menuClearListId = wx.NewId()

        # Store a local list of song_structs associated by index to playlist items.
        # This is a list of tuples of song_struct and performer name.
        # (Cannot store stuff like this associated with an item in a listctrl)
        self.PlaylistSongStructList = []

        # Set up drag and drop
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._startDrag)
        dt = ListDrop(self._insert)
        self.Playlist.SetDropTarget(dt)

    # Create all playlist columns (at startup and if changing display mode)
    def CreateColumns (self):

        # Display the Artist/Titles column if configured to do so
        col_cnt = 0
        if self.KaraokeMgr.SongDB.Settings.DisplayArtistTitleCols:
            self.TitleCol = col_cnt
            col_cnt = col_cnt + 1
            self.ArtistCol = col_cnt
            col_cnt = col_cnt + 1
            self.Playlist.InsertColumn(self.TitleCol, PLAY_COL_TITLE)
            self.Playlist.InsertColumn(self.ArtistCol, PLAY_COL_ARTIST)
        # Otherwise display the filename column instead
        else:
            self.FilenameCol = col_cnt
            col_cnt = col_cnt + 1
            self.Playlist.InsertColumn(self.FilenameCol, PLAY_COL_FILENAME)

        # Display the performer's name column if configured to do so
        if self.KaraokeMgr.SongDB.Settings.UsePerformerName:
            self.PerformerCol = col_cnt
            col_cnt = col_cnt + 1
            self.Playlist.InsertColumn(self.PerformerCol, PLAY_COL_PERFORMER)
        
        # Finished adding columns, show the panel
        self.NumColumns = col_cnt
        self.Playlist.Show(True)

    # Delete all playlist columns, used when changing display mode
    def DeleteColumns (self):

        # Hide the panel while we delete
        self.Playlist.Show(False)

        # Delete all columns
        self.Playlist.DeleteAllColumns()

        # Clear the number of columns
        self.NumColumns = 0

    # Delete and reload all playlist entries, used when changing display mode
    def ReloadData (self):

        # Take a copy of all songs in the list
        song_list = list(self.PlaylistSongStructList)

        # Delete all items
        for index in range (len(song_list)):
             self.DelItem (0)

        # Clear all data
        self.clear()

        # Using our backup copy, reload all the data
        for song in song_list:
            self.AddItem (song[0], song[1])

    # Handle item selected (double-click). Starts the selected track.
    def OnFileSelected(self, event):
        if self.KaraokeMgr.SongDB.Settings.DoubleClickPlayList:
            selected_index = event.GetIndex()
            self.KaraokeMgr.PlaylistStart(selected_index)

    # Handle right-click in the playlist (show popup menu).
    def OnRightClick(self, event):
        self.RightClickedItemIndex = event.GetIndex()
        # Doesn't bring up a popup if no items are in the list
        if self.Playlist.GetItemCount() > 0:
            menu = wx.Menu()
            # Only show play when a song isn't already playing
            # Prevents the accidental playing
            if self.StatusBar.GetStatusText() == "Currently Not Playing A Song":
                menu.Append( self.menuPlayId, "Play song" )
                wx.EVT_MENU( menu, self.menuPlayId, self.OnMenuSelection )
            menu.Append( self.menuDeleteId, "Delete from playlist" )
            wx.EVT_MENU( menu, self.menuDeleteId, self.OnMenuSelection )
            if self.KaraokeMgr.SongDB.Settings.ClearFromPlayList:
                menu.Append( self.menuClearListId, "Clear playlist" )
                wx.EVT_MENU( menu, self.menuClearListId, self.OnMenuSelection )
            self.Playlist.SetItemState(
                    self.RightClickedItemIndex,
                    wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED,
                    wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED)
            self.Playlist.PopupMenu( menu, event.GetPoint() )

    # Handle popup menu selection events.
    def OnMenuSelection( self, event ):
        if event.GetId() == self.menuPlayId:
            self.KaraokeMgr.PlaylistStart(self.RightClickedItemIndex)
        elif event.GetId() == self.menuDeleteId:
            for index in self.GetSelections():
                self.DelItem(index)
        elif self.KaraokeMgr.SongDB.Settings.ClearFromPlayList and (event.GetId() == self.menuClearListId):
            self.clear()

    def play(self):
        """ Start the playlist playing. """
        if self.Playlist.GetItemCount() > 0:
            self.KaraokeMgr.PlaylistStart(self.Playlist.GetFirstSelected())

    def clear(self):
        """ Empty the playlist. """
        self.Playlist.DeleteAllItems()
        self.PlaylistSongStructList = []
        self.MaxFilenameWidth = 0
        self.MaxArtistWidth = 0
        self.MaxPerformerWidth = 0

    def onResize(self, event):
        self.doResize(resize_event = True)
        event.Skip()

    # Common handler for SIZE events and our own resize requests
    def doResize(self, resize_event = False):
        # Get the listctrl's width
        listWidth = self.Playlist.GetClientSize().width
        # We're showing the vertical scrollbar -> allow for scrollbar width
        # NOTE: on GTK, the scrollbar is included in the client size, but on
        # Windows it is not included
        if wx.Platform != '__WXMSW__':
            if self.Playlist.GetItemCount() > self.Playlist.GetCountPerPage():
                scrollWidth = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
                listWidth = listWidth - scrollWidth

        # Set up initial sizes when list is built, not when window is resized
        if (resize_event == False):

            # Initially attempt to get the full required width for each column
            filenameWidth = max (self.MaxFilenameWidth, (len(PLAY_COL_FILENAME) * self.GetCharWidth() + self.GetCharWidth()))
            artistWidth = max (self.MaxArtistWidth, (len(PLAY_COL_ARTIST) * self.GetCharWidth() + self.GetCharWidth()))
            titleWidth = max (self.MaxTitleWidth, (len(PLAY_COL_TITLE) * self.GetCharWidth() + self.GetCharWidth()))
            performerWidth = max (self.MaxPerformerWidth, (len(PLAY_COL_PERFORMER) * self.GetCharWidth() + self.GetCharWidth()))
            #print "Max sizes: list=%d, artist=%d, title=%d, filename=%d, performer=%d" % (listWidth, titleWidth, artistWidth, filenameWidth, performerWidth)

            # For some reason the last column becomes shorter than expected,
            # so ask for a bit more from last column than we need.
            if self.KaraokeMgr.SongDB.Settings.UsePerformerName:
                performerWidth = performerWidth + self.GetCharWidth()
            elif self.KaraokeMgr.SongDB.Settings.DisplayArtistTitleCols:
                artistWidth = artistWidth + self.GetCharWidth()
            else:
                filenameWidth = filenameWidth + self.GetCharWidth()

            # Calculate the max width required
            totalWidth = 0
            if self.KaraokeMgr.SongDB.Settings.DisplayArtistTitleCols:
                totalWidth = totalWidth + titleWidth + artistWidth
            else:
                totalWidth = totalWidth + filenameWidth
            if self.KaraokeMgr.SongDB.Settings.UsePerformerName:
                totalWidth = totalWidth + performerWidth

            # If we haven't filled the space, just use as much space as we need, with space at the end
            if (totalWidth <= listWidth):
                pass
                #print "Not filled: list=%d, artist=%d, title=%d, filename=%d, performer=%d" % (listWidth, titleWidth, artistWidth, filenameWidth, performerWidth)
 
            # If we have too much to fill the list space, then resize so that all columns
            # can be seen on screen. Scale each column by the same amount.
            else:
                extraWidth = totalWidth - listWidth
                if self.KaraokeMgr.SongDB.Settings.DisplayArtistTitleCols:
                    titleWidth = (titleWidth * listWidth)/totalWidth
                    artistWidth = (artistWidth * listWidth)/totalWidth
                else:
                    filenameWidth = (filenameWidth * listWidth)/totalWidth
                if self.KaraokeMgr.SongDB.Settings.UsePerformerName:
                    performerWidth = (performerWidth * listWidth)/totalWidth
                #print "Too big: list=%d, artist=%d, title=%d, filename=%d, performer=%d" % (listWidth, titleWidth, artistWidth, filenameWidth, performerWidth)

        # For resize events (user changed the window size) keep all their
        # column settings
        else:
            if self.KaraokeMgr.SongDB.Settings.DisplayArtistTitleCols:
                titleWidth = self.Playlist.GetColumnWidth(self.TitleCol)
                artistWidth = self.Playlist.GetColumnWidth(self.ArtistCol)
            else:
                filenameWidth = self.Playlist.GetColumnWidth(self.FilenameCol)
            if self.KaraokeMgr.SongDB.Settings.UsePerformerName:
                performerWidth = self.Playlist.GetColumnWidth(self.PerformerCol)

        # Have calculated all the desired widths, now set them
        if self.KaraokeMgr.SongDB.Settings.DisplayArtistTitleCols:
            self.Playlist.SetColumnWidth(self.TitleCol, titleWidth)
            self.Playlist.SetColumnWidth(self.ArtistCol, artistWidth)
        else:
            self.Playlist.SetColumnWidth(self.FilenameCol, filenameWidth)
        if self.KaraokeMgr.SongDB.Settings.UsePerformerName:
            self.Playlist.SetColumnWidth(self.PerformerCol, performerWidth)

    # Add item to specific index in playlist
    def AddItemAtIndex ( self, index, song, performer="" ):

        # Insert an empty item
        item = wx.ListItem()
        item.SetId(index)
        self.Playlist.InsertItem(item)

        # If there is no title, set it to the filename
        if len(song.Title) == 0:
            song.Title = song.DisplayFilename

        if self.KaraokeMgr.SongDB.Settings.DisplayArtistTitleCols:
            # Add the title column
            item = wx.ListItem()
            item.SetId(index)
            item.SetColumn(self.TitleCol)
            try:
                item.SetText(song.Title)
            except UnicodeError:
                item.SetText(song.Title.encode('UTF-8', 'replace'))
            item.SetData(index)
            self.Playlist.SetItem(item)

            # Add the artist column
            item = wx.ListItem()
            item.SetId(index)
            item.SetColumn(self.ArtistCol)
            try:
                item.SetText(song.Artist)
            except UnicodeError:
                item.SetText(song.Artist.encode('UTF-8', 'replace'))
            item.SetData(index)
            self.Playlist.SetItem(item)
        else:
            # Add the filename column information
            item = wx.ListItem()
            item.SetId(index)
            item.SetColumn(self.FilenameCol)
            try:
                item.SetText(song.DisplayFilename)
            except UnicodeError:
                item.SetText(song.DisplayFilename.encode('UTF-8', 'replace'))
            item.SetData(index)
            self.Playlist.SetItem(item)

        # Add performer name if enabled
        if self.KaraokeMgr.SongDB.Settings.UsePerformerName:
            # Add the performer column information
            item = wx.ListItem()
            item.SetId(index)
            item.SetColumn(self.PerformerCol)
            try:
                item.SetText(performer)
            except UnicodeError:
                item.SetText(performer.encode('UTF-8', 'replace'))
            item.SetData(index)
            self.Playlist.SetItem(item)

        # Create a tuple containing the song_struct ([0]) and performer name ([1])
        song_tuple = (song, performer)
        self.PlaylistSongStructList.insert(index, song_tuple)

        # Update the max title width for column sizing, in case this is the largest one yet
        resize_needed = False
        if ((len(song.DisplayFilename) * self.GetCharWidth()) > self.MaxFilenameWidth):
            self.MaxFilenameWidth = len(song.DisplayFilename) * self.GetCharWidth() + self.GetCharWidth()
            resize_needed = True
        if ((len(song.Title) * self.GetCharWidth()) > self.MaxTitleWidth):
            self.MaxTitleWidth = len(song.Title) * self.GetCharWidth() + self.GetCharWidth()
            resize_needed = True
        if ((len(song.Artist) * self.GetCharWidth()) > self.MaxArtistWidth):
            self.MaxArtistWidth = len(song.Artist) * self.GetCharWidth() + self.GetCharWidth()
            resize_needed = True
        if ((len(performer) * self.GetCharWidth()) > self.MaxPerformerWidth):
            self.MaxPerformerWidth = len(performer) * self.GetCharWidth() + self.GetCharWidth()
            resize_needed = True

        if resize_needed:
            self.doResize()


    # Add item to end of playlist
    def AddItem( self, song_struct, performer ):
        self.AddItemAtIndex (self.Playlist.GetItemCount(), song_struct, performer)

    # Delete item from playlist
    def DelItem( self, item_index ):
        # Update the max title width for column sizing, in case this was the largest one
        resize_needed = False
        if ((len(self.PlaylistSongStructList[item_index][0].DisplayFilename) * self.GetCharWidth()) == self.MaxFilenameWidth):
            resize_needed = True
        if ((len(self.PlaylistSongStructList[item_index][0].Title) * self.GetCharWidth()) == self.MaxTitleWidth):
            resize_needed = True
        if ((len(self.PlaylistSongStructList[item_index][0].Artist) * self.GetCharWidth()) == self.MaxArtistWidth):
            resize_needed = True
        if ((len(self.PlaylistSongStructList[item_index][1]) * self.GetCharWidth()) == self.MaxPerformerWidth):
            resize_needed = True

        # Delete the item from the listctrl and our local song struct list
        self.Playlist.DeleteItem(item_index)
        self.PlaylistSongStructList.pop(item_index)
        # Find the next largest title if necessary
        if resize_needed:
            self.MaxFilenameWidth = 0
            self.MaxTitleWidth = 0
            self.MaxArtistWidth = 0
            self.MaxPerformerWidth = 0
            for song_tuple in self.PlaylistSongStructList:
                if ((len(song_tuple[0].DisplayFilename) * self.GetCharWidth()) > self.MaxFilenameWidth):
                    self.MaxFilenameWidth = len(song_tuple[0].DisplayFilename) * self.GetCharWidth() + self.GetCharWidth()
                if ((len(song_tuple[0].Title) * self.GetCharWidth()) > self.MaxTitleWidth):
                    self.MaxTitleWidth = len(song_tuple[0].Title) * self.GetCharWidth() + self.GetCharWidth()
                if ((len(song_tuple[0].Artist) * self.GetCharWidth()) > self.MaxArtistWidth):
                    self.MaxArtistWidth = len(song_tuple[0].Artist) * self.GetCharWidth() + self.GetCharWidth()
                if ((len(song_tuple[1]) * self.GetCharWidth()) > self.MaxPerformerWidth):
                    self.MaxPerformerWidth = len(song_tuple[1]) * self.GetCharWidth() + self.GetCharWidth()
            self.doResize()

    # Get number of items in playlist
    def GetItemCount( self ):
        return self.Playlist.GetItemCount()

    # Get the song_struct for an item index
    def GetSongStruct ( self, item_index ):
        return self.PlaylistSongStructList[item_index][0]

    # Set an item as selected
    def SetItemSelected( self, item_index ):
        self.Playlist.SetItemState(
                item_index,
                wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED,
                wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED)

    # Return list of selected items.
    def GetSelections(self, state =  wx.LIST_STATE_SELECTED):
        indices = []
        found = 1
        lastFound = -1
        while found:
            index = self.Playlist.GetNextItem(lastFound, wx.LIST_NEXT_ALL, state)
            if index == -1:
                break
            else:
                lastFound = index
                indices.append( index )
        return indices

    # Put together a data object for drag-and-drop _from_ this list
    # Code from WxPython Wiki
    def _startDrag(self, e):
        # Wrap the song_struct in a DataObject. We make use of the
        # extra_data area to also send the performer name. This is
        # only used for drag-drop within the playlist window where
        # we might have performer info.
        song_struct = self.PlaylistSongStructList[e.GetIndex()][0]
        songs = [song_struct]
        performer = self.PlaylistSongStructList[e.GetIndex()][1]
        data = SongStructDataObject(songs, performer)

        # Also store this data object in the globalDragObject pointer,
        # to work around a wxPython bug.
        global globalDragObject
        globalDragObject = data

        # Create drop source and begin drag-and-drop.
        dropSource = wx.DropSource(self.Playlist)
        dropSource.SetData(data)

        # The docs say the parameter here should be one of
        # wx.DragCopy/DragMove/etc., but in practice it appears that
        # only wx.DragNone works on Windows.
        if env == ENV_WINDOWS:
            res = dropSource.DoDragDrop(wx.DragNone)
        else:
            res = dropSource.DoDragDrop(wx.DragMove)

        # If move, we want to remove the item from this list.
        if res == wx.DragMove:
            # It's possible we are dragging/dropping from this
            # list to this list. In which case, the index we are
            # removing may have changed...

            # Find correct position.
            idx = e.GetIndex()
            # Compare the filename if in filename-only mode
            if (not self.KaraokeMgr.SongDB.Settings.DisplayArtistTitleCols):
                if (self.Playlist.GetItem(idx, self.FilenameCol).GetText() == song_struct.DisplayFilename):
                    self.DelItem(idx)
                elif (self.Playlist.GetItem(idx + 1, self.FilenameCol).GetText() == song_struct.DisplayFilename):
                    self.DelItem(idx + 1)
            # Or compare the title if in title/artist mode
            else:
                if (self.Playlist.GetItem(idx, self.TitleCol).GetText() == song_struct.Title):
                    self.DelItem(idx)
                elif (self.Playlist.GetItem(idx + 1, self.TitleCol).GetText() == song_struct.Title):
                    self.DelItem(idx + 1)

    def _insert(self, x, y, songs, extra_data, drag_result):
        """ Insert songs from drag_index in search results, at given x,y coordinates, used with drag-and-drop. Code from WxPython Wiki """

        # Find insertion point.
        index, flags = self.Playlist.HitTest((x, y))
        if index == wx.NOT_FOUND:
            # Note: should only insert if flags & wx.LIST_HITTEST_NOWHERE
            # but for some reason always get flags = 0 even if out of area...
            index = self.Playlist.GetItemCount()
        else:
            # Get bounding rectangle for the item the user is dropping over.
            rect = self.Playlist.GetItemRect(index)

            # If the user is dropping into the lower half of the rect, we want to insert
            # _after_ this item.
            if y > (rect.y + rect.height/2):
                index = index + 1

        # Add it to the list
        for song in songs:
            # Add the performer information if enabled
            performer = ""
            if self.KaraokeMgr.SongDB.Settings.UsePerformerName:
                # If a new song is being added to the playlist pop up a prompt
                if (drag_result != wx.DragMove):
                    dlg = PerformerPrompt.PerformerPrompt(self)
                    if dlg.ShowModal() == wx.ID_OK:
                        performer = dlg.getPerformer()
                    else:
                        return
                # If this is a drag-drop within the playlist (i.e. rearranging), the
                # performer name will be passed to us.
                elif extra_data:
                    performer = extra_data

            self.AddItemAtIndex(index, song, performer)
            index += 1


class PrintSongListWindow(wx.Frame):
    """ The dialog for printing a song list and selecting print options. """

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, 'Print Song List',
                          style = wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.parent = parent
        self.KaraokeMgr = parent.KaraokeMgr

        self.__layoutWindow()

        pos = parent.GetPosition()
        parentSize = parent.GetSize()
        thisSize = self.GetSize()
        pos[0] += (parentSize[0] / 2) - (thisSize[0] / 2)
        pos[1] += (parentSize[1] / 2) - (thisSize[1] / 2)
        self.SetPosition(pos)

        self.Show()

    def __layoutWindow(self):
        self.panel = wx.Panel(self)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self.panel, -1, 'The song database includes %s songs.' % (len(self.KaraokeMgr.SongDB.FullSongList)))
        vsizer.Add(label, flag = wx.ALIGN_CENTER)

        gsizer = wx.FlexGridSizer(0, 2, 5, 0)
        label = wx.StaticText(self.panel, -1, 'Sort by:')
        gsizer.Add(label, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        choices = ['Title', 'Title (filename not printed)',
                   'Artist', 'Artist (filename not printed)',
                   'Filename']
        c = wx.Choice(self.panel, -1, choices = choices)
        c.SetSelection(0)
        self.sort = c
        gsizer.Add(c, flag = 0)

        label = wx.StaticText(self.panel, -1, 'Pages:')
        gsizer.Add(label, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        choices = ['Odd and even pages', 'Odd pages only', 'Even pages only']
        c = wx.Choice(self.panel, -1, choices = choices)
        c.SetSelection(0)
        self.pages = c
        hsizer.Add(c, flag = 0)
        cb = wx.CheckBox(self.panel, -1, 'Back-to-front')
        self.backToFront = cb
        hsizer.Add(cb, flag = wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border = 10)
        gsizer.Add(hsizer, flag = 0)

        label = wx.StaticText(self.panel, -1, 'Extra margin:')
        gsizer.Add(label, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        choices = ['No', 'Left', 'Right', 'Both']
        c = wx.Choice(self.panel, -1, choices = choices)
        c.SetSelection(0)
        self.extraMargin = c
        hsizer.Add(c, flag = 0)
        gsizer.Add(hsizer, flag = 0)

        label = wx.StaticText(self.panel, -1, 'Font size:')
        gsizer.Add(label, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border = 5)
        choices = ['6', '8', '10', '12']
        c = wx.ComboBox(self.panel, -1, choices = choices)
        if len(self.KaraokeMgr.SongDB.FullSongList) >= 3000:
            # There's a lot of songs here.  Assume the user wants to
            # save a bit of paper, and make the default be for a
            # smaller font.
            c.SetValue('8')
        else:
            c.SetValue('10')

        self.fontSize = c
        gsizer.Add(c, flag = 0)

        vsizer.Add(gsizer, flag = wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border = 10)
        vsizer.Add((0, 0), proportion = 1)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        b = wx.Button(self.panel, -1, 'Page Setup')
        self.Bind(wx.EVT_BUTTON, self.clickedPageSetup, b)
        hsizer.Add(b, flag = 0)

        b = wx.Button(self.panel, -1, 'Preview')
        self.Bind(wx.EVT_BUTTON, self.clickedPreview, b)
        hsizer.Add(b, flag = wx.LEFT, border = 10)

        b = wx.Button(self.panel, wx.ID_OK, 'Print')
        self.Bind(wx.EVT_BUTTON, self.clickedOK, b)
        hsizer.Add(b, flag = wx.LEFT, border = 10)

        b = wx.Button(self.panel, wx.ID_CANCEL, 'Cancel')
        self.Bind(wx.EVT_BUTTON, self.clickedCancel, b)
        hsizer.Add(b, flag = wx.LEFT, border = 10)
        vsizer.Add(hsizer, flag = wx.ALIGN_CENTER | wx.TOP, border = 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(vsizer, flag = wx.EXPAND | wx.ALL, border = 10,
                   proportion = 1)

        self.panel.SetSizerAndFit(hsizer)
        self.Fit()

    def __selectSort(self):
        sortKey = [('title', 3), ('title', 2),
                   ('artist', 3), ('artist', 2),
                   ('filename', 2)]
        sort, numColumns = sortKey[self.sort.GetSelection()]

        songDb = self.KaraokeMgr.SongDB
        songDb.SelectSort(sort)
        title = 'Songs by %s' % (sort.title())

        return title, numColumns

    def __makePrintout(self, title, numColumns, now):
        # bit 0x1 means print odd pages, bit 0x2 means print even pages.
        choices = [0x3, 0x1, 0x2]
        pages = choices[self.pages.GetSelection()]

        backToFront = self.backToFront.IsChecked()

        # bit 0x1 means margin on the left, bit 0x2 means margin on
        # the right.
        choices = [0x0, 0x1, 0x2, 0x3]
        marginBits = choices[self.extraMargin.GetSelection()]
        ((mleft, mtop), (mright, mbottom)) = self.parent.margins
        if marginBits & 0x1:
            mleft += 12.5
        if marginBits & 0x2:
            mright += 12.5
        margins = (wx.Point(mleft, mtop), wx.Point(mright, mbottom))

        try:
            fontSize = float(self.fontSize.GetValue())
        except:
            fontSize = 4

        printout = SongListPrintout(
            self.KaraokeMgr.SongDB, title, numColumns, now,
            marginBits, margins, pages, backToFront, fontSize)

        return printout

    def clickedPageSetup(self, event):
        data = wx.PageSetupDialogData()
        data.EnablePrinter(False)
        data.SetPrintData(self.parent.pdata)

        data.SetDefaultMinMargins(True)
        data.SetMarginTopLeft(self.parent.margins[0])
        data.SetMarginBottomRight(self.parent.margins[1])

        dlg = wx.PageSetupDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetPageSetupData()
            self.parent.pdata = wx.PrintData(data.GetPrintData()) # force a copy
            self.parent.pdata.SetPaperId(data.GetPaperId())
            self.parent.margins = (data.GetMarginTopLeft(),
                                   data.GetMarginBottomRight())
        dlg.Destroy()

    def clickedPreview(self, event):
        title, numColumns = self.__selectSort()
        now = time.time()
        printout1 = self.__makePrintout(title, numColumns, now)
        printout2 = self.__makePrintout(title, numColumns, now)

        data = wx.PrintDialogData(self.parent.pdata)
        preview = wx.PrintPreview(printout1, printout2, data)

        if not preview.Ok():
            wx.MessageBox("Unable to create PrintPreview!", "Error")
        else:
            # create the preview frame such that it overlays the app frame
            frame = wx.PreviewFrame(preview, self, "Print Preview",
                                    pos = self.parent.GetPosition(),
                                    size = self.parent.GetSize())
            frame.Initialize()
            frame.Show()

    def clickedOK(self, event):
        self.Show(False)
        title, numColumns = self.__selectSort()
        now = time.time()
        printout = self.__makePrintout(title, numColumns, now)

        data = wx.PrintDialogData(self.parent.pdata)
        printer = wx.Printer(data)
        useSetupDialog = True
        if not printer.Print(self, printout, useSetupDialog) \
           and printer.GetLastError() == wx.PRINTER_ERROR:
            wx.MessageBox(
                "There was a problem printing.\n"
                "Perhaps your current printer is not set correctly?",
                "Printing Error", wx.OK)
            self.Show(True)
        else:
            data = printer.GetPrintDialogData()
            data = wx.PrintData(data.GetPrintData()) # force a copy
            self.parent.pdata = data
            self.Destroy()
        printout.Destroy()

    def clickedCancel(self, event):
        self.Show(False)
        self.Destroy()

class SongListPrintout(wx.Printout):
    """This class is used to manage the printout of the song list.
    Much of it was borrowed from the example given in the book
    "wxPython In Action" by Rappin and Dunn. """

    def __init__(self, songDb, title, numColumns, now, marginBits,
                 margins, pages, backToFront, fontSize):
        wx.Printout.__init__(self, title)
        self.songDb = songDb
        self.numColumns = numColumns
        self.marginBits = marginBits
        self.margins = margins
        self.pages = pages
        self.backToFront = backToFront
        self.requestedFontSize = fontSize

        self.printDate = time.strftime('Printed %b %d, %Y', time.localtime(now))

    def HasPage(self, page):
        return page <= self.numPages

    def GetPageInfo(self):
        return (1, self.numPages, 1, self.numPages)


    def CalculateScale(self, dc):
        # Scale the DC such that the printout is roughly the same as
        # the screen scaling.
        ppiPrinterX, ppiPrinterY = self.GetPPIPrinter()
        ppiScreenX, ppiScreenY = self.GetPPIScreen()
        logScale = float(ppiPrinterX) / float(ppiScreenX)

        if env == ENV_POSIX:
            # For some reason on Linux this scale seems to come out a
            # little bit wrong.  Experimentally, it seems it really
            # wants to be 1.0, but it always comes out 72/86 instead.
            # Check for this special case.
            if ppiPrinterX == 72 and ppiScreenX == 86:
                logScale = 1

        # Now adjust if the real page size is reduced (such as when
        # drawing on a scaled wx.MemoryDC in the Print Preview.)  If
        # page width == DC width then nothing changes, otherwise we
        # scale down for the DC.
        pw, ph = self.GetPageSizePixels()
        dw, dh = dc.GetSize()

        # Rather than using dc.SetUserScale(), which seems to have
        # issues on Linux platforms (it keeps things at integer
        # values, which means at large scale factors they get all
        # wonky), we'll perform the scaling explicitly.
        self.scale = logScale * float(dw) / float(pw)

        # Find the logical units per millimeter (for calculating the
        # margins)
        self.logUnitsMM = self.scale * float(ppiPrinterX) / (logScale*25.4)


    def CalculateLayout(self, dc):
        self.fontSize = self.requestedFontSize * self.scale
        if self.fontSize < 1:
            self.fontSize = 1

        self.titleFont = wx.Font(self.fontSize * 1.5, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_BOLD)
        self.headerFont = wx.Font(self.fontSize, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.dateFont = wx.Font(self.fontSize, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.NORMAL)

        self.font = wx.Font(self.fontSize, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        dc.SetFont(self.titleFont)
        titleHeight = dc.GetCharHeight()
        
        dc.SetFont(self.font)
        self.lineHeight = dc.GetCharHeight()

        # Determine the position of the margins and the
        # page/line height
        topLeft, bottomRight = self.margins
        dw, dh = dc.GetSize()
        self.x1 = topLeft.x * self.logUnitsMM
        self.y1 = topLeft.y * self.logUnitsMM

        # Give extra clearance for the title.
        self.y1 += titleHeight * 1.5

        # A little extra margin for the header line.
        self.y0 = self.y1
        self.y1 += self.logUnitsMM

        self.x2 = dc.DeviceToLogicalXRel(dw) - bottomRight.x * self.logUnitsMM
        self.y2 = dc.DeviceToLogicalYRel(dh) - bottomRight.y * self.logUnitsMM

        # Give extra clearance for the footer.
        self.y2 -= (self.lineHeight)
        
        assert self.y2 > self.y1

        # Divide the space into columns.
        w = self.x2 - self.x1
        numColumns = min(len(self.songDb.SortKeys), self.numColumns)
        if numColumns == 3:
            self.c1 = self.x1 + int(0.4 * w)
            self.c2 = self.x1 + int(0.8 * w)
        elif numColumns == 2:
            self.c1 = self.x1 + int(0.5 * w)
            self.c2 = self.x2
        elif numColumns == 1:
            self.c1 = self.x2
            self.c2 = self.x2

        # use a 1mm buffer around the inside of the box, and a few
        # pixels between each line
        self.pageHeight = self.y2 - self.y1 - 2*self.logUnitsMM

        self.linesPerPage = int(self.pageHeight / self.lineHeight)
        assert self.linesPerPage > 0

        # Normalize so we don't end up with a little extra whitespace
        # on the bottom
        self.pageHeight = self.linesPerPage * self.lineHeight
        self.y2 = self.y1 + self.pageHeight + 2*self.logUnitsMM

        # The top page is reserved for column headers.
        self.linesPerPage -= 1
        self.y1 += self.lineHeight

    def OnPreparePrinting(self):
        # calculate the number of pages
        dc = self.GetDC()
        self.CalculateScale(dc)
        self.CalculateLayout(dc)

        numPages = (len(self.songDb.SongList) + self.linesPerPage - 1) / self.linesPerPage

        if self.pages == 0x3:
            # Print both odd and even pages.
            self.numPages = numPages

        elif self.pages == 0x1:
            # Print odd pages only.
            self.numPages = (numPages + 1) / 2

        elif self.pages == 0x2:
            # Print even pages only.
            self.numPages = numPages / 2

    def OnPrintPage(self, page):
        # Map the virtual page number to the actual page number.a
        if self.backToFront:
            page = self.numPages - page + 1

        if self.pages == 0x3:
            # Print both odd and even pages.
            pass

        elif self.pages == 0x1:
            # Print odd pages only.
            page = (page * 2) - 1

        elif self.pages == 0x2:
            # Print even pages only.
            page = (page * 2)

        dc = self.GetDC()
        self.CalculateScale(dc)
        self.CalculateLayout(dc)

        # draw a page outline at the margin points
        pen = wx.ThePenList.FindOrCreatePen(wx.BLACK, 0, wx.SOLID)
        dc.SetPen(pen)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        r = wx.RectPP((self.x1, self.y0),
                      (self.x2, self.y2))
        dc.DrawRectangleRect(r)

        # Also draw lines around the column headers, and between the
        # columns.
        if self.c1 != self.x2:
            dc.DrawLine(self.c1, self.y0, self.c1, self.y2)
        if self.c2 != self.x2:
            dc.DrawLine(self.c2, self.y0, self.c2, self.y2)
        dc.DrawLine(self.x1, self.y1, self.x2, self.y1)

        # Draw column a for this page
        dc.DestroyClippingRegion()
        dc.SetClippingRect((self.x1, self.y0,
                            self.c1 - self.x1, self.y2 - self.y0))
        x = self.x1 + self.logUnitsMM
        a = self.songDb.SortKeys[0]
        dc.SetFont(self.headerFont)
        dc.DrawText(a.title(), x, self.y0 + self.logUnitsMM)

        dc.SetFont(self.font)
        line = (page - 1) * self.linesPerPage
        y = self.y1 + self.logUnitsMM
        while line < (page * self.linesPerPage):
            song = self.songDb.SongList[line]
            a, b, c = self.songDb.GetSongTuple(song)
            self.__drawClippedText(dc, a, x, y, self.c1 - self.x1)

            y += self.lineHeight
            line += 1
            if line >= len(self.songDb.SongList):
                break

        if self.c1 != self.x2:
            # Draw column b
            dc.DestroyClippingRegion()
            dc.SetClippingRect((self.c1, self.y0,
                                self.c2 - self.c1, self.y2 - self.y0))
            x = self.c1 + self.logUnitsMM
            b = self.songDb.SortKeys[1]
            dc.SetFont(self.headerFont)
            dc.DrawText(b.title(), x, self.y0 + self.logUnitsMM)

            dc.SetFont(self.font)
            line = (page - 1) * self.linesPerPage
            y = self.y1 + self.logUnitsMM
            while line < (page * self.linesPerPage):
                song = self.songDb.SongList[line]
                a, b, c = self.songDb.GetSongTuple(song)
                self.__drawClippedText(dc, b, x, y, self.c2 - self.c1)

                y += self.lineHeight
                line += 1
                if line >= len(self.songDb.SongList):
                    break

        if self.c2 != self.x2:
            # Draw column c
            dc.DestroyClippingRegion()
            dc.SetClippingRect((self.c2, self.y0,
                                self.x2 - self.c2, self.y2 - self.y0))
            x = self.c2 + self.logUnitsMM
            c = self.songDb.SortKeys[2]
            dc.SetFont(self.headerFont)
            dc.DrawText(c.title(), x, self.y0 + self.logUnitsMM)

            dc.SetFont(self.font)
            line = (page - 1) * self.linesPerPage
            y = self.y1 + self.logUnitsMM
            while line < (page * self.linesPerPage):
                song = self.songDb.SongList[line]
                a, b, c = self.songDb.GetSongTuple(song)
                self.__drawClippedText(dc, c, x, y, self.x2 - self.c2)

                y += self.lineHeight
                line += 1
                if line >= len(self.songDb.SongList):
                    break

        dc.DestroyClippingRegion()

        # Draw the page title.
        dc.SetFont(self.titleFont)
        title = 'Karaoke Songs By %s' % (self.songDb.Sort.title())
        w, h = dc.GetTextExtent(title)
        y = self.y0 - h * 1.5 - self.logUnitsMM
        if y >= 0:
            dc.DrawText(title, (self.x1 + self.x2 - w) / 2, y)

        # Draw the page number and print date.
        if self.marginBits == 0x01:
            # Margin on the left: put the page number on the right.
            dc.SetFont(self.font)
            w, h = dc.GetTextExtent(str(page))
            dc.DrawText(str(page), self.x2 - w, self.y2 + self.logUnitsMM)

            dc.SetFont(self.dateFont)
            w, h = dc.GetTextExtent(self.printDate)
            dc.DrawText(self.printDate, self.x1, self.y2 + self.logUnitsMM)

        elif self.marginBits == 0x02:
            # Margin on the right: put the page number on the left.
            dc.SetFont(self.font)
            w, h = dc.GetTextExtent(str(page))
            dc.DrawText(str(page), self.x1, self.y2 + self.logUnitsMM)

            dc.SetFont(self.dateFont)
            w, h = dc.GetTextExtent(self.printDate)
            dc.DrawText(self.printDate, self.x2 - w, self.y2 + self.logUnitsMM)

        else:
            # No margin, or double margin: center the page number.
            dc.SetFont(self.font)
            w, h = dc.GetTextExtent(str(page))
            dc.DrawText(str(page), (self.x1 + self.x2 - w) / 2, self.y2 + self.logUnitsMM)

            dc.SetFont(self.dateFont)
            w, h = dc.GetTextExtent(self.printDate)
            dc.DrawText(self.printDate, self.x2 - w, self.y2 + self.logUnitsMM)

        return True

    def __drawClippedText(self, dc, text, x, y, width):
        """ Draws the text onto the dc, respecting the specified
        clipping width. """

        # On Windows, the clipping region we have already set seems to
        # work fine, and gives superior results.  So just rely on
        # that.
        if env == ENV_WINDOWS:
            dc.DrawText(text, x, y)
            return

        # On Linux, it appears that the clipping region is commonly
        # ignored by the printer driver.  So we have to clip it by
        # hand.  We do this by determining the smallest subset of the
        # text that fits within the width.

        w, h = dc.GetTextExtent(text)
        while w > width:
            text = text[:-1]
            w, h = dc.GetTextExtent(text)

        dc.DrawText(text, x, y)


# Main window
class PyKaraokeWindow (wx.Frame):
    def __init__(self,parent,id,title,KaraokeMgr):
        wx.Frame.__init__(self,parent,wx.ID_ANY, title, size = manager.settings.WindowSize,
                            style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
        self.KaraokeMgr = KaraokeMgr

        # Create the window icon. Find the correct icons path. If
        # fully installed on Linux this will be
        # sys.prefix/share/pykaraoke/icons. Otherwise look for it
        # in the current directory.
        if (os.path.isfile("icons/pykaraoke.xpm")):
            iconspath = "icons"
        else:
            iconspath = os.path.join(sys.prefix, "share/pykaraoke/icons")
        fullpath = os.path.join(iconspath, "pykaraoke.xpm")
        icon1 = wx.Icon(fullpath, wx.BITMAP_TYPE_XPM)
        self.SetIcon(icon1)

        fullpath = os.path.join(iconspath, "microphone.png")
        self.BigIconPath = fullpath

        self.__setupMenu()

        # initialize the print data and set some default values
        self.pdata = wx.PrintData()
        self.pdata.SetPaperId(wx.PAPER_LETTER)
        self.pdata.SetOrientation(wx.PORTRAIT)
        self.margins = (wx.Point(12.5, 20.0), wx.Point(12.5, 12.5))

        self.splitter = wx.SplitterWindow(self)
        self.leftPanel = wx.Panel(self.splitter)
        self.rightPanel = wx.Panel(self.splitter)

        # Create left-hand side buttons at the button
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        choices = ["Search View", "Folder View"]
        self.ViewChoice = wx.Choice(self.leftPanel, -1, choices = choices)
        self.Bind(wx.EVT_CHOICE, self.OnViewChosen, self.ViewChoice)
        hsizer.Add(self.ViewChoice, flag = wx.ALIGN_LEFT)
        hsizer.Add((0, 0), proportion = 1)

        # Determine if we should use the kamikaze button or the play button
        if manager.settings.Kamikaze:
            self.playButton = wx.Button(self.leftPanel, -1, 'Kamikaze')
            self.Bind(wx.EVT_BUTTON, self.OnKamikazeClicked, self.playButton)
        else:
            self.playButton = wx.Button(self.leftPanel, -1, 'Play')
            self.Bind(wx.EVT_BUTTON, self.OnPlayClicked, self.playButton)
        hsizer.Add(self.playButton, flag = wx.EXPAND)

        b = wx.Button(self.leftPanel, -1, 'Add to Playlist')
        self.Bind(wx.EVT_BUTTON, self.OnPlaylistClicked, b)
        hsizer.Add(b, flag = wx.EXPAND)

        # Create the view and playlist panels
        self.TreePanel = FileTree(self.leftPanel, -1, KaraokeMgr, 0, 0)
        self.SearchPanel = SearchResultsPanel(self.leftPanel, self, -1, KaraokeMgr, 0, 0)
        self.LeftSizer = wx.BoxSizer(wx.VERTICAL)
        self.LeftSizer.Add(hsizer, 0, wx.ALL | wx.EXPAND, 5)
        self.LeftSizer.Add(self.TreePanel, 1, wx.ALL | wx.EXPAND, 5)
        self.LeftSizer.Add(self.SearchPanel, 1, wx.ALL | wx.EXPAND, 5)
        self.leftPanel.SetSizer(self.LeftSizer)

        # Create the buttons on the right panel
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(self.rightPanel, -1, 'Playlist')
        hsizer.Add(text, flag = wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border = 5)
        hsizer.Add((0, 0), proportion = 1)

        # Add the play-list play button and determine correct text
        if manager.settings.AutoPlayList:
            self.playlistButton = wx.Button(self.rightPanel, -1, 'Start')
        else:
            self.playlistButton = wx.Button(self.rightPanel, -1, 'Play')
        self.Bind(wx.EVT_BUTTON, self.OnStartPlaylistClicked, self.playlistButton)
        hsizer.Add(self.playlistButton, flag = wx.EXPAND)

        # Control volume of the song 1.0 = 100% volume
        self.VolumeControlID = wx.NewId()
        self.VolumeControl = wx.SpinCtrl(self.rightPanel, self.VolumeControlID, "Volume", size=(50,25))
        self.VolumeControl.SetRange(0, 100)
        self.VolumeControl.SetValue(manager.GetVolume() * 100)
        wx.EVT_SPIN_UP(self.rightPanel, self.VolumeControlID, self.OnVolumeUpClicked)
        wx.EVT_SPIN_DOWN(self.rightPanel, self.VolumeControlID, self.OnVolumeUpClicked)
        wx.EVT_SPINCTRL(self.rightPanel, self.VolumeControlID, self.OnVolumeChanged)
        hsizer.Add(self.VolumeControl)

        # Play list clear
        b = wx.Button(self.rightPanel, -1, 'Clear Playlist')
        self.Bind(wx.EVT_BUTTON, self.OnClearPlaylistClicked, b)
        hsizer.Add(b, flag = wx.EXPAND)

        self.PlaylistPanel = Playlist(self.rightPanel, -1, KaraokeMgr, 0, 0)

        self.RightSizer = wx.BoxSizer(wx.VERTICAL)
        self.RightSizer.Add(hsizer, 0, wx.ALL | wx.EXPAND, 5)
        self.RightSizer.Add(self.PlaylistPanel, 1, wx.ALL | wx.EXPAND, 5)
        self.rightPanel.SetSizer(self.RightSizer)

        if manager.settings.SplitVertically:
            self.splitter.SplitVertically(self.leftPanel, self.rightPanel, 0.5)
        else:
            self.splitter.SplitHorizontally(self.leftPanel, self.rightPanel, 0.5)
        self.splitter.SetMinimumPaneSize(1)

        # Default start in Search View
        self.LeftSizer.Show(self.TreePanel, False)
        self.ViewChoice.SetSelection(0)
        self.SearchPanel.SearchText.SetFocus()

        # Put the top level buttons and main panels in a sizer
        self.MainSizer = wx.BoxSizer(wx.VERTICAL)
        # Add a top-level set of buttons across both panels here if desired
        self.MainSizer.Add(self.splitter, 1, wx.ALL | wx.EXPAND)
        self.SetAutoLayout(True)
        self.SetSizer(self.MainSizer)

        # Attach on exit handler to clean up temporary files
        wx.EVT_CLOSE(self, self.OnClose)

        self.Show(True)

    def __setupMenu(self):
        accelTable = []

        menuBar = wx.MenuBar()

        fileMenu = wx.Menu()

        item = fileMenu.Append(-1, '&Configure')
        self.Bind(wx.EVT_MENU, self.OnConfigClicked, item)
        item = fileMenu.Append(-1, 'Add New Songs to &Database')
        self.Bind(wx.EVT_MENU, self.OnDBClicked, item)
        item = fileMenu.Append(-1, '&Export Song List')
        self.Bind(wx.EVT_MENU, self.OnExport, item)
        item = fileMenu.Append(-1, 'Print Song List')
        self.Bind(wx.EVT_MENU, self.OnPrintSongList, item)

        fileMenu.AppendSeparator()
        item = fileMenu.Append(-1, '&Save database\tCtrl+S')
        accelTable.append((wx.ACCEL_CTRL, ord('S'), item.GetId()))
        self.Bind(wx.EVT_MENU, self.OnSave, item)
        item = fileMenu.Append(-1, 'E&xit')
        self.Bind(wx.EVT_MENU, self.OnClose, item)

        menuBar.Append(fileMenu, '&File')

        helpMenu = wx.Menu()
        item = helpMenu.Append(wx.ID_ABOUT, '&About')
        self.Bind(wx.EVT_MENU, self.OnAbout, item)

        menuBar.Append(helpMenu, '&Help')

        self.SetMenuBar(menuBar)
        self.SetAcceleratorTable(wx.AcceleratorTable(accelTable))

    # Handle drop-down box (Folder View/Search View)
    def OnViewChosen(self, event):
        # Change between Folder View and Search View
        if self.ViewChoice.GetSelection() == 1:
            self.LeftSizer.Show(self.SearchPanel, False)
            self.LeftSizer.Show(self.TreePanel, True)
            self.LeftSizer.Layout()
        else:
            self.LeftSizer.Show(self.TreePanel, False)
            self.LeftSizer.Show(self.SearchPanel, True)
            self.LeftSizer.Layout()
            self.SearchPanel.SearchText.SetFocus()

    def OnVolumeUpClicked(self, event):
        """ Moves the volume up. """
        manager.VolumeUp()
        self.VolumeControl.SetValue(manager.GetVolume() * 100)

    def OnVolumeDownClicked(self, event):
        """ Moves the volume down. """
        manager.VolumeDown()
        self.VolumeControl.SetValue(manager.GetVolume() * 100)

    def OnVolumeChanged(self, event):
        """ Resets the value to what the spin box has set."""
        manager.SetVolume(self.VolumeControl.GetValue() / 100.0)

    def UpdateVolume(self):
        """ Synchronises the volume spinner and the PyGame music instance """
        manager.SetVolume(self.VolumeControl.GetValue() / 100.0)

    def OnKamikazeClicked(self, event):
        """ Handles the Kamikaze button click event. """
        if self.KaraokeMgr.SongDB.GetDatabaseSize() == 0:
            setupString = "You do not have any songs in your database. Would you like to add folders now?"
            answer = wx.MessageBox(setupString, "Setup database now?", wx.YES_NO | wx.ICON_QUESTION)
            if answer == wx.YES:
                # Open up the database setup dialog
                self.Frame = DatabaseSetupWindow(self, -1, "Database Setup", self.KaraokeMgr)
        else:
            songIndex = random.randrange(0, self.KaraokeMgr.SongDB.GetDatabaseSize())
            song = self.KaraokeMgr.SongDB.GetSong(songIndex)
            # Add the performer information or the file name
            if self.KaraokeMgr.SongDB.Settings.UsePerformerName:
                dlg = PerformerPrompt.PerformerPrompt(self)
                if dlg.ShowModal() == wx.ID_OK:
                    song.DisplayFilename = dlg.getPerformer()
                else:
                    return
            self.KaraokeMgr.AddToPlaylist(song, self)

    def OnPlayClicked(self, event):
        """ "Play Song" button clicked. """

        if self.ViewChoice.GetSelection() == 1:
            songs = self.TreePanel.getSelectedSongs()
        else:
            songs = self.SearchPanel.getSelectedSongs()

        if not songs:
            wx.MessageBox("No songs selected.")
            return

        self.UpdateVolume()
        self.KaraokeMgr.PlayWithoutPlaylist(songs[0])

    def OnPlaylistClicked(self, event):
        """ "Add to Playlist" button clicked. """

        if self.ViewChoice.GetSelection() == 1:
            songs = self.TreePanel.getSelectedSongs()
        else:
            songs = self.SearchPanel.getSelectedSongs()

        if not songs:
            wx.MessageBox("No songs selected.")
            return

        for song in songs:
            self.UpdateVolume()
            self.KaraokeMgr.AddToPlaylist(song, self)

    def OnStartPlaylistClicked(self, event):
        """ "Start" button clicked. """
        if (self.playlistButton.GetLabel() == "Play") or (self.playlistButton.GetLabel() == "Start"):
            self.UpdateVolume()
            self.PlaylistPanel.play()
        elif self.playlistButton.GetLabel() == "Stop":
            self.KaraokeMgr.Player.Close()
            self.playlistButton.SetLabel("Play")

    def OnClearPlaylistClicked(self, event):
        """ "Clear playlist" button clicked. """
        self.PlaylistPanel.clear()

    def OnDBClicked(self, event):
        # Open up the database setup dialog
        self.Frame = DatabaseSetupWindow(self, -1, "Database Setup", self.KaraokeMgr)

    def OnConfigClicked(self, event):
        # Open up the settings setup dialog
        self.Frame = ConfigWindow(self, -1, "Configuration", self.KaraokeMgr)

    def OnExport(self, event):
        self.Frame = ExportWindow(self)

    def OnAbout(self, event):
        # Show the appropriate About window (we must use a special About window
        # if using Wx2.6 on which AboutDialogInfo() controls are not available).
        if HasWx26Only() == True:
            self.Frame = Wx26AboutWindow(self)
        else:
            abtnfAbout = wx.AboutDialogInfo()
            abtnfAbout.AddArtist("Kelvin Lawson <kelvinl@users.sf.net>")
            abtnfAbout.AddArtist("Tavmjung Bah")
            abtnfAbout.SetCopyright("(C) 2005-2009 Kelvin Lawson\n(C) 2009 John Schneiderman\n(C) 2006 David Rose\n(C) 2005 William Ferrell")
            abtnfAbout.SetDescription("A karaoke player to play your collection of karaoke songs.")
            abtnfAbout.AddDeveloper("Will Ferrell <willfe@gmail.com>")
            abtnfAbout.AddDeveloper("Andrei Gavrila")
            abtnfAbout.AddDeveloper("Kelvin Lawson <kelvinl@users.sf.net>")
            abtnfAbout.AddDeveloper("Craig Rindy")
            abtnfAbout.AddDeveloper("David Rose <pykar@ddrose.com>")
            abtnfAbout.AddDeveloper("John Schneiderman <JohnMS@member.fsf.org>")
            #abtnfAbout.AddDocWriter("N/A")
            abtnfAbout.SetIcon(wx.Icon(self.BigIconPath, wx.BITMAP_TYPE_PNG, 64, 64))
            LGPLv2_Notice = "PyKaraoke is free software; you can redistribute it and/or modify it under\n the terms of the GNU Lesser General Public License as published by the\n Free Software Foundation; either version 2.1 of the License, or (at your\n option) any later version.\n \n PyKaraoke is distributed in the hope that it will be useful, but WITHOUT\n ANY WARRANTY; without even the implied warranty of MERCHANTABILITY\n or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General\n Public License for more details.\n \n You should have received a copy of the GNU Lesser General Public\n License along with this library; if not, write to the\n Free Software Foundation, Inc.\n 59 Temple Place, Suite 330\n Boston, MA  02111-1307  USA"
            abtnfAbout.SetLicence(LGPLv2_Notice)
            abtnfAbout.SetName("PyKaraoke")
            #abtnfAbout.AddTranslator("N/A")
            abtnfAbout.SetVersion(pykversion.PYKARAOKE_VERSION_STRING)
            abtnfAbout.SetWebSite("http://www.kibosh.org/pykaraoke/")
            wx.AboutBox(abtnfAbout)

    def OnPrintSongList(self, evt):
        PrintSongListWindow(self)

    def OnSave(self, event):
        self.KaraokeMgr.SongDB.SaveDatabase()
        self.KaraokeMgr.SongDB.SaveSettings()

    def OnClose(self, event):
        """ Handle closing pykaraoke (need to delete any temporary files on close) """

        # Save the current window size
        self.KaraokeMgr.SongDB.Settings.WindowSize = (self.GetSize().GetWidth(), self.GetSize().GetHeight())
        self.KaraokeMgr.SongDB.SaveSettings()

        # Hide the window
        self.Show(False)

        if self.KaraokeMgr.SongDB.databaseDirty:
            saveString = "You have made changes, would you like to save your database now?"
            answer = wx.MessageBox(saveString, "Save changes?", wx.YES_NO | wx.ICON_QUESTION)
            if answer == wx.YES:
                self.KaraokeMgr.SongDB.SaveDatabase()
                self.KaraokeMgr.SongDB.SaveSettings()

        self.KaraokeMgr.SongDB.CleanupTempFiles()
        self.Destroy()

        # Normally, destroying the main window is sufficient to exit
        # the application, but sometimes something might have gone
        # wrong and a window or thread might be left hanging.
        # Therefore, close the whole thing down forcefully.
        wx.Exit()

        # We also explicitly close with sys.exit(), since we've forced
        # the MainLoop to keep running.
        sys.exit(0)


# Subclass WxPyEvent to add storage for an extra data pointer
class PyKaraokeEvent(wx.PyEvent):
    def __init__(self, event_id, data):
        wx.PyEvent.__init__(self)
        self.SetEventType(event_id)
        self.data = data


# Main manager class, starts the window and handles the playlist and players
class PyKaraokeManager:
    def __init__(self, gui=True):
        self.SongDB = pykdb.globalSongDB
        self.gui = True
        self.SongDB.LoadSettings(None)

        # Set the global command-line options.
        if manager.options == None:
            parser = self.SetupOptions()
            (manager.options, args) = parser.parse_args()
            manager.ApplyOptions(self.SongDB)

            if (len(args) != 0):
                # If we received filename arguments on the command
                # line, don't start up a gui.
                self.gui = False

                for a in args:
                    # Maybe it's a directory name or a zip name or
                    # something.
                    if os.path.exists(a):
                        self.SongDB.AddFile(a)
                    elif a[-1] == '.' and os.path.exists(a + 'cdg'):
                        self.SongDB.AddFile(a + 'cdg')
                    else:
                        # Maybe it's an embedded file.  Add it anyway.
                        song = self.SongDB.makeSongStruct(a)
                        self.SongDB.addSong(song)

        # Set the default file types that should be displayed
        self.Player = None
        # Used to tell the song finished callback that a song has been
        # requested for playing straight away
        self.DirectPlaySongStruct = None
        # Used to store the currently playing song (if from the playlist)
        self.PlayingIndex = 0

        if self.gui:
            # Set up the WX windows
            if manager.options.validate:
                self.SongDB.LoadDatabase(None)
                manager.ValidateDatabase(self.SongDB)
                sys.exit(0)
            else:
                self.EVT_ERROR_POPUP = wx.NewId()
                self.Frame = PyKaraokeWindow(None, -1, "PyKaraoke " + pykversion.PYKARAOKE_VERSION_STRING, self)
                self.Frame.Connect(-1, -1, self.EVT_ERROR_POPUP, self.ErrorPopupEventHandler)
                self.SongDB.LoadDatabase(self.ErrorPopupCallback)

        else:
            # Without a GUI, just play all the songs in the database
            # (which is to say, all the songs on the command line.)

            if manager.options.validate:
                manager.ValidateDatabase(self.SongDB)
            else:
                for song_struct in self.SongDB.FullSongList:
                    self.StartPlayer(song_struct)
                    manager.WaitForPlayer()
            sys.exit(0)

    def SetupOptions(self):
        """ Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application. """

        return manager.SetupOptions("%prog [options]", self.SongDB)


    # Called when a karaoke file is added to the playlist from the
    # file tree or search results for adding to the playlist.
    # Handles adding to the playlist panel, playing if necessary etc.
    # Takes a SongStruct so it has both title and full path details.
    # Stores the SongStruct in the Playlist control and sets the title.
    def AddToPlaylist(self, song_struct, client_win):
        # Add the performer information if enabled
        performer = ""
        if self.SongDB.Settings.UsePerformerName:
            dlg = PerformerPrompt.PerformerPrompt(client_win)
            if dlg.ShowModal() == wx.ID_OK:
                performer = dlg.getPerformer()
        self.Frame.PlaylistPanel.AddItem(song_struct, performer)

    # Called when a karaoke file is played from the file tree or search
    # results. Does not add to the playlist, just plays directly,
    # cancelling any song currently playing.
    def PlayWithoutPlaylist(self, song_struct):
        if self.Player:
            # If a song is already playing, start closing it. It will be
            # be played directly by the song finished callback.
            self.Player.Close()
            self.DirectPlaySongStruct = song_struct
        else:
            # If no song is already playing, just play this one directly
            self.StartPlayer(song_struct)

    # Called if a song is double-clicked in the playlist.
    # If no song is playing, just start the song at the selected
    # playlist item. If a song is playing, then tell the player to
    # start closing, and set PlayingIndex so that the song finished
    # callback will start playing this one.
    def PlaylistStart(self, song_index):
        if not self.Player:
            song_struct = self.Frame.PlaylistPanel.GetSongStruct(song_index)
            self.StartPlayer(song_struct)
            self.PlayingIndex = song_index
            # Show the song as selected in the playlist
            self.Frame.PlaylistPanel.SetItemSelected(self.PlayingIndex)
        else:
            # Note that this will be -1 if the first item is playing,
            # but this is a valid index for GetNextItem() - it will
            # get the first song in the list.
            self.PlayingIndex = song_index - 1
            self.Player.Close()

    def SongFinishedCallback(self):
        if not self.gui:
            self.SongDB.CleanupTempFiles()
            return
        manager.CloseDisplay()

        # Set the status bar
        self.Frame.PlaylistPanel.StatusBar.SetStatusText ("Currently Not Playing A Song")
        # Only continue to play if auto play is enabled.
        if self.SongDB.Settings.AutoPlayList:
            next_index = self.PlayingIndex + 1
            # If a direct play (not from playlist) was requested, start playing
            # it now that the previous one has closed. Otherwise check the
            # playlist to see if there is another one in there to play
            if self.DirectPlaySongStruct:
                song_struct = self.DirectPlaySongStruct
                self.DirectPlaySongStruct = None
                self.StartPlayer(song_struct)
                # Don't continue with the playlist next
                self.PlayingIndex = -2
                # Play the next song in the list, if there is one (and if the
                # last song wasn't a direct play)
            elif (self.PlayingIndex != -2) and (next_index <= (self.Frame.PlaylistPanel.GetItemCount() - 1)):
                song_struct = self.Frame.PlaylistPanel.GetSongStruct(next_index)
                self.StartPlayer(song_struct)
                self.PlayingIndex = next_index
                # Show the song as selected in the playlist
                self.Frame.PlaylistPanel.SetItemSelected(next_index)
            else:
                self.Player = None
        else:
            self.Player = None
            self.Frame.playlistButton.SetLabel("Play")
        # Delete any temporary files that may have been unzipped
        self.SongDB.CleanupTempFiles()

    # The callback is in the player thread context, so need to post an event
    # for the GUI thread, actually handled by ErrorPopupEventHandler()
    def ErrorPopupCallback(self, ErrorString):
        if not self.gui:
            print ErrorString
            return
        # We use the extra data storage we got by subclassing WxPyEvent to
        # pass data to the event handler (the error string).
        event = PyKaraokeEvent(self.EVT_ERROR_POPUP, ErrorString)
        wx.PostEvent (self.Frame, event)
        if self.Player != None:
            self.Player.shutdown()
            self.Player = None
        self.SongDB.CleanupTempFiles()

    # Handle the error popup event, runs in the GUI thread.
    def ErrorPopupEventHandler(self, event):
        ErrorPopup(event.data)

    # Takes a SongStruct, which contains any info on ZIPs etc
    def StartPlayer(self, song_struct):
        # Create the necessary player instance for this filetype.
        self.Player = song_struct.MakePlayer(
            self.SongDB, self.ErrorPopupCallback, self.SongFinishedCallback)
        if self.Player == None:
            return

        # Start playing
        self.Player.Play()
        if not self.SongDB.Settings.AutoPlayList:
            self.Frame.playlistButton.SetLabel("Stop")

    def handleIdle(self, event):
        manager.Poll()

        if self.Player:
            wx.WakeUpIdle()
            if self.gui:
                # Display the time played and the time remaining
                position = self.Player.GetPos()
                minutes = position / 60000
                seconds = (position % 60000) / 1000
                timeLength = self.Player.GetLength()
                timeLeft = timeLength - (position / 1000)
                if timeLeft <= 0:
                    self.Frame.PlaylistPanel.StatusBar.SetStatusText("[%02d:%02d] %s - %s" % (minutes, seconds, self.Player.Song.Artist, self.Player.Song.Title))
                else:
                    minutesRemaining = timeLeft / 60
                    secondsRemaining = timeLeft % 60
                    self.Frame.PlaylistPanel.StatusBar.SetStatusText("[%02d:%02d/%02d:%02d] %s - %s" % (minutes, seconds, minutesRemaining, secondsRemaining, self.Player.Song.Artist, self.Player.Song.Title))


# Decide whether only WxPython v2.6 is available (and no later version).
def HasWx26Only ():
    # Don't do this for py2exe builds, for which we cannot use wxversion
    if not hasattr(sys, 'frozen'):
        # Check whether only Wx2.6 is installed. We know that a minimum of 2.6 is in use,
        # so check whether any later versions are installed.
        wx26_only = True
        vers = wxversion.getInstalled()
        for ver in vers:
            if ('2.6' not in ver) and ('2.4' not in ver):
                wx26_only = False
    else:
        # Py2exe builds: always assume later than Wx2.6
        wx26_only = False

    return wx26_only


# Subclass wx.App so that we can override the normal Wx MainLoop().
# We only have to do this because since Wx 2.8, the MainLoop()
# appears to be stealing all time from Pygame, and we run Pygame
# and Wx in the same process.
class PyKaraokeApp(wx.App):
    def MainLoop(self):

        # Create an event loop and make it active.
        evtloop = wx.EventLoop()
        wx.EventLoop.SetActive(evtloop)

        # Loop forever.
        while True:

            # This inner loop will process any GUI events
            # until there are no more waiting.
            while evtloop.Pending():
                evtloop.Dispatch()

            # Send idle events to idle handlers.  Sleep here to yield
            # the timeslice, but not for any longer than that, since
            # any time spent in sleep() can steal time away from
            # pygame, especially on slower computers.
            time.sleep(0)
            self.ProcessIdle()

    def OnInit(self):
        # On OSX, it's important to initialize pygame first, *before*
        # we create the main menu, since initializing pygame seems to
        # replace whatever menu we've already created.
        manager.Poll()
        
        Mgr = PyKaraokeManager()
        if Mgr.gui:
            self.Bind(wx.EVT_IDLE, Mgr.handleIdle)
        return True

def main():
    # Display license
    print "PyKaraoke is free software; you can redistribute it and/or\nmodify it under the terms of the GNU Lesser General Public\nLicense as published by the Free Software Foundation; either\nversion 2.1 of the License, or (at your option) any later version.\n\nPyKaraoke is distributed in the hope that it will be useful,\nbut WITHOUT ANY WARRANTY; without even the implied warranty of\nMERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\nGNU Lesser General Public License for more details.\n\nYou should have received a copy of the GNU Lesser General Public\nLicense along with this library; if not, write to the Free Software\nFoundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA\n"

    MyApp = PyKaraokeApp(False)

    # Normally, MainLoop() should only be called once; it will
    # return when it receives WM_QUIT.  However, since pygame
    # posts WM_QUIT when the user closes the pygame window, we
    # need to keep running MainLoop indefinitely.  This means we
    # need to force-quit the application when we really do intend
    # to exit.
    while True:
        MyApp.MainLoop()

if __name__ == "__main__":
    sys.exit(main())
