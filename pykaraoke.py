#!/usr/bin/python

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
# . Numeric module (numpy.sourceforge.net)


# USAGE INSTRUCTIONS
#
# To start the player, run the following from the command line:
# 		python pykaraoke.py
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
# player modules start their own threads, so the GUI is still
# usable while the songs are playing, allowing the user to
# continue adding to the playlist etc.


from wxPython.wx import *
import os, string, zipfile, pickle
import pycdg, pympg

# SongStruct used as storage only (no methods) to store song details for
# the database. Separate Titles allow us to cut off the pathname, use ID3
# tags (when supported) etc. For ZIP files there is an extra member - for
# the stored filename, which might be different from the title if the
# stored file is in a stored sub-dir, or is an ID tag.
class SongStruct:
	def __init__(self, Filepath, Title, ZipStoredName = None):
		self.Filepath = Filepath	# Full path to file or ZIP file
		self.Title = Title			# Title for display in playlist
		self.ZipStoredName = ZipStoredName # Filename stored in ZIP

# SettingsStruct used as storage only for settings. The instance
# can be pickled to save all user's settings.
class SettingsStruct:
	def __init__(self, FolderList, FileExtensions, LookInsideZips):
		self.FolderList = FolderList			# List of song folders
		self.FileExtensions = FileExtensions	# List of extensions (.cdg etc)
		self.LookInsideZips = LookInsideZips	# Whether to look inside zips


# Song database class with methods for building the database, searching etc
class SongDB:
	def __init__(self, KaraokeMgr):
		# Filepaths and titles are stored in a list of SongStruct instances
		self.SongList = []
	
		# Set the default settings, in case none are stored on disk
		folder_path = []
		file_extensions = [".cdg", ".mpg", ".mpeg"]
		look_inside_zips = True
	
		# Create a SettingsStruct instance for storing settings
		# in case none are stored.
		self.Settings = SettingsStruct (folder_path, file_extensions, look_inside_zips)
		
		# Store the karaoke manager instance
		self.KaraokeMgr = KaraokeMgr
		
		# All temporary files use this prefix
		self.TempFilePrefix = "00Pykar__"

		# Get Wx's idea of the home directory
		self.TempDir = os.path.join(wxGetHomeDir(), ".pykaraoke")
		self.CleanupTempFiles()
		
		# Override the default settings with stored ones if they exist
		# and load any saved database
		self.LoadSettings()

	# Load settings and database if they are stored
	def LoadSettings (self):
		# Load the settings file
		settings_filepath = os.path.join (self.TempDir, "settings.dat")
		if os.path.exists (settings_filepath):
			file = open (settings_filepath, "rb")
			self.Settings = pickle.load (file)
			file.close()
		# Load the database file
		db_filepath = os.path.join (self.TempDir, "songdb.dat")
		if os.path.exists (db_filepath):
			file = open (db_filepath, "rb")
			self.SongList = pickle.load (file)
			file.close()

	# Save settings and database to the home/temp directory
	def SaveSettings (self):
		# Create the temp directory if it doesn't exist already
		if not os.path.exists (self.TempDir):
			os.mkdir(self.TempDir)
		# Save the settings file
		settings_filepath = os.path.join (self.TempDir, "settings.dat")
		file = open (settings_filepath, "wb")
		pickle.dump (self.Settings, file)
		file.close()
		# Save the database file
		db_filepath = os.path.join (self.TempDir, "songdb.dat")
		file = open (db_filepath, "wb")
		pickle.dump (self.SongList, file)
		file.close()
	
	def BuildSearchDatabase(self):
		# Zap the database and build again from scratch
		self.SongList = []
		busyBox = wxBusyCursor()
		for root_path in self.Settings.FolderList:
			self.FolderScan (root_path)

	def FolderScan (self, FolderToScan):
		# Search for karaoke files inside the folder, looking inside ZIPs if
		# configured to do so. Function is recursive for subfolders.
		filedir_list = os.listdir(FolderToScan)
		theApp = wxGetApp()
		searched = 0
		for item in filedir_list:
			searched = searched + 1
			# Allow windows to refresh now and again while scanning
			if ((searched % 15) == 0):
				theApp.Yield()
			full_path = os.path.join(FolderToScan, item)
			# Recurse into subdirectories
			if os.path.isdir(full_path):
				self.FolderScan (full_path)
			# Store file details if it's a file type we're interested in
			else:
				root, ext = os.path.splitext(full_path)
				# Non-ZIP files
				if self.IsExtensionValid(ext):
					self.SongList.append(SongStruct(full_path, item))
				# Look inside ZIPs if configured to do so
				if self.Settings.LookInsideZips and ext.lower() == ".zip":
					try:
						if zipfile.is_zipfile(full_path):
							zip = zipfile.ZipFile(full_path)
							for filename in zip.namelist():
								root, ext = os.path.splitext(filename)
								if self.IsExtensionValid(ext):
									# Python zipfile only supports deflated and stored
									info = zip.getinfo(filename)
									if info.compress_type == zipfile.ZIP_STORED or info.compress_type == zipfile.ZIP_DEFLATED:
										#print ("Adding song %s in ZIP file %s"%(filename, full_path))
										lose, fileonly = os.path.split(filename)
										self.SongList.append(SongStruct(full_path, fileonly, filename))
									else:
										print ("ZIP member %s compressed with unsupported type (%d)"%(filename,info.compress_type))
					except:
						print "Error looking inside zip " + full_path
	
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
	def SearchDatabase (self, SearchTerms):
		# Display a busy cursor while searching, yielding now and again
		# to update the GUI.
		theApp = wxGetApp()
		busyBox = wxBusyCursor()
		searched = 0
		ResultsList = []
		LowerTerms = SearchTerms.lower()
		TermsList = LowerTerms.split()
		for song in self.SongList:
			searched = searched + 1
			if ((searched % 30) == 0):
				theApp.Yield()
			LowerTitle = song.Title.lower()
			LowerPath = song.Filepath.lower()
			misses = 0
			for term in TermsList:
				if (term not in LowerTitle) and (term not in LowerPath):
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
				if self.TempFilePrefix in item:
					full_path = os.path.join (self.TempDir, item)
					os.unlink(full_path)


