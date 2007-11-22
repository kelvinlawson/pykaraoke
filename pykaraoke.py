#!/usr/bin/env python

# pykaraoke - Karaoke Player Frontend
#
# Copyright (C) 2005  Kelvin Lawson (kelvinl@users.sourceforge.net)
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

import wxversion
wxversion.select(['2.6', '2.8'])
import os, string, wx, sys
from pykconstants import *
from pykenv import env
import pycdg, pympg, pykar, pykversion, pykdb
import cPickle
from pykmanager import manager

# Size of the main window
MAIN_WINDOW_SIZE = (604,480)

# Size of the Database setup window
DB_WINDOW_SIZE = (450,300)

# Size of the Config window
CONFIG_WINDOW_SIZE = (240,60)

class wxAppYielder(pykdb.AppYielder):
    def Yield(self):
        wx.GetApp().Yield()

# Popup busy window with cancel button
class wxBusyCancelDialog(wx.Frame, pykdb.BusyCancelDialog):
    def __init__(self,parent,title):
        pykdb.BusyCancelDialog.__init__(self)
        
        pos = parent.GetPosition()
        pos[0] += (MAIN_WINDOW_SIZE[0] / 2) - 70
        pos[1] += (MAIN_WINDOW_SIZE[1] / 2) - 25
        wx.Frame.__init__(self,parent,wx.ID_ANY, title, size=(140,50),
                            style=wx.SYSTEM_MENU|wx.CAPTION|wx.FRAME_FLOAT_ON_PARENT,pos=pos)
        
        # Add the buttons
        self.CancelButtonID = wx.NewId()
        self.CancelButton = wx.Button(self, self.CancelButtonID, "Cancel")
        wx.EVT_BUTTON(self, self.CancelButtonID, self.OnCancelClicked)

    # Cancel clicked
    def OnCancelClicked(self, event):
        self.Clicked = True

