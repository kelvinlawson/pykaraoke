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


import os, string, zipfile, pickle, wx, sys
import pycdg, pympg, pykar, pykversion

# Size of the main window
MAIN_WINDOW_SIZE = (604,480)

# Size of the Database setup window
DB_WINDOW_SIZE = (450,300)

# Size of the Config window
CONFIG_WINDOW_SIZE = (240,60)

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
	def __init__(self, FolderList, FileExtensions, LookInsideZips, FullScreen):
		self.Version = pykversion.PYKARAOKE_VERSION_STRING
		self.FolderList = FolderList			# List of song folders
		self.FileExtensions = FileExtensions	# List of extensions (.cdg etc)
		self.LookInsideZips = LookInsideZips	# Whether to look inside zips
		self.FullScreen = False					# Full-screen mode


# Song database class with methods for building the database, searching etc
class SongDB:
	def __init__(self, KaraokeMgr):
		# Filepaths and titles are stored in a list of SongStruct instances
		self.SongList = []
	
		# Set the default settings, in case none are stored on disk
		folder_path = []
		file_extensions = [".cdg", ".mpg", ".mpeg", ".kar", ".mid"]
		look_inside_zips = True
	
		# Create a SettingsStruct instance for storing settings
		# in case none are stored.
		self.Settings = SettingsStruct (folder_path, file_extensions, look_inside_zips, False)
		
		# Store the karaoke manager instance
		self.KaraokeMgr = KaraokeMgr
		
		# All temporary files use this prefix
		self.TempFilePrefix = "00Pykar__"

		# Get Wx's idea of the home directory
		self.TempDir = os.path.join(wx.GetHomeDir(), ".pykaraoke")
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
			loadsettings = pickle.load (file)
			try:
				# Check settings are for the current version
				if (loadsettings.Version == pykversion.PYKARAOKE_VERSION_STRING):
					self.Settings = loadsettings
			except:
				ErrorPopup ("New version of PyKaraoke, clearing settings")
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
		# Zap the database and build again from scratch. Return False
		# if was cancelled.
		cancelled = False
		self.SongList = []
		self.BusyDlg = BusyCancelDialog (self.KaraokeMgr.Frame, "Searching")
		self.BusyDlg.Show()
		for root_path in self.Settings.FolderList:
			cancelled = self.FolderScan (root_path)
			if cancelled == True:
				break
		self.BusyDlg.Destroy()
		return cancelled

	def FolderScan (self, FolderToScan):
		# Search for karaoke files inside the folder, looking inside ZIPs if
		# configured to do so. Function is recursive for subfolders.
		filedir_list = os.listdir(FolderToScan)
		theApp = wx.GetApp()
		searched = 0
		for item in filedir_list:
			searched = searched + 1
			# Allow windows to refresh now and again while scanning
			if ((searched % 5) == 0):
				# Check if cancel was clicked
				if self.BusyDlg.Clicked == True:
					return (True)
				else:
					theApp.Yield()
			full_path = os.path.join(FolderToScan, item)
			# Recurse into subdirectories
			if os.path.isdir(full_path):
				cancelled = self.FolderScan (full_path)
				if cancelled == True:
					return (True)
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
										zipname_with_file = item + ": " + fileonly
										self.SongList.append(SongStruct(full_path, zipname_with_file, filename))
									else:
										print ("ZIP member %s compressed with unsupported type (%d)"%(filename,info.compress_type))
					except:
						print "Error looking inside zip " + full_path
		return (False)

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
		theApp = wx.GetApp()
		busyBox = wx.BusyCursor()
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