# Popup settings window for adding song folders, requesting a 
# new folder scan to fill the database etc.
class DatabaseSetupWindow (wxFrame):
	def __init__(self,parent,id,title,KaraokeMgr):
		wxFrame.__init__(self,parent,wxID_ANY, title, size=(450,300),
							style=wxDEFAULT_FRAME_STYLE|wxFRAME_FLOAT_ON_PARENT)
		self.KaraokeMgr = KaraokeMgr
		
		# Help text
		self.HelpText = wxStaticText (self, wxID_ANY,
				"\nAdd folders to build a searchable database of your karaoke songs\n",
				style = wxALIGN_RIGHT) 
		
		# Add the folder list
		self.FolderList = wxListBox(self, -1, style=wxLB_SINGLE)
		for item in self.KaraokeMgr.SongDB.GetFolderList():
			self.FolderList.Append(item)
		
		# Add the buttons
		self.AddFolderButtonID = wxNewId()
		self.DelFolderButtonID = wxNewId()
		self.AddFolderButton = wxButton(self, self.AddFolderButtonID, "Add Folder")
		self.DelFolderButton = wxButton(self, self.DelFolderButtonID, "Delete Folder")
		self.FolderButtonsSizer = wxBoxSizer(wxVERTICAL)
		self.FolderButtonsSizer.Add(self.AddFolderButton, 0, wxALIGN_LEFT, 3)
		self.FolderButtonsSizer.Add(self.DelFolderButton, 0, wxALIGN_LEFT, 3)
		EVT_BUTTON(self, self.AddFolderButtonID, self.OnAddFolderClicked)
		EVT_BUTTON(self, self.DelFolderButtonID, self.OnDelFolderClicked)

		# Create a sizer for the folder list and folder buttons
		self.FolderSizer = wxBoxSizer (wxHORIZONTAL)
		self.FolderSizer.Add (self.FolderList, 1, wxEXPAND, 3)
		self.FolderSizer.Add (self.FolderButtonsSizer, 0, wxALL, 3)

		# Create the settings controls
		self.FileExtensionID = wxNewId()
		self.FiletypesText = wxStaticText (self, wxID_ANY, "Include File Types: ")
		self.cdgCheckBox = wxCheckBox(self, self.FileExtensionID, "CDG")
		self.mpgCheckBox = wxCheckBox(self, self.FileExtensionID, "MPG")
		self.karCheckBox = wxCheckBox(self, self.FileExtensionID, "KAR")
		self.midCheckBox = wxCheckBox(self, self.FileExtensionID, "MID")
		EVT_CHECKBOX (self, self.FileExtensionID, self.OnFileExtChanged)
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
		self.FiletypesSizer = wxBoxSizer (wxHORIZONTAL)
		self.FiletypesSizer.Add (self.cdgCheckBox, 0, wxALL)
		self.FiletypesSizer.Add (self.mpgCheckBox, 0, wxALL)
		self.FiletypesSizer.Add (self.karCheckBox, 0, wxALL)
		self.FiletypesSizer.Add (self.midCheckBox, 0, wxALL)

		# Create the ZIP file setting checkbox
		self.zipID = wxNewId()
		self.zipText = wxStaticText (self, wxID_ANY, "Look Inside ZIPs: ")
		self.zipCheckBox = wxCheckBox(self, self.zipID, "Enabled")
		if self.KaraokeMgr.SongDB.Settings.LookInsideZips == True:
			self.zipCheckBox.SetValue(True)
		else:
			self.zipCheckBox.SetValue(False)
		self.ZipSizer = wxBoxSizer (wxHORIZONTAL)
		self.ZipSizer.Add (self.zipCheckBox, 0, wxALL)
		EVT_CHECKBOX (self, self.zipID, self.OnZipChanged)

		# Create the scan folders button
		self.ScanText = wxStaticText (self, wxID_ANY, "Rescan all folders: ")
		self.ScanFoldersButtonID = wxNewId()
		self.ScanFoldersButton = wxButton(self, self.ScanFoldersButtonID, "Scan Now")
		EVT_BUTTON(self, self.ScanFoldersButtonID, self.OnScanFoldersClicked)

		# Create the save settings button
		self.SaveText = wxStaticText (self, wxID_ANY, "Save settings and song database: ")
		self.SaveSettingsButtonID = wxNewId()
		self.SaveSettingsButton = wxButton(self, self.SaveSettingsButtonID, "Save All")
		EVT_BUTTON(self, self.SaveSettingsButtonID, self.OnSaveSettingsClicked)

		# Create the settings and buttons grid
		self.LowerSizer = wxFlexGridSizer(cols = 2, vgap = 3, hgap = 3)
		self.LowerSizer.Add(self.FiletypesText, 0, wxALL, 3)
		self.LowerSizer.Add(self.FiletypesSizer, 1, wxALL, 3)
		self.LowerSizer.Add(self.zipText, 0, wxALL, 3)
		self.LowerSizer.Add(self.ZipSizer, 1, wxALL, 3)
		self.LowerSizer.Add(self.ScanText, 0, wxALL, 3)
		self.LowerSizer.Add(self.ScanFoldersButton, 1, wxALL, 3)
		self.LowerSizer.Add(self.SaveText, 0, wxALL, 3)
		self.LowerSizer.Add(self.SaveSettingsButton, 1, wxALL, 3)
		
		# Create the main sizer
		self.MainSizer = wxBoxSizer(wxVERTICAL)
		self.MainSizer.Add(self.HelpText, 0, wxEXPAND, 3)
		self.MainSizer.Add(self.FolderSizer, 1, wxEXPAND, 3)
		self.MainSizer.Add(self.LowerSizer, 0, wxALL, 3)
		self.SetSizer(self.MainSizer)
		
		# Add a close handler to ask the user if they want to rescan folders
		self.ScanNeeded = False
		self.SaveNeeded = False
		EVT_WINDOW_DESTROY(self, self.ExitHandler)
	
		self.Show()

	# User wants to add a folder
	def OnAddFolderClicked(self, event):
		dirDlg = wxDirDialog(self)
		retval = dirDlg.ShowModal()
		FolderPath = dirDlg.GetPath()
		if retval == wxID_OK:
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
		if self.ScanNeeded == True:
			self.KaraokeMgr.SongDB.BuildSearchDatabase()
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

	# Popup asking if want to rescan the database after changing settings
	def ExitHandler(self, event):
		if self.ScanNeeded == True:
			changedString = "You have changed settings, would you like to rescan your folders now?"
			answer = wxMessageBox(changedString, "Rescan folders now?", wxYES_NO | wxICON_QUESTION)
			if answer == wxYES:
				self.KaraokeMgr.SongDB.BuildSearchDatabase()
				self.SaveNeeded = True
		if self.SaveNeeded == True:
			saveString = "You have made changes, would you like to save your settings and database now?"
			answer = wxMessageBox(saveString, "Save changes?", wxYES_NO | wxICON_QUESTION)
			if answer == wxYES:
				self.KaraokeMgr.SongDB.SaveSettings()
		self.Close()