# Popup settings window for adding song folders, requesting a 
# new folder scan to fill the database etc.
class DatabaseSetupWindow (wx.Frame):
    def __init__(self,parent,id,title,KaraokeMgr):
        pos = parent.GetPosition()
        pos[0] += (MAIN_WINDOW_SIZE[0] / 2) - (DB_WINDOW_SIZE[0] / 2)
        pos[1] += (MAIN_WINDOW_SIZE[1] / 2) - (DB_WINDOW_SIZE[1] / 2)
        wx.Frame.__init__(self,parent,wx.ID_ANY, title, size=DB_WINDOW_SIZE, pos=pos,
                            style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.KaraokeMgr = KaraokeMgr
        
        # Help text
        self._HelpText = wx.StaticText (self, wx.ID_ANY,
                "\nAdd folders to build a searchable database of your karaoke songs\n",
                style = wx.ALIGN_RIGHT) 
        
        # Add the folder list
        self.FolderList = wx.ListBox(self, -1, style=wx.LB_SINGLE)
        for item in self.KaraokeMgr.SongDB.GetFolderList():
            self.FolderList.Append(item)
        
        # Add the buttons
        self.AddFolderButtonID = wx.NewId()
        self.DelFolderButtonID = wx.NewId()
        self.AddFolderButton = wx.Button(self, self.AddFolderButtonID, "Add Folder")
        self.DelFolderButton = wx.Button(self, self.DelFolderButtonID, "Delete Folder")
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
        self.FiletypesText = wx.StaticText (self, wx.ID_ANY, "Include File Types: ")
        self.cdgCheckBox = wx.CheckBox(self, self.FileExtensionID, "CDG")
        self.mpgCheckBox = wx.CheckBox(self, self.FileExtensionID, "MPG")
        self.karCheckBox = wx.CheckBox(self, self.FileExtensionID, "KAR")
        self.midCheckBox = wx.CheckBox(self, self.FileExtensionID, "MID")
        wx.EVT_CHECKBOX (self, self.FileExtensionID, self.OnFileExtChanged)
        if self.KaraokeMgr.SongDB.IsExtensionValid(".cdg"):
            self.cdgCheckBox.SetValue(True)
        else:
            self.cdgCheckBox.SetValue(False)
        if self.KaraokeMgr.SongDB.IsExtensionValid(".mpg"):
            self.mpgCheckBox.SetValue(True)
        else:
            self.mpgCheckBox.SetValue(False)
        if self.KaraokeMgr.SongDB.IsExtensionValid(".kar"):
            self.karCheckBox.SetValue(True)
        else:
            self.karCheckBox.SetValue(False)
        if self.KaraokeMgr.SongDB.IsExtensionValid(".mid"):
            self.midCheckBox.SetValue(True)
        else:
            self.midCheckBox.SetValue(False)
        self.FiletypesSizer = wx.BoxSizer (wx.HORIZONTAL)
        self.FiletypesSizer.Add (self.cdgCheckBox, 0, wx.ALL)
        self.FiletypesSizer.Add (self.mpgCheckBox, 0, wx.ALL)
        self.FiletypesSizer.Add (self.karCheckBox, 0, wx.ALL)
        self.FiletypesSizer.Add (self.midCheckBox, 0, wx.ALL)

        # Create the ZIP file setting checkbox
        self.zipID = wx.NewId()
        self.zipText = wx.StaticText (self, wx.ID_ANY, "Look Inside ZIPs: ")
        self.zipCheckBox = wx.CheckBox(self, self.zipID, "Enabled")
        if self.KaraokeMgr.SongDB.Settings.LookInsideZips == True:
            self.zipCheckBox.SetValue(True)
        else:
            self.zipCheckBox.SetValue(False)
        self.ZipSizer = wx.BoxSizer (wx.HORIZONTAL)
        self.ZipSizer.Add (self.zipCheckBox, 0, wx.ALL)
        wx.EVT_CHECKBOX (self, self.zipID, self.OnZipChanged)

        # Create the titles.txt file setting checkbox
        self.titlesID = wx.NewId()
        self.titlesText = wx.StaticText (self, wx.ID_ANY, "Read titles.txt files: ")
        self.titlesCheckBox = wx.CheckBox(self, self.titlesID, "Enabled")
        if self.KaraokeMgr.SongDB.Settings.ReadTitlesTxt == True:
            self.titlesCheckBox.SetValue(True)
        else:
            self.titlesCheckBox.SetValue(False)
        self.TitlesSizer = wx.BoxSizer (wx.HORIZONTAL)
        self.TitlesSizer.Add (self.titlesCheckBox, 0, wx.ALL)
        wx.EVT_CHECKBOX (self, self.titlesID, self.OnTitlesChanged)

        # Create the scan folders button
        self.ScanText = wx.StaticText (self, wx.ID_ANY, "Rescan all folders: ")
        self.ScanFoldersButtonID = wx.NewId()
        self.ScanFoldersButton = wx.Button(self, self.ScanFoldersButtonID, "Scan Now")
        wx.EVT_BUTTON(self, self.ScanFoldersButtonID, self.OnScanFoldersClicked)

        # Create the save settings button
        self.SaveText = wx.StaticText (self, wx.ID_ANY, "Save settings and song database: ")
        self.SaveSettingsButtonID = wx.NewId()
        self.SaveSettingsButton = wx.Button(self, self.SaveSettingsButtonID, "Save All")
        wx.EVT_BUTTON(self, self.SaveSettingsButtonID, self.OnSaveSettingsClicked)

        # Create the settings and buttons grid
        self.LowerSizer = wx.FlexGridSizer(cols = 2, vgap = 3, hgap = 3)
        self.LowerSizer.Add(self.FiletypesText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.FiletypesSizer, 1, wx.ALL, 3)
        self.LowerSizer.Add(self.zipText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.ZipSizer, 1, wx.ALL, 3)
        self.LowerSizer.Add(self.titlesText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.TitlesSizer, 1, wx.ALL, 3)
        self.LowerSizer.Add(self.ScanText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.ScanFoldersButton, 1, wx.ALL, 3)
        self.LowerSizer.Add(self.SaveText, 0, wx.ALL, 3)
        self.LowerSizer.Add(self.SaveSettingsButton, 1, wx.ALL, 3)
        
        # Create the main sizer
        self.MainSizer = wx.BoxSizer(wx.VERTICAL)
        self.MainSizer.Add(self._HelpText, 0, wx.EXPAND, 3)
        self.MainSizer.Add(self.FolderSizer, 1, wx.EXPAND, 3)
        self.MainSizer.Add(self.LowerSizer, 0, wx.ALL, 3)
        self.SetSizer(self.MainSizer)
        
        # Add a close handler to ask the user if they want to rescan folders
        self.ScanNeeded = False
        self.SaveNeeded = False
        wx.EVT_CLOSE(self, self.ExitHandler)
    
        self.Show()

    # User wants to add a folder
    def OnAddFolderClicked(self, event):
        dirDlg = wx.DirDialog(self)
        retval = dirDlg.ShowModal()
        FolderPath = dirDlg.GetPath()
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
        
    # User wants to rescan all folders
    def OnScanFoldersClicked(self, event):
        cancelled = self.KaraokeMgr.SongDB.BuildSearchDatabase(
            wxAppYielder(), wxBusyCancelDialog(self.KaraokeMgr.Frame, "Searching"))
        if cancelled == False:
            self.ScanNeeded = False
            self.SaveNeeded = True

    # User wants to save all settings
    def OnSaveSettingsClicked(self, event):
        self.KaraokeMgr.SongDB.SaveSettings()
        self.SaveNeeded = False

    # User changed a checkbox, just do them all again
    def OnFileExtChanged(self, event):
        ext_list = []
        if (self.cdgCheckBox.IsChecked()):
            ext_list.append(".cdg")
        if (self.mpgCheckBox.IsChecked()):
            ext_list.append(".mpg")
            ext_list.append(".mpeg")
        if (self.karCheckBox.IsChecked()):
            ext_list.append(".kar")
        if (self.midCheckBox.IsChecked()):
            ext_list.append(".mid")
        self.KaraokeMgr.SongDB.FileExtensionsChange(ext_list)
        self.ScanNeeded = True
        self.SaveNeeded = True

    # User changed the zip checkbox, enable it
    def OnZipChanged(self, event):
        if (self.zipCheckBox.IsChecked()):
            self.KaraokeMgr.SongDB.Settings.LookInsideZips = True
        else:
            self.KaraokeMgr.SongDB.Settings.LookInsideZips = False
        self.ScanNeeded = True
        self.SaveNeeded = True

    # User changed the titles.txt checkbox, enable it
    def OnTitlesChanged(self, event):
        if (self.titlesCheckBox.IsChecked()):
            self.KaraokeMgr.SongDB.Settings.ReadTitlesTxt = True
        else:
            self.KaraokeMgr.SongDB.Settings.ReadTitlesTxt = False
        self.ScanNeeded = True
        self.SaveNeeded = True

    # Popup asking if want to rescan the database after changing settings
    def ExitHandler(self, event):
        if self.ScanNeeded == True:
            changedString = "You have changed settings, would you like to rescan your folders now?"
            answer = wx.MessageBox(changedString, "Rescan folders now?", wx.YES_NO | wx.ICON_QUESTION)
            if answer == wx.YES:
                self.KaraokeMgr.SongDB.BuildSearchDatabase(
                    wxAppYielder(), wxBusyCancelDialog(self.KaraokeMgr.Frame, "Searching"))
                self.SaveNeeded = True
        if self.SaveNeeded == True:
            saveString = "You have made changes, would you like to save your settings and database now?"
            answer = wx.MessageBox(saveString, "Save changes?", wx.YES_NO | wx.ICON_QUESTION)
            if answer == wx.YES:
                self.KaraokeMgr.SongDB.SaveSettings()
        self.Destroy()


# Popup config window for setting full-screen mode etc
class ConfigWindow (wx.Frame):
    def __init__(self,parent,id,title,KaraokeMgr):
        pos = parent.GetPosition()
        pos[0] += (MAIN_WINDOW_SIZE[0] / 2) - (CONFIG_WINDOW_SIZE[0] / 2)
        pos[1] += (MAIN_WINDOW_SIZE[1] / 2) - (CONFIG_WINDOW_SIZE[1] / 2)
        wx.Frame.__init__(self,parent,wx.ID_ANY, title, size=CONFIG_WINDOW_SIZE, pos=pos,
                            style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.KaraokeMgr = KaraokeMgr
        
        # Add the config options
        self.FullScreenID = wx.NewId()
        self.FSCheckBox = wx.CheckBox(self, self.FullScreenID, "Full-screen mode")
        wx.EVT_CHECKBOX (self, self.FullScreenID, self.OnFSChanged)
        if self.KaraokeMgr.SongDB.Settings.FullScreen == True:
            self.FSCheckBox.SetValue(True)
        else:
            self.FSCheckBox.SetValue(False)

        self.CharsetText = wx.StaticText (self, wx.ID_ANY,
                "\nDefault charset:\n", style = wx.ALIGN_LEFT) 
        self.DefaulCharsetID = wx.NewId()
        self.DefaultCharset = wx.TextCtrl(self, self.DefaulCharsetID, self.KaraokeMgr.SongDB.Settings.DefaultCharset, style=wx.TE_PROCESS_ENTER)
#       self.DefaultCharset.SetValue(self, self.toGUI(self.KaraokeMgr.SongDB.Settings.DefaultCharset))


        # Create a sizer for the settings
        self.ConfigSizer = wx.BoxSizer (wx.HORIZONTAL)
        self.ConfigSizer.Add (self.FSCheckBox, 0, wx.ALL)
        self.CharsetSizer = wx.BoxSizer (wx.HORIZONTAL)
        self.CharsetSizer.Add (self.CharsetText, 0, wx.ALL)
        self.CharsetSizer.Add (self.DefaultCharset, 0, wx.ALL)

        # Create the main sizer
        self.MainSizer = wx.BoxSizer(wx.VERTICAL)
        self.MainSizer.Add(self.ConfigSizer, 0, wx.ALL, 3)
        self.MainSizer.Add(self.CharsetSizer, 0, wx.ALL, 3)
        self.SetSizer(self.MainSizer)
        wx.EVT_CLOSE(self, self.ExitHandler)
    
        self.Show()

    # User changed a checkbox, just do them all again
    def OnFSChanged(self, event):
        self.KaraokeMgr.SongDB.Settings.FullScreen = self.FSCheckBox.IsChecked()
        self.KaraokeMgr.SongDB.SaveSettings()
        
    def ExitHandler(self, event):
        self.KaraokeMgr.SongDB.Settings.DefaultCharset = self.DefaultCharset.GetValue()
        self.KaraokeMgr.SongDB.SaveSettings()
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
        TreeStyle = wx.TR_NO_LINES|wx.TR_HAS_BUTTONS|wx.SUNKEN_BORDER
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
        # Populate the tree control, directories then files
        for item in dir_list:
            node = self.FileTree.AppendItem(root_node, item, image=self.FolderClosedIconIndex)   
            self.FileTree.SetItemHasChildren(node, True)
        for item in file_list:
            node = self.FileTree.AppendItem(root_node, item, image=self.FileIconIndex) 
            self.FileTree.SetItemBold(node)

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
                song = pykdb.SongStruct (full_path, filename)
                self.KaraokeMgr.PlayWithoutPlaylist(song)

    # Handle a right-click on an item (show a popup)
    def OnRightClick(self, event):
        selected_node = event.GetItem()
        self.FileTree.SelectItem(selected_node)
        self.PopupFilename = self.FileTree.GetItemText(selected_node)
        self.PopupFullPath = self.GetFullPathForNode(selected_node)
        # Only do a popup if it's not a directory (must be a karaoke song then
        # due to the filtering)
        if not os.path.isdir(self.PopupFullPath):
            menu = wx.Menu()
            menu.Append( self.menuPlayId, "Play song" )
            wx.EVT_MENU( menu, self.menuPlayId, self.OnMenuSelection )
            menu.Append( self.menuPlaylistAddId, "Add to playlist" )
            wx.EVT_MENU( menu, self.menuPlaylistAddId, self.OnMenuSelection )
            menu.Append( self.menuFileDetailsId, "File Details" )
            wx.EVT_MENU( menu, self.menuFileDetailsId, self.OnMenuSelection )
            self.PopupMenu( menu, event.GetPoint() )

    # Handle the popup menu events
    def OnMenuSelection( self, event ):
        root, ext = os.path.splitext(self.PopupFilename)
        if self.KaraokeMgr.SongDB.IsExtensionValid(ext) and os.path.isfile (self.PopupFullPath):
            # Create a SongStruct because that's what karaoke mgr wants
            song = pykdb.SongStruct (self.PopupFullPath, self.PopupFilename)
            # Now respond to the menu choice
            if event.GetId() == self.menuPlayId:
                self.KaraokeMgr.PlayWithoutPlaylist(song)
            elif event.GetId() == self.menuPlaylistAddId:
                self.KaraokeMgr.AddToPlaylist(song)
            elif event.GetId() == self.menuFileDetailsId:
                wx.MessageBox("File: " + self.PopupFullPath, "File details", wx.OK)

    # Start drag handler. Code from WxPython Wiki
    def OnBeginDrag(self, event):
        item = event.GetItem()
        tree = event.GetEventObject()

        if item != tree.GetRootItem(): # prevent dragging root item
            def DoDragDrop():
                txt = tree.GetItemText(item)
                
                # Convert the song_struct to a string.
                filename = self.FileTree.GetItemText(item)
                full_path = self.GetFullPathForNode(item)
                song_struct = pykdb.SongStruct(full_path)
                data = SongStructDataObject(song_struct)

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
# type: a SongStruct object.
songStructFormat = wx.CustomDataFormat('SongStruct')

class SongStructDataObject(wx.PyDataObjectSimple):
    """This class is used to encapsulate a SongStruct object, moving
    through the drag-and-drop system.  We use a custom DataObject
    class instead of using PyTextDataObject, so wxPython will know
    that we are specifically dragging SongStruct objects only, and
    won't crash if someone tries to drag an arbitrary text string into
    the playlist window. """
    
    def __init__(self, songStruct = None):
        wx.PyDataObjectSimple.__init__(self)
        self.SetFormat(songStructFormat)
        self.songStruct = songStruct
        self.data = cPickle.dumps(self.songStruct)

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
        self.songStruct = cPickle.loads(self.data)

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
        songStruct = None
        if self.GetData():
            songStruct = self.data.songStruct

        if not songStruct:
            # If GetData() failed, copy the data in by hand, working
            # around that wxPython bug.
            if globalDragObject:
                songStruct = globalDragObject.songStruct

        if songStruct:
            self.setFn(x, y, songStruct)

        # what is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return drag_result

# Implement the Search Results panel and list box
class SearchResultsPanel (wx.Panel):
    def __init__(self, parent, id, KaraokeMgr, x, y):
        wx.Panel.__init__(self, parent, id)
        self.KaraokeMgr = KaraokeMgr

        self.parent = parent

        self.SearchText = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        self.SearchButton = wx.Button(self, -1, "Search")
        self.SearchSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SearchSizer.Add(self.SearchText, 1, wx.EXPAND, 5)
        self.SearchSizer.Add(self.SearchButton, 0, wx.EXPAND, 5)
        
        self.ListPanel = wx.ListCtrl(self, -1, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.SUNKEN_BORDER)
        self.ListPanel.Show(True)

	# Insert the Filename/Title/Artist columns
        self.FilenameCol = 0 
        self.TitleCol = 1
        self.ArtistCol = 2
 	self.ListPanel.InsertColumn (self.FilenameCol, "Filename", width=100)
        self.ListPanel.InsertColumn (self.TitleCol, "Title", width=100)
        self.ListPanel.InsertColumn (self.ArtistCol, "Artist", width=100)

        wx.EVT_LIST_COL_CLICK(self.ListPanel, wx.ID_ANY, self.OnColumnClicked)

        self.StatusBar = wx.StatusBar(self, -1)
        self.StatusBar.SetStatusText ("No search performed")
        
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
        self.menuFileDetailsId = wx.NewId()
    
        # Set up drag and drop
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._startDrag)
    
    # Handle a file selected event (double-click). Plays directly (not add to playlist)
    def OnFileSelected(self, event):
        # The SongStruct is stored as data - get it and pass to karaoke mgr
        selected_index = self.ListPanel.GetItemData(event.GetIndex())
        song = self.SongStructList[selected_index]
        self.KaraokeMgr.PlayWithoutPlaylist(song)

    # Handle the search button clicked event
    def OnSearchClicked(self, event):
        # Empty the previous results and perform a new search
        self.StatusBar.SetStatusText ("Please wait... Searching")
        songList = self.KaraokeMgr.SongDB.SearchDatabase(
            str(self.SearchText.GetValue()), wxAppYielder())
        if self.KaraokeMgr.SongDB.GetDatabaseSize() == 0:
            setupString = "You do not have any songs in your database. Would you like to add folders now?"
            answer = wx.MessageBox(setupString, "Setup database now?", wx.YES_NO | wx.ICON_QUESTION)
            if answer == wx.YES:
                # Open up the database setup dialog
                self.DBFrame = DatabaseSetupWindow(self.parent, -1, "Database Setup", self.KaraokeMgr)
                self.StatusBar.SetStatusText ("No search performed")
            else:
                self.StatusBar.SetStatusText ("No songs in song database")
        elif len(songList) == 0:
            ErrorPopup("No matches found for " + self.SearchText.GetValue())
            self.StatusBar.SetStatusText ("No matches found")
        else:
            for index in range(self.ListPanel.GetItemCount()):
                self.ListPanel.DeleteItem(0)
            self.MaxFilenameWidth = 0
            self.MaxTitleWidth = 0
            self.MaxArtistWidth = 0
            index = 0
            for song in songList:
                # Add the three columns to the table.
                item = wx.ListItem()
                item.SetId(index)
                item.SetColumn(self.FilenameCol)
                try:
                    item.SetText(song.DisplayFilename)
                except UnicodeDecodeError:
                    # if we can't handle the name, ignore it
                    pass

                item.SetData(index)
                self.ListPanel.InsertItem(item)
                item = wx.ListItem()
                item.SetId(index)
                item.SetColumn(self.TitleCol)
                try:
                    item.SetText(song.Title)
                except UnicodeDecodeError:
                    pass
                item.SetData(index)
                self.ListPanel.SetItem(item)

                item = wx.ListItem()
                item.SetId(index)
                item.SetColumn(self.ArtistCol)
                try:
                    item.SetText(song.Artist)
                except UnicodeDecodeError:
                    pass
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
            self.StatusBar.SetStatusText ("%d songs found" % index)
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


    # Handle right-click on a search results item (show the popup menu)
    def OnRightClick(self, event):
        self.RightClickedItemIndex = event.GetIndex()
        # Doesn't bring up a popup if no items are in the list
        if self.ListPanel.GetItemCount() > 0:
            menu = wx.Menu()
            menu.Append( self.menuPlayId, "Play song" )
            wx.EVT_MENU( menu, self.menuPlayId, self.OnMenuSelection )
            menu.Append( self.menuPlaylistAddId, "Add to playlist" )
            wx.EVT_MENU( menu, self.menuPlaylistAddId, self.OnMenuSelection )
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
            self.KaraokeMgr.AddToPlaylist(song)
        elif event.GetId() == self.menuFileDetailsId:
            if song.ZipStoredName:
                detailsString = "File: " + song.ZipStoredName + "\nInside ZIP: " + song.Filepath
            else:
                detailsString = "File: " + song.Filepath
            wx.MessageBox(detailsString, song.DisplayFilename, wx.OK)

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
            self.ListPanel.SetColumnWidth(self.FilenameCol, fileWidth)
            self.ListPanel.SetColumnWidth(self.TitleCol, titleWidth)
            self.ListPanel.SetColumnWidth(self.ArtistCol, artistWidth)

        # For resize events (user changed the window size) keep their column width
        # settings, but resize the Artist column to match whatever space is left.
        else:
            fileWidth = self.ListPanel.GetColumnWidth(self.FilenameCol)
            titleWidth = self.ListPanel.GetColumnWidth(self.TitleCol)
            artistWidth = listWidth - fileWidth - titleWidth
            self.ListPanel.SetColumnWidth(self.ArtistCol, artistWidth)

    # Not used yet. Return list of selected items.
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
        # Wrap the song_struct in a DataObject.
        idx = self.ListPanel.GetItemData(event.GetIndex())
        song_struct = self.SongStructList[idx]
        data = SongStructDataObject(song_struct)

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
        self.Playlist.InsertColumn (0, "Playlist", width=500)
        self.Playlist.Show(True)

        # Create the status bar
        self.StatusBar = wx.StatusBar(self, -1)
        self.StatusBar.SetStatusText ("Not playing")

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

        # Resize column width to the same as list width (or max title width, which larger)
        wx.EVT_SIZE(self.Playlist, self.onResize)
        # Store the width (in pixels not chars) of the longest title
        self.MaxTitleWidth = 0

        # Create IDs for popup menu
        self.menuPlayId = wx.NewId()
        self.menuDeleteId = wx.NewId()
        self.menuClearListId = wx.NewId()

        # Store a local list of song_structs associated by index to playlist items.
        # (Cannot store stuff like this associated with an item in a listctrl)
        self.PlaylistSongStructList = []

        # Set up drag and drop
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._startDrag)
        dt = ListDrop(self._insert)
        self.Playlist.SetDropTarget(dt)

    # Handle item selected (double-click). Starts the selected track.
    def OnFileSelected(self, event):
        selected_index = event.GetIndex()
        self.KaraokeMgr.PlaylistStart(selected_index)

    # Handle right-click in the playlist (show popup menu).
    def OnRightClick(self, event):
        self.RightClickedItemIndex = event.GetIndex()
        # Doesn't bring up a popup if no items are in the list
        if self.Playlist.GetItemCount() > 0:
            menu = wx.Menu()
            menu.Append( self.menuPlayId, "Play song" )
            wx.EVT_MENU( menu, self.menuPlayId, self.OnMenuSelection )
            menu.Append( self.menuDeleteId, "Delete from playlist" )
            wx.EVT_MENU( menu, self.menuDeleteId, self.OnMenuSelection )
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
        elif event.GetId() == self.menuClearListId:
            for index in range(self.Playlist.GetItemCount()):
                self.DelItem(0)

    def onResize(self, event):
        self.doResize()
        event.Skip()

    # Common handler for SIZE events and our own resize requests
    def doResize(self):
        # Get the listctrl's width
        listWidth = self.Playlist.GetClientSize().width
        # We're showing the vertical scrollbar -> allow for scrollbar width
        # NOTE: on GTK, the scrollbar is included in the client size, but on
        # Windows it is not included
        if wx.Platform != '__WXMSW__':
            if self.Playlist.GetItemCount() > self.Playlist.GetCountPerPage():
                scrollWidth = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
                listWidth = listWidth - scrollWidth

        # Only one column, set its width to list width, or the longest title if larger
        if self.MaxTitleWidth > listWidth:
            width = self.MaxTitleWidth
        else:
            width = listWidth
        self.Playlist.SetColumnWidth(0, width)

    # Add item to specific index in playlist
    def AddItemAtIndex ( self, index, song_struct ):
        self.Playlist.InsertStringItem (index, song_struct.DisplayFilename)
        self.PlaylistSongStructList.insert(index, song_struct)

        # Update the max title width for column sizing, in case this is the largest one yet
        if ((len(song_struct.DisplayFilename) * self.GetCharWidth()) > self.MaxTitleWidth):
            self.MaxTitleWidth = len(song_struct.DisplayFilename) * self.GetCharWidth()
            self.doResize()

    # Add item to end of playlist
    def AddItem( self, song_struct ):
        self.AddItemAtIndex (self.Playlist.GetItemCount(), song_struct)
    
    # Delete item from playlist
    def DelItem( self, item_index ):
        # Update the max title width for column sizing, in case this was the largest one
        if ((len(self.PlaylistSongStructList[item_index].DisplayFilename) * self.GetCharWidth()) == self.MaxTitleWidth):
            resize_needed = True
        else:
            resize_needed = False
        # Delete the item from the listctrl and our local song struct list
        self.Playlist.DeleteItem(item_index)
        self.PlaylistSongStructList.pop(item_index)
        # Find the next largest title if necessary
        if resize_needed:
            self.MaxTitleWidth = 0
            for song_struct in self.PlaylistSongStructList:
                if (len(song_struct.DisplayFilename) * self.GetCharWidth()) > self.MaxTitleWidth:
                    self.MaxTitleWidth = len(song_struct.DisplayFilename) * self.GetCharWidth()
            self.doResize()

    # Get number of items in playlist
    def GetItemCount( self ):
        return self.Playlist.GetItemCount()

    # Get the song_struct for an item index
    def GetSongStruct ( self, item_index ):
        return self.PlaylistSongStructList[item_index]

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
        # Wrap the song_struct in a DataObject.
        song_struct = self.PlaylistSongStructList[e.GetIndex()]
        data = SongStructDataObject(song_struct)

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
            if self.Playlist.GetItem(idx).GetText() == song_struct.DisplayFilename:
                self.DelItem(idx)
            elif self.Playlist.GetItem(idx + 1).GetText() == song_struct.DisplayFilename:
                self.DelItem(idx + 1)


    # Insert song from drag_index in search results, at given x,y coordinates,
    # used with drag-and-drop. Code from WxPython Wiki
    def _insert(self, x, y, song_struct):
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
        self.AddItemAtIndex(index, song_struct)