# Popup busy window with cancel button
class BusyCancelDialog (wx.Frame):
	def __init__(self,parent,title):
		pos = parent.GetPosition()
		pos[0] += (MAIN_WINDOW_SIZE[0] / 2) - 70
		pos[1] += (MAIN_WINDOW_SIZE[1] / 2) - 25
		wx.Frame.__init__(self,parent,wx.ID_ANY, title, size=(140,50),
							style=wx.SYSTEM_MENU|wx.CAPTION|wx.FRAME_FLOAT_ON_PARENT,pos=pos)
		
		# Add the buttons
		self.CancelButtonID = wx.NewId()
		self.CancelButton = wx.Button(self, self.CancelButtonID, "Cancel")
		wx.EVT_BUTTON(self, self.CancelButtonID, self.OnCancelClicked)

		# Set clicked status
		self.Clicked = False

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
		self.HelpText = wx.StaticText (self, wx.ID_ANY,
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
		self.LowerSizer.Add(self.ScanText, 0, wx.ALL, 3)
		self.LowerSizer.Add(self.ScanFoldersButton, 1, wx.ALL, 3)
		self.LowerSizer.Add(self.SaveText, 0, wx.ALL, 3)
		self.LowerSizer.Add(self.SaveSettingsButton, 1, wx.ALL, 3)
		
		# Create the main sizer
		self.MainSizer = wx.BoxSizer(wx.VERTICAL)
		self.MainSizer.Add(self.HelpText, 0, wx.EXPAND, 3)
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
		cancelled = self.KaraokeMgr.SongDB.BuildSearchDatabase()
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

	# Popup asking if want to rescan the database after changing settings
	def ExitHandler(self, event):
		if self.ScanNeeded == True:
			changedString = "You have changed settings, would you like to rescan your folders now?"
			answer = wx.MessageBox(changedString, "Rescan folders now?", wx.YES_NO | wx.ICON_QUESTION)
			if answer == wx.YES:
				self.KaraokeMgr.SongDB.BuildSearchDatabase()
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

		# Create a sizer for the settings
		self.ConfigSizer = wx.BoxSizer (wx.HORIZONTAL)
		self.ConfigSizer.Add (self.FSCheckBox, 0, wx.ALL)

		# Create the main sizer
		self.MainSizer = wx.BoxSizer(wx.VERTICAL)
		self.MainSizer.Add(self.ConfigSizer, 0, wx.ALL, 3)
		self.SetSizer(self.MainSizer)
	
		self.Show()

	# User changed a checkbox, just do them all again
	def OnFSChanged(self, event):
		self.KaraokeMgr.SongDB.Settings.FullScreen = self.FSCheckBox.IsChecked()
		self.KaraokeMgr.SongDB.SaveSettings()
		

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
			song = SongStruct (self.PopupFullPath, self.PopupFilename)
			# Now respond to the menu choice
			if event.GetId() == self.menuPlayId:
				self.KaraokeMgr.PlayWithoutPlaylist(song)
			elif event.GetId() == self.menuPlaylistAddId:
				self.KaraokeMgr.AddToPlaylist(song)
			elif event.GetId() == self.menuFileDetailsId:
				wx.MessageBox("File: " + self.PopupFullPath, "File details", wx.OK)


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
		self.ListPanel.InsertColumn (0, "Search Results", width=500)

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
		self.RightClicekedItemIndex = -1
		wx.EVT_LIST_ITEM_RIGHT_CLICK(self.ListPanel, wx.ID_ANY, self.OnRightClick)

		# Resize column width to the same as list width (or longest title, whichever bigger)
		wx.EVT_SIZE(self.ListPanel, self.onResize)
		# Store the width (in pixels not chars) of the longest title
		self.MaxTitleWidth = 0
 
		# Create IDs for popup menu
		self.menuPlayId = wx.NewId()
		self.menuPlaylistAddId = wx.NewId()
		self.menuFileDetailsId = wx.NewId()
		
	# Handle a file selected event (double-click). Plays directly (not add to playlist)
	def OnFileSelected(self, event):
		# The SongStruct is stored as data - get it and pass to karaoke mgr
		selected_index = event.GetIndex()
		song = self.SongStructList[selected_index]
		self.KaraokeMgr.PlayWithoutPlaylist(song)

	# Handle the search button clicked event
	def OnSearchClicked(self, event):
		# Empty the previous results and perform a new search
		self.StatusBar.SetStatusText ("Please wait... Searching")
		songList = self.KaraokeMgr.SongDB.SearchDatabase(self.SearchText.GetValue())
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
			self.MaxTitleWidth = 0
			index = 0
			for song in songList:
				# Set the SongStruct title as the text
				self.ListPanel.InsertStringItem(index, song.Title)
				index = index + 1
				if (len(song.Title) * self.GetCharWidth()) > self.MaxTitleWidth:
					self.MaxTitleWidth = (len(song.Title) * self.GetCharWidth())
			# Keep a copy of all the SongStructs in a list, accessible via item index
			self.SongStructList = songList
			self.StatusBar.SetStatusText ("%d songs found" % index)
			# Set the column width now we've added some titles
			self.doResize()

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
		song = self.SongStructList[self.RightClickedItemIndex]
		if event.GetId() == self.menuPlayId:
			self.KaraokeMgr.PlayWithoutPlaylist(song)
		elif event.GetId() == self.menuPlaylistAddId:
			self.KaraokeMgr.AddToPlaylist(song)
		elif event.GetId() == self.menuFileDetailsId:
			if song.ZipStoredName:
				detailsString = "File: " + song.ZipStoredName + "\nInside ZIP: " + song.Filepath
			else:
				detailsString = "File: " + song.Filepath
			wx.MessageBox(detailsString, song.Title, wx.OK)

	def onResize(self, event):
		self.doResize()
		event.Skip()

	# Common handler for SIZE events and our own resize requests
	def doResize(self):
		# Get the listctrl's width
		listWidth = self.ListPanel.GetClientSize().width
		# We're showing the vertical scrollbar -> allow for scrollbar width
		# NOTE: on GTK, the scrollbar is included in the client size, but on
		# Windows it is not included
		if wx.Platform != '__WXMSW__':
			if self.ListPanel.GetItemCount() > self.ListPanel.GetCountPerPage():
				scrollWidth = wx.SystemSettings_GetSystemMetric(wx.SYS_VSCROLL_X)
				listWidth = listWidth - scrollWidth

		# Only one column, set its width to list width, or the longest title if larger
		if self.MaxTitleWidth > listWidth:
			width = self.MaxTitleWidth
		else:
			width = listWidth
		self.ListPanel.SetColumnWidth(0, width)


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
				scrollWidth = wx.SystemSettings_GetSystemMetric(wx.SYS_VSCROLL_X)
				listWidth = listWidth - scrollWidth

		# Only one column, set its width to list width, or the longest title if larger
		if self.MaxTitleWidth > listWidth:
			width = self.MaxTitleWidth
		else:
			width = listWidth
		self.Playlist.SetColumnWidth(0, width)


	# Add item to playlist
	def AddItem( self, song_struct ):
		self.Playlist.InsertStringItem(self.Playlist.GetItemCount(), song_struct.Title)
		self.PlaylistSongStructList.append(song_struct)
		# Update the max title width for column sizing, in case this is the largest one yet
		if ((len(song_struct.Title) * self.GetCharWidth()) > self.MaxTitleWidth):
			self.MaxTitleWidth = len(song_struct.Title) * self.GetCharWidth()
			self.doResize()
	
	# Delete item from playlist
	def DelItem( self, item_index ):
		# Update the max title width for column sizing, in case this was the largest one
		if ((len(self.PlaylistSongStructList[item_index].Title) * self.GetCharWidth()) == self.MaxTitleWidth):
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
				if (len(song_struct.Title) * self.GetCharWidth()) > self.MaxTitleWidth:
					self.MaxTitleWidth = len(song_struct.Title) * self.GetCharWidth()
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


# Main window
class PyKaraokeWindow (wx.Frame):
	def __init__(self,parent,id,title,KaraokeMgr):
		wx.Frame.__init__(self,parent,wx.ID_ANY, title, size = MAIN_WINDOW_SIZE,
							style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
		self.KaraokeMgr = KaraokeMgr
		
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


# Subclass WxPyEvent to add storage for an extra data pointer
class PyKaraokeEvent(wx.PyEvent):
    def __init__(self, event_id, data):
        wx.PyEvent.__init__(self)
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
		self.Frame = PyKaraokeWindow(None, -1, "PyKaraoke " + pykversion.PYKARAOKE_VERSION_STRING, self)
		# Set the default display size
		self.DisplaySize = (640, 480)
		# Set up an event so the player threads can call back and perform
		# GUI operations
		self.EVT_SONG_FINISHED = wx.NewId()
		self.EVT_ERROR_POPUP = wx.NewId()
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
		# We use the extra data storage we got by subclassing WxPyEvent to
		# pass data to the event handler (the error string).
		event = PyKaraokeEvent(self.EVT_ERROR_POPUP, ErrorString)
		wx.PostEvent (self.Frame, event)
		
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
			tmpfile_prefix = self.SongDB.CreateTempFileNamePrefix()
			root, stored_ext = os.path.splitext(song_struct.ZipStoredName)
			# Need to get the MP3 out for a CDG as well
			if stored_ext.lower() == ".cdg":
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
				unzipped_file.close()
				zip.close()
				self.FilePath = tmpfile_prefix + local_file
		else:
			# A non-zipped file, just start playing
			self.FilePath = song_struct.Filepath

		try:
			root, ext = os.path.splitext(self.FilePath)
			if ext.lower() == ".cdg":
				self.Player = pycdg.cdgPlayer(self.FilePath, None, self.ErrorPopupCallback, self.SongFinishedCallback)
				# Set the display size to the user's current preference (i.e. last song)
				self.Player.SetDisplaySize (self.DisplaySize)
				if (self.SongDB.Settings.FullScreen == True):
					self.Player.SetFullScreen ()
			elif (ext.lower() == ".kar") or (ext.lower() == ".mid"):
				self.Player = pykar.midPlayer(self.FilePath, self.ErrorPopupCallback, self.SongFinishedCallback)
			elif (ext.lower() == ".mpg") or (ext.lower() == ".mpeg"):
				self.Player = pympg.mpgPlayer(self.FilePath, self.ErrorPopupCallback, self.SongFinishedCallback)
				# Set the display size to the user's current preference (i.e. last song)
				self.Player.SetDisplaySize (self.DisplaySize)
				if (self.SongDB.Settings.FullScreen == True):
					self.Player.SetFullScreen ()
			# TODO basic mp3/ogg player
			else:
				ErrorPopup ("Unsupported file format " + ext)
		
			# Set the status bar
			self.Frame.PlaylistPanel.StatusBar.SetStatusText ("Playing " + song_struct.Title)
		
			# Start playing
			self.Player.Play()
		except:
			ErrorPopup ("Error starting player")

def main():
	PyKaraokeApp = wx.PySimpleApp()
	Mgr = PyKaraokeManager()
	PyKaraokeApp.MainLoop()

if __name__ == "__main__":
    sys.exit(main())