# Generic function for popping up errors
def ErrorPopup (ErrorString):
	wxMessageBox(ErrorString, "Error", wxOK | wxICON_ERROR)


# Folder View class subclassed from WxPanel, containing a WxTreeCtrl.
# There is no built in file browser with WxPython, so this was
# implemented using just a basic tree control.
class FileTree (wxPanel):
	def __init__(self, parent, id, KaraokeMgr, x, y):
		wxPanel.__init__(self, parent, id)
		self.KaraokeMgr = KaraokeMgr
		# Windows doesn't like expanding when the root is hidden
		if os.name in ["nt", "dos"]:
			TreeStyle = wxTR_DEFAULT_STYLE
		else:
			TreeStyle = wxTR_HIDE_ROOT|wxTR_NO_LINES|wxTR_HAS_BUTTONS

		# Create the tree control
		self.FileTree = wxTreeCtrl(self, -1, wxPoint(x, y), style=TreeStyle)
		self.FolderOpenIcon = wxBitmap("icons/folder_open_16.png")
		self.FolderClosedIcon = wxBitmap("icons/folder_close_16.png")
		self.FileIcon = wxBitmap("icons/audio_16.png")
		self.ImageList = wxImageList(16, 16)
		self.FolderOpenIconIndex = self.ImageList.Add(self.FolderOpenIcon)
		self.FolderClosedIconIndex = self.ImageList.Add(self.FolderClosedIcon)
		self.FileIconIndex = self.ImageList.Add(self.FileIcon)
		self.FileTree.AssignImageList(self.ImageList)
		self.CreateTreeRoot()
		EVT_TREE_ITEM_EXPANDING(self, wxID_ANY, self.OnFileExpand)
		EVT_TREE_ITEM_COLLAPSING(self, wxID_ANY, self.OnFileCollapse)
		EVT_TREE_ITEM_ACTIVATED(self, wxID_ANY, self.OnFileSelected)

		# Create the status bar
		self.StatusBar = wxStatusBar(self, -1)
		self.StatusBar.SetStatusText ("File Browser View")

		# Create a sizer for the tree view and status bar
		self.VertSizer = wxBoxSizer(wxVERTICAL)
		self.VertSizer.Add(self.FileTree, 1, wxEXPAND, 5)
		self.VertSizer.Add(self.StatusBar, 0, wxEXPAND, 5)
		self.SetSizer(self.VertSizer)
		self.Show(true)

		# Add handlers for right-click in the results box
		EVT_TREE_ITEM_RIGHT_CLICK(self, wxID_ANY, self.OnRightClick)

		# Create IDs for popup menu
		self.menuPlayId = wxNewId()
		self.menuPlaylistAddId = wxNewId()
		self.menuFileDetailsId = wxNewId()
		
	# Create the top-level filesystem entry. This is just root directory on Linux
	# but on Windows we have to find out the drive letters and show those as
	# multiple roots. There doesn't seem to be a portable way to do this with
	# WxPython, so this had to check the OS and use the Win32 API if necessary.
	def CreateTreeRoot(self):
	    # Get a drive list on Windows otherwise start at root
		if os.name in ["nt", "dos"]:
			import win32api
			drives = string.split(win32api.GetLogicalDriveStrings(),'\0')[:-1]
			self.TreeRoot = self.FileTree.AddRoot("")
			self.RootFolder = ""
			for drive in drives:
				node = self.FileTree.AppendItem(self.TreeRoot, drive) 
				self.FileTree.SetItemHasChildren(node, true)
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
			self.FileTree.SetItemHasChildren(node, true)
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
				song = SongStruct (full_path, filename)
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
			menu = wxMenu()
			menu.Append( self.menuPlayId, "Play song" )
			EVT_MENU( menu, self.menuPlayId, self.OnMenuSelection )
			menu.Append( self.menuPlaylistAddId, "Add to playlist" )
			EVT_MENU( menu, self.menuPlaylistAddId, self.OnMenuSelection )
			menu.Append( self.menuFileDetailsId, "File Details" )
			EVT_MENU( menu, self.menuFileDetailsId, self.OnMenuSelection )
			self.PopupMenu( menu, event.GetPoint() )

	# Handle the popup menu events
	def OnMenuSelection( self, event ):
		root, ext = os.path.splitext(self.PopupFilename)
		if self.KaraokeMgr.SongDB.IsExtensionValid(ext) and os.path.isfile (self.PopupFullPath):
			# Create a SongStruct because that's what karaoke mgr wants
			song = SongStruct (self.PopupFullPath, self.PopupFilename)
			# Now respond to the menu choice
			if event.GetId() == self.menuPlayId:
				self.KaraokeMgr.PlayWithoutPlaylist(song)
			elif event.GetId() == self.menuPlaylistAddId:
				self.KaraokeMgr.AddToPlaylist(song)
			elif event.GetId() == self.menuFileDetailsId:
				wxMessageBox("File: " + self.PopupFullPath, "File details", wxOK)