# Main window
class PyKaraokeWindow (wx.Frame):
    def __init__(self,parent,id,title,KaraokeMgr):
        wx.Frame.__init__(self,parent,wx.ID_ANY, title, size = MAIN_WINDOW_SIZE,
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
        
        # Create left-hand side buttons at the button
        choices = ["Search View", "Folder View"]
        self.ViewChoiceID = wx.NewId()
        self.DBButtonID = wx.NewId()
        self.ConfigButtonID = wx.NewId()
        self.DatabaseButton = wx.Button(self, self.DBButtonID, "Add Songs")
        DBButtonSize = self.DatabaseButton.GetSize()
        self.ConfigButton = wx.Button(self, self.ConfigButtonID, "Config")
        ConfigButtonSize = self.ConfigButton.GetSize()
        self.ViewChoice = wx.Choice(self, self.ViewChoiceID, (0,0), (-1, DBButtonSize[1]), choices)
        self.LeftTopSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.LeftTopSizer.Add(self.ViewChoice, 0, wx.ALIGN_LEFT)
        self.LeftTopSizer.Add((0, 0), 1, 1)
        self.LeftTopSizer.Add(self.ConfigButton, 0, wx.ALIGN_RIGHT)
        self.LeftTopSizer.Add(self.DatabaseButton, 0, wx.ALIGN_RIGHT)
        wx.EVT_CHOICE(self, self.ViewChoiceID, self.OnViewChosen)
        wx.EVT_BUTTON(self, self.ConfigButtonID, self.OnConfigClicked)
        wx.EVT_BUTTON(self, self.DBButtonID, self.OnDBClicked)

        # Create the view and playlist panels
        self.TreePanel = FileTree(self, -1, KaraokeMgr, 0, 0)
        self.SearchPanel = SearchResultsPanel(self, -1, KaraokeMgr, 0, 0)
        self.PlaylistPanel = Playlist(self, -1, KaraokeMgr, 0, 0)
        self.LeftSizer = wx.BoxSizer(wx.VERTICAL)
        self.LeftSizer.Add(self.LeftTopSizer, 0, wx.ALL | wx.EXPAND, 5)
        self.LeftSizer.Add(self.TreePanel, 1, wx.ALL | wx.EXPAND, 5)
        self.LeftSizer.Add(self.SearchPanel, 1, wx.ALL | wx.EXPAND, 5)
        self.RightSizer = wx.BoxSizer(wx.VERTICAL)
        self.RightSizer.Add(self.PlaylistPanel, 1, wx.ALL | wx.EXPAND, 5)
        self.ViewSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ViewSizer.Add(self.LeftSizer, 1, wx.ALL | wx.EXPAND, 5)
        self.ViewSizer.Add(self.RightSizer, 1, wx.ALL | wx.EXPAND, 5)

        # Default start in Search View
        self.LeftSizer.Show(self.TreePanel, False)
        self.ViewChoice.SetSelection(0)
        self.SearchPanel.SearchText.SetFocus()

        # Put the top level buttons and main panels in a sizer
        self.MainSizer = wx.BoxSizer(wx.VERTICAL)
        # Add a top-level set of buttons across both panels here if desired
        #self.MainSizer.Add(self.TopSizer, 0, wx.ALL)
        self.MainSizer.Add(self.ViewSizer, 1, wx.ALL | wx.EXPAND)
        self.SetAutoLayout(True)
        self.SetSizer(self.MainSizer)

        # Attach on exit handler to clean up temporary files
        wx.EVT_CLOSE(self, self.OnClose)

        self.Show(True)

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
    
    # Handle "Add Songs" button clicked
    def OnDBClicked(self, event):
        # Open up the database setup dialog
        self.Frame = DatabaseSetupWindow(self, -1, "Database Setup", self.KaraokeMgr)

    # Handle "Config" button clicked
    def OnConfigClicked(self, event):
        # Open up the database setup dialog
        self.Frame = ConfigWindow(self, -1, "Configuration", self.KaraokeMgr)

    # Handle closing pykaraoke (need to delete any temporary files on close)
    def OnClose(self, event):
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
        
        # Set the global command-line options.
        if manager.options == None:
            parser = self.SetupOptions()
            (manager.options, args) = parser.parse_args()

            if (len(args) != 0):
                # If we received filename arguments on the command
                # line, don't start up a gui.
                self.gui = False
                for a in args:
                    if os.path.exists(a):
                        self.SongDB.AddFile(a)
                    elif a[-1] == '.' and os.path.exists(a + 'cdg'):
                        self.SongDB.AddFile(a + 'cdg')
                    else:
                        print "No such file: %s" % (a)

        # Set the default file types that should be displayed
        self.Player = None
        # Used to tell the song finished callback that a song has been
        # requested for playing straight away
        self.DirectPlaySongStruct = None
        # Used to store the currently playing song (if from the playlist)
        self.PlayingIndex = 0
  
        if self.gui:
            # Set up the WX windows
            self.EVT_SONG_FINISHED = wx.NewId()
            self.EVT_ERROR_POPUP = wx.NewId()
            self.Frame = PyKaraokeWindow(None, -1, "PyKaraoke " + pykversion.PYKARAOKE_VERSION_STRING, self)
            self.Frame.Connect(-1, -1, self.EVT_SONG_FINISHED, self.SongFinishedEventHandler)
            self.Frame.Connect(-1, -1, self.EVT_ERROR_POPUP, self.ErrorPopupEventHandler)

            self.SongDB.LoadSettings(self.ErrorPopupCallback)

        else:
            # Without a GUI, just play all the songs in the database
            # (which is to say, all the songs on the command line.)
            for song_struct in self.SongDB.SongList:
                self.StartPlayer(song_struct)
                manager.WaitForPlayer()

    def SetupOptions(self):
        """ Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application. """

        return manager.SetupOptions(usage = "%prog [options]")


    # Called when a karaoke file is added to the playlist from the 
    # file tree or search results for adding to the playlist. 
    # Handles adding to the playlist panel, playing if necessary etc.
    # Takes a SongStruct so it has both title and full path details.
    # Stores the SongStruct in the Playlist control and sets the title.
    def AddToPlaylist(self, song_struct):
        self.Frame.PlaylistPanel.AddItem(song_struct)
    
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
        
    # The callback is in the player thread context, so need to post an event
    # for the GUI thread, actually handled by SongFinishedEventHandler()
    def SongFinishedCallback(self):
        if not self.gui:
            self.SongDB.CleanupTempFiles()
            return
        manager.CloseDisplay()
        event = PyKaraokeEvent(self.EVT_SONG_FINISHED, None)
        wx.PostEvent (self.Frame, event)
    
    # Handle the song finished event. This is triggered by the callback but
    # runs in the GUI thread, instead of the player thread which the callback
    # runs in.
    def SongFinishedEventHandler(self, event):
        # Set the status bar
        self.Frame.PlaylistPanel.StatusBar.SetStatusText ("Not playing")
        # Find out if the user changed the display size, to use on the next song.
        # Note it's not possible to get the current pygame window position, so
        # the players always start at the top-left (0,0)
        self.DisplaySize = manager.GetDisplaySize()
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
        manager.SetFullScreen (self.SongDB.Settings.FullScreen)

        # Create the necessary player instance for this filetype.
        self.Player = song_struct.MakePlayer(self.ErrorPopupCallback, self.SongFinishedCallback)
        if self.Player == None:
            return
        
        if self.gui:
            # Set the status bar
            self.Frame.PlaylistPanel.StatusBar.SetStatusText ("Playing " + song_struct.DisplayFilename)
        
        # Start playing
        self.Player.Play()

    def handleIdle(self, event):
        manager.Poll()
        if self.Player:
            wx.WakeUpIdle()

def main():
    PyKaraokeApp = wx.PySimpleApp()
    Mgr = PyKaraokeManager()

    if Mgr.gui:
        PyKaraokeApp.Bind(wx.EVT_IDLE, Mgr.handleIdle)

        # Normally, MainLoop() should only be called once; it will
        # return when it receives WM_QUIT.  However, since pygame
        # posts WM_QUIT when the user closes the pygame window, we
        # need to keep running MainLoop indefinitely.  This means we
        # need to force-quit the application when we really do intend
        # to exit.
        while True:
            PyKaraokeApp.MainLoop()

if __name__ == "__main__":
    sys.exit(main())