# Implement the Search Results panel and list box
class SearchResultsPanel (wxPanel):
	def __init__(self, parent, id, KaraokeMgr, x, y):
		wxPanel.__init__(self, parent, id)
		self.KaraokeMgr = KaraokeMgr

		self.parent = parent

		self.SearchText = wxTextCtrl(self, -1, style=wxTE_PROCESS_ENTER)
		self.SearchButton = wxButton(self, -1, "Search")
		self.SearchSizer = wxBoxSizer(wxHORIZONTAL)
		self.SearchSizer.Add(self.SearchText, 1, wxEXPAND, 5)
		self.SearchSizer.Add(self.SearchButton, 0, wxEXPAND, 5)
		
		self.ListPanel = wxListBox(self, -1)
		
		self.StatusBar = wxStatusBar(self, -1)
		self.StatusBar.SetStatusText ("Search Results")
		
		self.VertSizer = wxBoxSizer(wxVERTICAL)
		self.InterGap = 5
		self.VertSizer.Add(self.SearchSizer, 0, wxEXPAND, self.InterGap)
		self.VertSizer.Add(self.ListPanel, 1, wxEXPAND, self.InterGap)
		self.VertSizer.Add(self.StatusBar, 0, wxEXPAND, self.InterGap)
		self.SetSizer(self.VertSizer)
		self.Show(true)

		EVT_LISTBOX_DCLICK(self, wxID_ANY, self.OnFileSelected)
		EVT_BUTTON(self, wxID_ANY, self.OnSearchClicked)
		EVT_TEXT_ENTER(self, wxID_ANY, self.OnSearchClicked)

		# Add handlers for right-click in the results box
		EVT_RIGHT_UP(self.ListPanel, self.OnRightClick)

		# Create IDs for popup menu
		self.menuPlayId = wxNewId()
		self.menuPlaylistAddId = wxNewId()
		self.menuFileDetailsId = wxNewId()
		
	# Handle a file selected event (double-click). Plays directly (not add to playlist)
	def OnFileSelected(self, event):
		# The SongStruct is stored as data - get it and pass to karaoke mgr
		selected_index = self.ListPanel.GetSelection()
		song = self.ListPanel.GetClientData(selected_index)
		self.KaraokeMgr.PlayWithoutPlaylist(song)

	# Handle the search button clicked event
	def OnSearchClicked(self, event):
		# Empty the previous results and perform a new search
		self.StatusBar.SetStatusText ("Please wait... Searching")
		songList = self.KaraokeMgr.SongDB.SearchDatabase(self.SearchText.GetValue())
		if self.KaraokeMgr.SongDB.GetDatabaseSize() == 0:
			setupString = "You have not yet set up your song folders yet. Would you like to do it now?"
			answer = wxMessageBox(setupString, "Setup database now?", wxYES_NO | wxICON_QUESTION)
			if answer == wxYES:
				# Open up the database setup dialog
				self.Frame = DatabaseSetupWindow(self.parent, -1, "Database Setup", self.KaraokeMgr)
				self.StatusBar.SetStatusText ("Search Results")
			else:
				self.StatusBar.SetStatusText ("No songs in song database")
		elif len(songList) == 0:
			ErrorPopup("No matches found for " + self.SearchText.GetValue())
			self.StatusBar.SetStatusText ("No matches found")
		else:
			self.ListPanel.Clear()
			for song in songList:
				# Store the SongStruct as client data and set the list text as the title
				self.ListPanel.Append(song.Title, song)
			self.StatusBar.SetStatusText ("Search Results")

	# Handle right-click on a search results item (show the popup menu)
	def OnRightClick(self, event):
		# Doesn't bring up a popup if no items are in the list
		if self.ListPanel.GetCount() > 0:
			menu = wxMenu()
			menu.Append( self.menuPlayId, "Play song" )
			EVT_MENU( menu, self.menuPlayId, self.OnMenuSelection )
			menu.Append( self.menuPlaylistAddId, "Add to playlist" )
			EVT_MENU( menu, self.menuPlaylistAddId, self.OnMenuSelection )
			menu.Append( self.menuFileDetailsId, "File Details" )
			EVT_MENU( menu, self.menuFileDetailsId, self.OnMenuSelection )
			# Set the menu position. Add the event x,y offsets to the
			# location of the listbox
			menuPos = self.GetPosition()
			menuPos[0] = menuPos[0] + event.m_x
			menuPos[1] = menuPos[1] + event.m_y
			# Select the listbox item, as right-click mouse event doesn't
			# actually select the item. We have to calculate the line to
			# find out where the user right-clicked... If it's below the
			# last item, just select the last item in the list.
			CharHeight=self.ListPanel.GetCharHeight() + self.InterGap - 1
			selectedIndex = int(event.m_y/CharHeight)
			if selectedIndex > (self.ListPanel.GetCount() - 1):
				selectedIndex = self.ListPanel.GetCount() - 1
			self.ListPanel.SetSelection(selectedIndex)
			self.parent.PopupMenu( menu, menuPos )

	# Handle popup menu selection events
	def OnMenuSelection( self, event ):
		selected_index = self.ListPanel.GetSelection()
		song = self.ListPanel.GetClientData(selected_index)
		if event.GetId() == self.menuPlayId:
			self.KaraokeMgr.PlayWithoutPlaylist(song)
		elif event.GetId() == self.menuPlaylistAddId:
			self.KaraokeMgr.AddToPlaylist(song)
		elif event.GetId() == self.menuFileDetailsId:
			if song.ZipStoredName:
				detailsString = "File: " + song.ZipStoredName + "\nInside ZIP: " + song.Filepath
			else:
				detailsString = "File: " + song.Filepath
			wxMessageBox(detailsString, song.Title, wxOK)


# Class to manage the playlist panel and list box
class Playlist (wxPanel):
	def __init__(self, parent, id, KaraokeMgr, x, y):
		wxPanel.__init__(self, parent, id)
		self.KaraokeMgr = KaraokeMgr
		self.parent = parent
		
		# Create the playlist control
		self.Playlist = wxListBox(self, -1, wxPoint(x, y))

		# Create the status bar
		self.StatusBar = wxStatusBar(self, -1)
		self.StatusBar.SetStatusText ("Playlist")

		# Create a sizer for the tree view and status bar
		self.InterGap = 5
		self.VertSizer = wxBoxSizer(wxVERTICAL)
		self.VertSizer.Add(self.Playlist, 1, wxEXPAND, self.InterGap)
		self.VertSizer.Add(self.StatusBar, 0, wxEXPAND, self.InterGap)
		self.SetSizer(self.VertSizer)
		self.Show(true)

		# Add handlers for right-click in the listbox
		EVT_LISTBOX_DCLICK(self, wxID_ANY, self.OnFileSelected)
		EVT_RIGHT_UP(self.Playlist, self.OnRightClick)

		# Create IDs for popup menu
		self.menuPlayId = wxNewId()
		self.menuDeleteId = wxNewId()
		self.menuClearListId = wxNewId()

	# Handle item selected (double-click). Starts the selected track.
	def OnFileSelected(self, event):
		self.KaraokeMgr.PlaylistStart()

	# Handle right-click in the playlist (show popup menu).
	def OnRightClick(self, event):
		# Doesn't bring up a popup if no items are in the list
		if self.Playlist.GetCount() > 0:
			menu = wxMenu()
			menu.Append( self.menuPlayId, "Play song" )
			EVT_MENU( menu, self.menuPlayId, self.OnMenuSelection )
			menu.Append( self.menuDeleteId, "Delete from playlist" )
			EVT_MENU( menu, self.menuDeleteId, self.OnMenuSelection )
			menu.Append( self.menuClearListId, "Clear playlist" )
			EVT_MENU( menu, self.menuClearListId, self.OnMenuSelection )
			# Set the menu position. Add the event x,y offsets to the
			# location of the listbox
			menuPos = self.GetPosition()
			menuPos[0] = menuPos[0] + event.m_x
			menuPos[1] = menuPos[1] + event.m_y
			# Select the listbox item, as right-click mouse event doesn't
			# actually select the item. We have to calculate the line.
			# If it's below the last item, just select the last item.
			CharHeight=self.Playlist.GetCharHeight() + self.InterGap - 1
			selectedIndex = int(event.m_y/CharHeight)
			if selectedIndex > (self.Playlist.GetCount() - 1):
				selectedIndex = self.Playlist.GetCount() - 1
			self.Playlist.SetSelection(selectedIndex)
			self.parent.PopupMenu( menu, menuPos )

	# Handle popup menu selection events.
	def OnMenuSelection( self, event ):
		if event.GetId() == self.menuPlayId:
			self.KaraokeMgr.PlaylistStart()
		elif event.GetId() == self.menuDeleteId:
			for index in self.Playlist.GetSelections():
				self.Playlist.Delete(index)
		elif event.GetId() == self.menuClearListId:
			for index in range(self.Playlist.GetCount()):
				self.Playlist.Delete(0)


# Main window
class PyKaraokeWindow (wxFrame):
	def __init__(self,parent,id,title,KaraokeMgr):
		self.Width = 640
		self.Height = 480
		wxFrame.__init__(self,parent,wxID_ANY, title, size = (self.Width,self.Height),
							style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)
		self.KaraokeMgr = KaraokeMgr
		
		# Create left-hand side buttons at the button
		choices = ["Search View", "Folder View"]
		self.ViewChoiceID = wxNewId()
		self.DBButtonID = wxNewId()
		self.DatabaseButton = wxButton(self, self.DBButtonID, "Add Songs")
		buttonSize = self.DatabaseButton.GetSize()
		self.ViewChoice = wxChoice(self, self.ViewChoiceID, (0,0), (-1, buttonSize[1]), choices)
		self.LeftTopSizer = wxBoxSizer(wxHORIZONTAL)
		self.LeftTopSizer.Add(self.ViewChoice, 0, wxALIGN_LEFT)
		self.LeftTopSizer.Add((0, 0), 1, 1)
		self.LeftTopSizer.Add(self.DatabaseButton, 0, wxALIGN_RIGHT)
		EVT_CHOICE(self, self.ViewChoiceID, self.OnViewChosen)
		EVT_BUTTON(self, self.DBButtonID, self.OnDBClicked)

		# Create the view and playlist panels
		self.TreePanel = FileTree(self, -1, KaraokeMgr, 0, 0)
		self.SearchPanel = SearchResultsPanel(self, -1, KaraokeMgr, 0, 0)
		self.PlaylistPanel = Playlist(self, -1, KaraokeMgr, 0, 0)
		self.LeftSizer = wxBoxSizer(wxVERTICAL)
		self.LeftSizer.Add(self.LeftTopSizer, 0, wxALL | wxEXPAND, 5)
		self.LeftSizer.Add(self.TreePanel, 1, wxALL | wxEXPAND, 5)
		self.LeftSizer.Add(self.SearchPanel, 1, wxALL | wxEXPAND, 5)
		self.RightSizer = wxBoxSizer(wxVERTICAL)
		self.RightSizer.Add(self.PlaylistPanel, 1, wxALL | wxEXPAND, 5)
		self.ViewSizer = wxBoxSizer(wxHORIZONTAL)
		self.ViewSizer.Add(self.LeftSizer, 1, wxALL | wxEXPAND, 5)
		self.ViewSizer.Add(self.RightSizer, 1, wxALL | wxEXPAND, 5)

		# Default start in Search View
		self.LeftSizer.Show(self.TreePanel, False)
		self.ViewChoice.SetSelection(0)
		self.SearchPanel.SearchText.SetFocus()

		# Put the top level buttons and main panels in a sizer
		self.MainSizer = wxBoxSizer(wxVERTICAL)
		# Add a top-level set of buttons across both panels here if desired
		#self.MainSizer.Add(self.TopSizer, 0, wxALL)
		self.MainSizer.Add(self.ViewSizer, 1, wxALL | wxEXPAND)
		self.SetAutoLayout(true)
		self.SetSizer(self.MainSizer)

		# Attach on exit handler to clean up temporary files
		EVT_CLOSE(self, self.OnClose)

		self.Show(true)

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

	# Handle closing pykaraoke (need to delete any temporary files on close)
	def OnClose(self, event):
		self.KaraokeMgr.SongDB.CleanupTempFiles()
		self.Destroy()


# Subclass WxPyEvent to add storage for an extra data pointer
class PyKaraokeEvent(wxPyEvent):
    def __init__(self, event_id, data):
        wxPyEvent.__init__(self)
        self.SetEventType(event_id)
        self.data = data


# Main manager class, starts the window and handles the playlist and players
class PyKaraokeManager:
	def __init__(self):
		# Set the default file types that should be displayed
		self.Player = None
		# Set up and store the song database instance
		self.SongDB = SongDB(self)
		# Set up the WX windows
		self.Frame = PyKaraokeWindow(None, -1, "PyKaraoke", self)
		# Set the default display size
		self.DisplaySize = (640, 480)
		# Set up an event so the player threads can call back and perform
		# GUI operations
		self.EVT_SONG_FINISHED = wxNewId()
		self.EVT_ERROR_POPUP = wxNewId()
		self.Frame.Connect(-1, -1, self.EVT_SONG_FINISHED, self.SongFinishedEventHandler)
		self.Frame.Connect(-1, -1, self.EVT_ERROR_POPUP, self.ErrorPopupEventHandler)
		# Used to tell the song finished callback that a song has been
		# requested for playing straight away
		self.DirectPlaySongStruct = None
		# Used to store the currently playing song (if from the playlist)
		self.PlayingIndex = 0
	
	# Called when a karaoke file is added to the playlist from the 
	# file tree or search results for adding to the playlist. 
	# Handles adding to the playlist panel, playing if necessary etc.
	# Takes a SongStruct so it has both title and full path details.
	# Stores the SongStruct in the Playlist control and sets the title.
	def AddToPlaylist(self, song_struct):
		self.Frame.PlaylistPanel.Playlist.Append(song_struct.Title, song_struct)
	
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
	def PlaylistStart(self):
		song_index = self.Frame.PlaylistPanel.Playlist.GetSelection()
		if not self.Player:
			song_struct = self.Frame.PlaylistPanel.Playlist.GetClientData(song_index)
			self.StartPlayer(song_struct)
			self.PlayingIndex = song_index
			# Show the song as selected in the playlist
			self.Frame.PlaylistPanel.Playlist.SetSelection(self.PlayingIndex)
		else:
			# Note that this will be -1 if the first item is playing,
			# but this is a valid index for GetNextItem() - it will 
			# get the first song in the list.
			self.PlayingIndex = song_index - 1
			self.Player.Close()	
		
	# The callback is in the player thread context, so need to post an event
	# for the GUI thread, actually handled by SongFinishedEventHandler()
	def SongFinishedCallback(self):
		event = PyKaraokeEvent(self.EVT_SONG_FINISHED, None)
		wxPostEvent (self.Frame, event)
	
	# Handle the song finished event. This is triggered by the callback but
	# runs in the GUI thread, instead of the player thread which the callback
	# runs in.
	def SongFinishedEventHandler(self, event):
		# Find out if the user changed the display size, to use on the next song.
		# Note it's not possible to get the current pygame window position, so
		# the players always start at the top-left (0,0)
		self.DisplaySize = self.Player.GetDisplaySize()
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
		elif (self.PlayingIndex != -2) and (next_index <= (self.Frame.PlaylistPanel.Playlist.GetCount() - 1)):
			song_struct = self.Frame.PlaylistPanel.Playlist.GetClientData(next_index)
			self.StartPlayer(song_struct)
			self.PlayingIndex = next_index
			# Show the song as selected in the playlist
			self.Frame.PlaylistPanel.Playlist.SetSelection(next_index)
		else:
			self.Player = None
		# Delete any temporary files that may have been unzipped
		self.SongDB.CleanupTempFiles()

	# The callback is in the player thread context, so need to post an event
	# for the GUI thread, actually handled by ErrorPopupEventHandler()
	def ErrorPopupCallback(self, ErrorString):
		# We use the extra data storage we got by subclassing WxPyEvent to
		# pass data to the event handler (the error string).
		event = PyKaraokeEvent(self.EVT_ERROR_POPUP, ErrorString)
		wxPostEvent (self.Frame, event)
		
	# Handle the error popup event, runs in the GUI thread.
	def ErrorPopupEventHandler(self, event):
		ErrorPopup(event.data)
	
	# Takes a SongStruct, which contains any info on ZIPs etc
	def StartPlayer(self, song_struct):
		# Create the necessary player instance for this filetype.
		# The players run in a separate thread.
		root, ext = os.path.splitext(song_struct.Filepath)
		if ext.lower() == ".zip":
			# It's in a ZIP file, unpack it
			zip = zipfile.ZipFile(song_struct.Filepath)
			root, stored_ext = os.path.splitext(song_struct.ZipStoredName)
			# Need to get the MP3 out for a CDG as well
			if stored_ext.lower() == ".cdg":
				tmpfile_prefix = self.SongDB.CreateTempFileNamePrefix()
				# Create a local CDG file using the filename in the zip file.
				# (slicing off any path info first in case its in a subdir in the zip).
				lose, cdgpath = os.path.split(song_struct.ZipStoredName)
				cdg_file = open (tmpfile_prefix + cdgpath, "wb")
				cdg_data = zip.read(song_struct.ZipStoredName)
				cdg_file.write(cdg_data)
				cdg_file.close()
				# Guess the mp3 stored name from the CDG stored name
				root_filename, lose = os.path.splitext(song_struct.ZipStoredName)
				# Might be .mp3 or .MP3, try both
				try:
					mp3_filename = root_filename + ".mp3"
					mp3_data = zip.read(mp3_filename)
				except:
					mp3_filename = root_filename + ".MP3"
					mp3_data = zip.read(mp3_filename)
				# Create a local mp3 file based on the CDG filename in the zip file.
				# (slicing off any path info first in case its in a subdir in the zip).
				lose, local_mp3_path = os.path.split(mp3_filename)
				mp3_file = open (tmpfile_prefix + local_mp3_path, "wb")
				mp3_file.write(mp3_data)
				mp3_file.close()				
				zip.close()
				self.FilePath = tmpfile_prefix + cdgpath
			else:
			# Not a CDG, just unzip the one file
				# Handle files in sub-dirs inside the zip
				lose, local_file = os.path.split(song_struct.ZipStoredName)
				unzipped_file = open (tmpfile_prefix + local_file, "wb")
				unzipped_data = zip.read(song_struct.ZipStoredName)
				unzipped_file.write(unzipped_data)
				unziped_file.close()
				zip.close()
				self.FilePath = tmpfile_prefix + local_file
		else:
			# A non-zipped file, just start playing
			self.FilePath = song_struct.Filepath

		try:
			root, ext = os.path.splitext(self.FilePath)
			if ext.lower() == ".cdg":
				self.Player = pycdg.cdgPlayer(self.FilePath, self.ErrorPopupCallback, self.SongFinishedCallback)
		#	elif (ext.lower() == ".kar") or (ext == ".mid"):
		#		self.Player = pykar.karPlayer(self.FilePath, self.ErrorPopupCallback, self.SongFinishedCallback)
			elif (ext.lower() == ".mpg") or (ext == ".mpeg"):
				self.Player = pympg.mpgPlayer(self.FilePath, self.ErrorPopupCallback, self.SongFinishedCallback)
			# TODO basic mp3/ogg player
			else:
				ErrorPopup ("Unsupported file format " + ext)
		
			# Set the display size to the user's current preference (i.e. last song)
			self.Player.SetDisplaySize (self.DisplaySize)
		
			# Start playing
			self.Player.Play()
		except:
			ErrorPopup ("Error starting player")
		
PyKaraokeApp = wxPySimpleApp()
Mgr = PyKaraokeManager()
PyKaraokeApp.MainLoop()

