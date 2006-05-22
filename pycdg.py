#!/usr/bin/env python

# pycdg - CDG/MP3+G Karaoke Player

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
# pycdg is a CDG karaoke player which supports MP3+G and OGG+G tracks.
#
# The player uses the pygame library (www.pygame.org), and can therefore
# run on any operating system that runs pygame (currently Linux, Windows
# and OSX).
#
# You can use this file as a standalone player, or together with
# PyKaraoke. PyKaraoke provides a graphical user interface, playlists,
# searchable song database etc.
#
# For those writing a media player or similar project who would like
# CDG support, this module has been designed to be easily incorporated
# into such projects and is released under the LGPL.


# REQUIREMENTS
#
# pycdg requires the following to be installed on your system:
# . Python (www.python.org)
# . Pygame (www.pygame.org)
# . Numeric module (numpy.sourceforge.net)


# USAGE INSTRUCTIONS
#
# To start the player, pass the CDG filename/path on the command line:
# 		python pycdg.py /songs/theboxer.cdg
#
# You can also incorporate a CDG player in your own projects by
# importing this module. The class cdgPlayer is exported by the
# module. You can import and start it as follows:
#	import pycdg
#	player = pycdg.cdgPlayer("/songs/theboxer.cdg")
#	player.Play()
#
# The class also exports Close(), Pause(), Rewind(), GetPos().
#
# There are two optional parameters to the initialiser, errorNotifyCallback
# and doneCallback:
#
# errorNotifyCallback, if provided, will be used to print out any error
# messages (e.g. song file not found). This allows the module to fit 
# together well with GUI playlist managers by utilising the same GUI's
# error popup window mechanism (or similar). If no callback is provided,
# errors are printed to stdout. errorNotifyCallback should take one 
# parameter, the error string, e.g.:
# 	def errorPopup (ErrorString):
#		msgBox (ErrorString)
#
# doneCallback can be used to register a callback so that the player
# calls you back when the song is finished playing. The callback should
# take no parameters, e.g.:
# 	def songFinishedCallback():
#		msgBox ("Song is finished")
#
# To register callbacks, pass the functions in to the initialiser:
# 	cdgPlayer ("/songs/theboxer.cdg", errorPopup, songFinishedCallback)
# These parameters are optional and default to None.
#
# If the initialiser fails (e.g. the song file is not present), __init__
# raises an exception.


# IMPLEMENTATION DETAILS
#
# pycdg is implemented as one python module. It performs all
# of the CDG file decoding locally, and gets audio playback
# and video display capabilities from the pygame library.
# It also uses the python Numeric module, which provides
# fast handling of the arrays of pixel data for the display.
#
# All of the information on the CDG file format was learned
# from the fabulous "CDG Revealed" tutorial at www.jbum.com.
#
# The player is run within a thread to allow for easy
# integration with media player programs. The thread starts
# the pygame MP3/OGG playback, and then monitors the current
# time in the song. It reads the CDG file at the correct
# location for the current position of the song, and decodes
# the CDG commands stored there. If the CDG command requires
# a screen update, a local array of pixels is updated to
# reflect the new graphic information. Rather than update
# directly to the screen for every command, updates are
# cached and output to the screen ten times per second 
# (configurable). Performing the scaling and blitting
# required for screen updates consumes a lot of CPU
# horsepower, so we reduce the load further by dividing
# the screen into 24 segments. Only those segments that
# have changed are scaled and blitted. If the user resizes
# the window or we get a full-screen modification, the
# entire screen is updated, bur during normal CD+G
# operation only a small number of segments are likely to
# be changed at update time.
#
# NOTE: Pygame does not currently support querying the length
# of an MP3 track, therefore the GetLength() method is not
# currently implemented.
#
# There follows a description of the important data stored by
# the class:
#
# cdgPlayer.cdgColourTable[]
# Store the colours for each colour index (0-15).
# These are set using the load colour look up table commands.
#
# cdgPlayer.cdgSurfarray[300][216]
# Surfarray object containing pixel colours for the full 300x216 screen.
# The border area is not actually displayed on the screen, however we
# need to store the pixel colours there as they are set when Scroll
# commands are used. This stores the actual pygame colour value, not
# indeces into our colour table.
#
# cdgPlayer.cdgPixelColours[300][216]
# Store the colour index for every single pixel. The values stored
# are indeces into our colour table, rather than actual pygame
# colour representations. It's unfortunate that we need to store 
# all this data, when in fact the pixel colour is available from
# cdgSurfarray, but we need it for the Tile Block XOR command.
# The XOR command performs an XOR of the colour index currently
# at the pixel, with the new colour index. We therefore need to
# know the actual colour index at that pixel - we can't do a 
# get_at() on the screen, or look in cdgSurfarray, and map the RGB
# colour back to a colour index because some CDG files have the 
# same colour in two places in the table, making it impossible to
# determine which index is relevant for the XOR.
#
# cdgPlayer.cdgPresetColourIndex 
# Preset Colour (index into colour table)
#
# cdgPlayer.cdgPresetColourIndex 
# Border Colour (index into colour table)
#
# cdgPlayer.UpdatedTiles
# Bitmask to mark which screen segments have been updated.
# This is used to reduce the amount of effort required in
# scaling the output video. This is an expensive operation
# which must be done for every screen update so we divide
# the screen into 24 segments and only update those segments
# which have actually been updated.
#
# cdgPlayer.UnscaledSurface
# All drawing is done on the unscaled surface, at 
# the standard CD+G size of 294x204. (The full CDG
# size is 300x216, but some of this is border area
# which should not be displayed to the screen.
# The border area is only on the left-hand side and
# top. i.e. it starts at offset (6,12) and carries
# on to the bottom and right edges. This is because
# it's only used for writing data into before
# scrolling in, and it therefore only needs to be on
# one edge.
#
# cdgPlayer.cdgDisplaySurface
# This is the actual surface displayed after any resize scaling.
#
# self.cdgDisplaySize
# Current actual display size. Defaults to 294x204.

import sys, Numeric as N, struct, pygame, os, string, pykversion
from threading import Thread

# Python 2.3 and newer ship with optparse; older Python releases need "Optik"
# installed (optik.sourceforge.net)
try:
	from optparse import OptionParser
except:
	import Optik as optparse

# CDG Command Code
CDG_COMMAND 			= 0x09

# CDG Instruction Codes
CDG_INST_MEMORY_PRESET		= 1
CDG_INST_BORDER_PRESET		= 2
CDG_INST_TILE_BLOCK		= 6
CDG_INST_SCROLL_PRESET		= 20
CDG_INST_SCROLL_COPY		= 24
CDG_INST_DEF_TRANSP_COL		= 28
CDG_INST_LOAD_COL_TBL_0_7	= 30
CDG_INST_LOAD_COL_TBL_8_15	= 31
CDG_INST_TILE_BLOCK_XOR		= 38

# Bitmask for all CDG fields
CDG_MASK 			= 0x3F

# States
STATE_INIT			= 1
STATE_INIT_DONE			= 2
STATE_PLAYING			= 3
STATE_PAUSED			= 4
STATE_NOT_PLAYING		= 5
STATE_CLOSING			= 6

# Display depth (bits)
DISPLAY_DEPTH       		= 0

# Delay when no CD+G packets are due (ms)
MS_DELAY			= 25

# Screen tile positions
# The viewable area of the screen (294x204) is divided into
# 24 tiles (6x4 of 49x51 each). This is used to only update
# those tiles which have changed on every screen update,
# thus reducing the CPU load of screen updates. A bitmask of
# tiles requiring update is held in cdgPlayer.UpdatedTiles.
# This stores each of the 4 columns in separate bytes, with 6 bits used
# to represent the 6 rows.
TILES_PER_ROW			= 6
TILES_PER_COL			= 4
TILE_WIDTH			= 294 / TILES_PER_ROW
TILE_HEIGHT			= 204 / TILES_PER_COL


# cdgPlayer Class
class cdgPlayer(Thread):
	# Initialise the player instace
	def __init__(self, FileName, options, errorNotifyCallback=None, doneCallback=None):
		Thread.__init__(self)
		self.FileName = FileName 

		# Get the passed options or create a new object with defaults if none passed
		if options == None:
			parser = setupOptions()
			(self.options, args) = parser.parse_args()
		else:
			self.options = options

		# Caller can register a callback by which we
		# print out error information, use stdout if none registered
		if errorNotifyCallback:
			self.ErrorNotifyCallback = errorNotifyCallback
		else:
			self.ErrorNotifyCallback = defaultErrorPrint
	
		# Caller can register a callback by which we
		# let them know when the song is finished
		if doneCallback:
			self.SongFinishedCallback = doneCallback
		else:
			self.SongFinishedCallback = None
				
		# Allow for calls through tab-completion, where we will
		# get just a '.' and not the '.cdg' extension
		if self.FileName[len(self.FileName)-1] == '.':
			self.FileName = self.FileName + 'cdg'
	
		# Check the CDG file exists
		if not os.path.isfile(self.FileName):
			ErrorString = "No such file: " + self.FileName
			self.ErrorNotifyCallback (ErrorString)
			raise NoSuchFile
			return

		# Check there is a matching mp3 or ogg file
		validexts = [
			'wav', 'wAv', 'waV', 'wAV',
			'Wav', 'WAv', 'WaV', 'WAV',
			'mp3', 'mP3', 'Mp3', 'MP3', 
			'ogg', 'oGg', 'ogG', 'oGG',
			'Ogg', 'OGg', 'OgG', 'OGG'
		]
		# With the nomusic option no music will be played.
		# Note that Pause, Rewind etc do not work in this mode.
		if self.options.nomusic == False:
			matched = 0
			for ext in validexts:
				if (os.path.isfile(self.FileName[:-3] + ext)):
					self.SoundFileName = self.FileName[:-3] + ext
					matched = 1
	
			if not matched:
				ErrorString = "There is no mp3 or ogg file to match " + self.FileName
				self.ErrorNotifyCallback (ErrorString)
				raise NoSoundFile
				return

		# Initialise the colour table. Set a default value for any
		# CDG files that don't actually load the colour table
		# before doing something with it.
		defaultColour = 0
		self.cdgColourTable = [defaultColour] * 16
		self.cdgPresetColourIndex = -1
		self.cdgBorderColourIndex = -1
		# Support only one transparent colour
		self.cdgTransparentColour = -1
		
		# Initialise the display
		self.cdgDisplaySize = (294, 204)
			
		# Build a 300x216 array for the pixel indeces, including border area
		self.cdgPixelColours = N.zeros((300,216))

		# Unscaled surface tiles
		self.unscaled_tiles = []
		for col in range(TILES_PER_COL):
			tilerow = []
			for row in range(TILES_PER_ROW):
				tilerow.append(pygame.Surface((TILE_WIDTH, TILE_HEIGHT)))
			self.unscaled_tiles.append(tilerow)

		# Start with all tiles requiring update
		self.UpdatedTiles = 0xFFFFFFFFL

		# Build a 300x216 array for the actual RGB values. This will
		# be changed by the various commands, and blitted to the
		# screen now and again. But the border area will not be
		# blitted, only the central 294x204 area.
		self.cdgSurfarray = N.zeros((300,216))

		# Handle a bug in pygame (pre-1.7) which means that the position
		# timer carries on even when the song has been paused.
		self.TotalOffsetTime = 0

		# Default display-mode resizable
		self.cdgDisplayMode = pygame.RESIZABLE | pygame.DOUBLEBUF

		# Can only do the set_mode() on Windows in the pygame thread.
		# Therefore use a variable to tell the thread when a resize
		# is required. This can then be modified by any thread calling
		# SetDisplaySize()
		self.ResizeTuple = None
		self.ResizeFullScreen = self.options.fullscreen

		# Initialise pygame
		if os.name == "posix":
			self.pygame_init()

		self.SetDisplaySize((self.options.size_x, self.options.size_y))

		# Automatically start the thread which handles pygame events
		# Doesn't actually start playing until Play() is called.
		# This can be removed when 1.7 is well spread.
		self.State = STATE_INIT
		self.start()

	# Pygame initialisation
	def pygame_init(self):
		# Fix the position at top-left of window. Note when doing this, if the
		# mouse was moving around as the window opened, it made the window tiny.
		# Have stopped doing anything for resize events until 1sec into the song
		# to work around this. Note there appears to be no way to find out the
		# current window position, in order to bring up the next window in the
		# same place. Things seem to be different in development versions of
		# pygame-1.7 - it appears to remember the position, and it is the only
		# version for which fixing the position works on MS Windows.
		# Don't set the environment variable on OSX.
		if os.name == "posix":
			(uname, host, release, version, machine) = os.uname()
		if (os.name != "posix") or (string.lower(uname)[:5] == "linux"):
			os.environ['SDL_VIDEO_WINDOW_POS'] = '%d,%d' % (self.options.pos_x, self.options.pos_y)
		pygame.mixer.pre_init(44100, -16, 2, 1024*3)
		pygame.init()
		if self.options.title:
			pygame.display.set_caption(self.options.title, 'pykaraoke')
		else:
			pygame.display.set_caption(self.FileName, 'pykaraoke')
		pygame.mouse.set_visible(False)
		self.cdgUnscaledSurface = pygame.Surface(self.cdgDisplaySize)
		self.cdgDisplaySurface = pygame.display.set_mode(self.cdgDisplaySize, self.cdgDisplayMode, DISPLAY_DEPTH)

	# Start the thread running. Blocks until the thread is started and
	# has finished initialising pygame.
	def Play(self):
		while self.State == STATE_INIT:
			pass
		if self.options.nomusic == False:
			pygame.mixer.music.play()
		self.State = STATE_PLAYING

	# Pause the song - Use Pause() again to unpause
	def Pause(self):
		if self.State == STATE_PLAYING:
			pygame.mixer.music.pause()
			self.PauseStartTime = self.GetPos()
			self.State = STATE_PAUSED
		elif self.State == STATE_PAUSED:
			self.TotalOffsetTime = self.TotalOffsetTime + (self.GetPos() - self.PauseStartTime)
			pygame.mixer.music.unpause()
			self.State = STATE_PLAYING

	# Close the whole thing down
	def Close(self):
		self.State = STATE_CLOSING

	# you must call Play() to restart. Blocks until pygame is initialised
	def Rewind(self):
		while self.State == STATE_INIT:
			pass
		# Reset the state of the packet-reading thread
		self.cdgReadPackets = 0
		self.cdgPacketsDue = 0
		self.LastPos = 0
		# No need for the Pause() fix anymore
		self.TotalOffsetTime = 0
		# Move file pointer to the beginning of the file
		self.cdgFile.seek(0)
		# Actually stop the audio
		pygame.mixer.music.rewind()
		pygame.mixer.music.stop()
		self.State = STATE_NOT_PLAYING

	# Stop the song and go back to the start. As you would
	# expect Stop to do on a CD player. Play() restarts from
	# the beginning
	def Stop(self):
		self.Rewind()
			
	# Get the song length (in seconds)
	def GetLength(self):
		ErrorString = "GetLength() not supported"
		self.ErrorNotifyCallback (ErrorString)
		return None
		
	# Get the current time (in milliseconds). Blocks if pygame is
	# not initialised yet.
	def GetPos(self):
		while self.State == STATE_INIT:
			pass
		if self.options.nomusic == False:
			return pygame.mixer.music.get_pos()
		else:
			return pygame.time.get_ticks()

	# Get the current display size
	def GetDisplaySize(self):
		return self.cdgDisplaySize

	# Set the display size. On MS Windows the actual set_mode must
	# be done in the pygame thread context, so defer it.
	def SetDisplaySize(self, displaySizeTuple):
		self.ResizeTuple = displaySizeTuple

    # Set full-screen mode. Defer to pygame thread context for MS Win.
	def SetFullScreen(self):
		self.ResizeFullScreen = True

	# Start the thread but don't play until Play() called
	def run(self):

		# It turns out that on MS Windows you have to initialise pygame in the
		# thread that is going to check for events. Therefore move all pygame
		# init stuff here. Play() will now have to block until pygame init is
		# complete.
		if os.name != "posix":
			self.pygame_init()

		# Open the cdg and sound files
		self.cdgFile = open (self.FileName, "rb") 
		if self.options.nomusic == False:
			pygame.mixer.music.load(self.SoundFileName)

		# We're now ready to accept Play() commands
		self.State = STATE_INIT_DONE
		
		# Set the CDG file at the beginning
		self.cdgReadPackets = 0
		self.cdgPacketsDue = 0
		self.LastPos = self.curr_pos = 0

		# Use psyco if possible
		try:
			import psyco
			psyco.bind(self.cdgPresetScreenCommon)
			psyco.bind(self.cdgScrollCommon)
			psyco.bind(self.cdgTileBlockCommon)
			psyco.bind(cdgLoadColourTableCommon)
			psyco.bind(cdgDisplayUpdate)
		except:
			pass

		# Main thread processing loop
		finished = False
		while (finished == False):
			finished = self.main_loop()

	def main_loop(self):
		# Check whether the songfile has moved on, if so
		# get the relevant CDG data and update the screen.
		if self.State == STATE_PLAYING:
			self.curr_pos = self.GetPos() - self.TotalOffsetTime
			if self.cdgPacketsDue <= self.cdgReadPackets:
				# Check again if any display packets are due
				self.cdgPacketsDue = (self.curr_pos / 1000.0) * 300
				pygame.time.delay(MS_DELAY)
			else:
				# A packet needs to be displayed
				packd = self.cdgGetNextPacket()
				if (packd):
					# Protect against possible corrupt rips
					try:
						self.cdgPacketProcess (packd)
					except:
						pass
					self.cdgReadPackets = self.cdgReadPackets + 1
				else:
					# Couldn't get another packet, finish
					self.Close()

		# Check if any screen updates are now due.
		if ((self.curr_pos - self.LastPos) / 1000.0) > (1.0 / self.options.fps):
			# If we fall 1/4 second behind due to high CPU activity,
			# we block any screen updates until we catch up, allowing
			# us to catch up quicker.
			if ((self.cdgPacketsDue - self.cdgReadPackets) < 75):
				self.cdgDisplayUpdate()
				self.LastPos = self.curr_pos

		# Resizes have to be done in the pygame thread context on
		# MS Windows, so other threads can set ResizeTuple to 
		# request a resize (This is wrappered by SetDisplaySize()).
		if self.ResizeTuple != None and self.GetPos() > 250:
			self.cdgDisplaySize = self.ResizeTuple
			pygame.display.set_mode (self.cdgDisplaySize, self.cdgDisplayMode, DISPLAY_DEPTH)
			self.ResizeTuple = None
			self.UpdatedTiles = 0xFFFFFFFFL
	
	        # Handle full-screen in pygame thread context
		if self.ResizeFullScreen == True:
			self.cdgDisplaySize = pygame.display.list_modes(DISPLAY_DEPTH, pygame.FULLSCREEN)[0]
			self.cdgDisplayMode = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
			pygame.display.set_mode (self.cdgDisplaySize, self.cdgDisplayMode, DISPLAY_DEPTH)
			self.ResizeFullScreen = False
			self.UpdatedTiles = 0xFFFFFFFFL

		# Check for and handle pygame events and close requests
		for event in pygame.event.get():
			# Only handle resize events 250ms into song. This is to handle the
			# bizarre problem of SDL making the window small automatically if
			# you set SDL_VIDEO_WINDOW_POS and move the mouse around while the
			# window is opening. Give it some time to settle.
			if event.type == pygame.VIDEORESIZE and self.GetPos() > 250:
				self.cdgDisplaySize = event.size
				pygame.display.set_mode (event.size, self.cdgDisplayMode, DISPLAY_DEPTH)
				self.UpdatedTiles = 0xFFFFFFFFL
			elif event.type == pygame.KEYDOWN and ((event.key == pygame.K_ESCAPE) or (event.key == pygame.K_q)):
				self.State = STATE_CLOSING
			elif event.type == pygame.QUIT:
				self.State = STATE_CLOSING
			# Use keypad -/= to offset the current graphics time by 1/4 sec
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_MINUS:
				self.TotalOffsetTime += 250
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_EQUALS:
				self.TotalOffsetTime -= 250
				
		# Common handling code for a close request or if the
		# pygame window was quit
		if self.State == STATE_CLOSING:
			self.cdgFile.close()
			pygame.quit()
			# If the caller gave us a callback, let them know we're finished
			if self.SongFinishedCallback != None:
				self.SongFinishedCallback()
			return True
		
		# Not finished
		return False

	# Decode the CDG commands read from the CDG file
	def cdgPacketProcess (self, packd):
		if (packd['command'] & CDG_MASK) == CDG_COMMAND:
			inst_code = (packd['instruction'] & CDG_MASK)
			if inst_code == CDG_INST_MEMORY_PRESET:
				self.cdgMemoryPreset (packd)
			elif inst_code == CDG_INST_BORDER_PRESET:
				self.cdgBorderPreset (packd)
			elif inst_code == CDG_INST_TILE_BLOCK:
				self.cdgTileBlockCommon (packd, xor = 0)
			elif inst_code == CDG_INST_SCROLL_PRESET:
				self.cdgScrollPreset (packd)
			elif inst_code == CDG_INST_SCROLL_COPY:
				self.cdgScrollCopy (packd)
			elif inst_code == CDG_INST_DEF_TRANSP_COL:
				self.cdgDefineTransparentColour (packd)
			elif inst_code == CDG_INST_LOAD_COL_TBL_0_7:
				self.cdgLoadColourTableCommon (packd, 0)
			elif inst_code == CDG_INST_LOAD_COL_TBL_8_15:
				self.cdgLoadColourTableCommon (packd, 1)
			elif inst_code == CDG_INST_TILE_BLOCK_XOR:
				self.cdgTileBlockCommon (packd, xor = 1)
			else:
				# Don't use the error popup, ignore the unsupported command
				ErrorString = "CDG file may be corrupt, cmd: " + str(inst_code)
				print (ErrorString)

	# Read the next CDG command from the file (24 bytes each)
	def cdgGetNextPacket (self):
		packd={}
		packet = self.cdgFile.read(24)
		if (len(packet) == 24):
			packd['command']=struct.unpack('B', packet[0])[0]
			packd['instruction']=struct.unpack('B', packet[1])[0]
			packd['parityQ']=struct.unpack('2B', packet[2:4])[0:2]
			packd['data']=struct.unpack('16B', packet[4:20])[0:16]
			packd['parity']=struct.unpack('4B', packet[20:24])[0:4]
			return packd
		else:
			return None

	# Memory preset (clear the viewable area + border)
	def cdgMemoryPreset (self, packd):
		colour = packd['data'][0] & 0x0F
		repeat = packd['data'][1] & 0x0F
		# Ignore repeat because this is a reliable data stream

		# Our new interpretation of CD+G Revealed is that memory preset
		# commands should also change the border
		self.cdgPresetColourIndex = colour
		self.cdgBorderColourIndex = self.cdgPresetColourIndex
		
		# Note that this may be done before any load colour table
		# commands by some CDGs. So the load colour table itself
		# actual recalculates the RGB values for all pixels when
		# the colour table changes.

		# Set the border colour for every pixel. Must be stored in 
		# the pixel colour table indeces array, as well as
		# the screen RGB surfarray.
		# NOTE: The preset area starts at (6,12) and extends all
		# the way to the right and bottom edges.
		
		# The most efficient way of setting the values in a Numeric
		# array, is to create a zero array and do addition on the
		# the border and preset slices.
		self.cdgPixelColours = N.zeros([300,216])
		self.cdgPixelColours[:,:12] = self.cdgPixelColours[:,:12] + self.cdgBorderColourIndex
		self.cdgPixelColours[:6,12:] = self.cdgPixelColours[:6,12:] + self.cdgBorderColourIndex
		self.cdgPixelColours[6:,12:] = self.cdgPixelColours[6:,12:] + self.cdgPresetColourIndex
		
		# Now set the border and preset colour in our local surfarray. 
		# This will be blitted next time there is a screen update.
		self.cdgSurfarray = N.zeros([300,216])
		self.cdgSurfarray[:,:12] = self.cdgSurfarray[:,:12] + self.cdgColourTable[self.cdgBorderColourIndex]
		self.cdgSurfarray[:6,12:] = self.cdgSurfarray[:6,12:] + self.cdgColourTable[self.cdgBorderColourIndex]
		self.cdgSurfarray[6:,12:] = self.cdgSurfarray[6:,12:] + self.cdgColourTable[self.cdgPresetColourIndex]

		self.UpdatedTiles = 0xFFFFFFFFL

	# Border Preset (clear the border area only) 
	def cdgBorderPreset (self, packd):
		colour = packd['data'][0] & 0x0F
		self.cdgBorderColourIndex = colour

		# See cdgMemoryPreset() for a description of what's going on.
		# In this case we are only clearing the border area.

		# Set up the border area of the pixel colours array
		self.cdgPixelColours[:,:12] = N.zeros([300,12])
		self.cdgPixelColours[:,:12] = self.cdgPixelColours[:,:12] + self.cdgBorderColourIndex
		self.cdgPixelColours[:6,12:] = N.zeros([6,216]) 
		self.cdgPixelColours[:6,12:] = self.cdgPixelColours[:6,12:] + self.cdgBorderColourIndex
		
		# Now set the border colour in our local surfarray. 
		# This will be blitted next time there is a screen update.
		self.cdgSurfarray[:,:12] = N.zeros([300,12])
		self.cdgSurfarray[:,:12] = self.cdgSurfarray[:,:12] + self.cdgColourTable[self.cdgBorderColourIndex]
		self.cdgSurfarray[:6,12:] = N.zeros([6,216])
		self.cdgSurfarray[:6,12:] = self.cdgSurfarray[:6,12:] + self.cdgColourTable[self.cdgBorderColourIndex]

		return

	# CDG Scroll Command - Set the scrolled in area with a fresh colour
	def cdgScrollPreset (self, packd):
		self.cdgScrollCommon (packd, copy = False)
		return

	# CDG Scroll Command - Wrap the scrolled out area into the opposite side
	def cdgScrollCopy (self, packd):
		self.cdgScrollCommon (packd, copy = True)
		return

	# Common function to handle the actual pixel scroll for Copy and Preset
	def cdgScrollCommon (self, packd, copy):

		# Decode the scroll command parameters
		data_block = packd['data']
		colour = data_block[0] & 0x0F
		hScroll = data_block[1] & 0x3F
		vScroll = data_block[2] & 0x3F
		hSCmd = (hScroll & 0x30) >> 4
		hOffset = (hScroll & 0x07)
		vSCmd = (vScroll & 0x30) >> 4
		vOffset = (vScroll & 0x0F)

		# Scroll Vertical - Calculate number of pixels
		vScrollUpPixels = 0
		vScrollDownPixels = 0
		if (vSCmd == 2 and vOffset == 0):
			vScrollUpPixels = 12
		elif (vSCmd == 2):
			vScrollUpPixels = vOffset
		elif (vSCmd == 1 and vOffset == 0):
			vScrollDownPixels = 12
		elif (vSCmd == 1):
			vScrollDownPixels = vOffset

		# Scroll Horizontal- Calculate number of pixels
		hScrollLeftPixels = 0
		hScrollRightPixels = 0
		if (hSCmd == 2 and hOffset == 0):
			hScrollRightPixels = 6
		elif (hSCmd == 2):
			hScrollRightPixels = hOffset
		elif (hSCmd == 1 and hOffset == 0):
			hScrollLeftPixels = 6
		elif (hSCmd == 1):
			hScrollLeftPixels = hOffset

		# Perform the actual scroll. Use surfarray and slicing to make
		# this efficient. A copy scroll (where the data scrolls round)
		# can be achieved by slicing and concatenating again.
		# For non-copy, the new slice is filled in with a new colour.
		# NOTE: Only Vertical Scroll with Copy has been tested as no 
		# CDGs were available with horizontal scrolling or Scroll Preset.
		if (copy == True):
			if (vScrollUpPixels > 0):
				self.cdgSurfarray = N.concatenate((self.cdgSurfarray[:,vScrollUpPixels:], self.cdgSurfarray[:,:vScrollUpPixels]), 1)
				self.cdgPixelColours = N.concatenate((self.cdgPixelColours[:,vScrollUpPixels:], self.cdgPixelColours[:,:vScrollUpPixels]), 1)
			elif (vScrollDownPixels > 0):
				self.cdgSurfarray = N.concatenate((self.cdgSurfarray[:,-vScrollDownPixels:], self.cdgSurfarray[:,:-vScrollDownPixels]), 1)
				self.cdgPixelColours = N.concatenate((self.cdgPixelColours[:,-vScrollDownPixels:], self.cdgPixelColours[:,:-vScrollDownPixels]), 1)
			elif (hScrollLeftPixels > 0):
				self.cdgSurfarray = N.concatenate((self.cdgSurfarray[hScrollLeftPixels:,:], self.cdgSurfarray[:hScrollLeftPixels,:]), 0)
				self.cdgPixelColours = N.concatenate((self.cdgPixelColours[hScrollLeftPixels:,:], self.cdgPixelColours[:hScrollLeftPixels,:]), 0)
			elif (hScrollRightPixels > 0):
				self.cdgSurfarray = N.concatenate((self.cdgSurfarray[-hScrollRightPixels:,:], self.cdgSurfarray[:-hScrollRightPixels,:]), 0)
				self.cdgPixelColours = N.concatenate((self.cdgPixelColours[-hScrollRightPixels:,:], self.cdgPixelColours[:-hScrollRightPixels,:]), 0)
		elif (copy == False):
			if (vScrollUpPixels > 0):
				copyBlockActualColour = N.zeros([300,vScrollUpPixels]) + self.cdgColourTable[colour]
				copyBlockColourIndex = N.zeros([300,vScrollUpPixels]) + colour
				self.cdgSurfarray = N.concatenate((self.cdgSurfarray[:,vScrollUpPixels:], copyBlockActualColour), 1)
				self.cdgPixelColours = N.concatenate((self.cdgPixelColours[:,vScrollUpPixels:], copyBlockColourIndex), 1)
			elif (vScrollDownPixels > 0):
				copyBlockActualColour = N.zeros([300,vScrollDownPixels]) + self.cdgColourTable[colour]
				copyBlockColourIndex = N.zeros([300,vScrollDownPixels]) + colour
				self.cdgSurfarray = N.concatenate((copyBlockActualColour, self.cdgSurfarray[:,:-vScrollDownPixels]), 1)
				self.cdgPixelColours = N.concatenate((copyBlockColourIndex, self.cdgPixelColours[:,:-vScrollDownPixels]), 1)
			elif (hScrollLeftPixels > 0):
				copyBlockActualColour = N.zeros([hScrollLeftPixels, 216]) + self.cdgColourTable[colour]
				copyBlockColourIndex = N.zeros([hScrollLeftPixels, 216]) + colour
				self.cdgSurfarray = N.concatenate((self.cdgSurfarray[hScrollLeftPixels:,:], copyBlockActualColour), 0)
				self.cdgPixelColours = N.concatenate((self.cdgPixelColours[hScrollLeftPixels:,:], copyBlockColourIndex), 0)
			elif (hScrollRightPixels > 0):
				copyBlockActualColour = N.zeros([hScrollRightPixels, 216]) + self.cdgColourTable[colour]
				copyBlockColourIndex = N.zeros([hScrollRightPixels, 216]) + colour
				self.cdgSurfarray = N.concatenate((copyBlockActualColour, self.cdgSurfarray[:-hScrollRightPixels,:]), 0)
				self.cdgPixelColours = N.concatenate((copyBlockColourIndex, self.cdgPixelColours[:-hScrollRightPixels,:]), 0)
		
		# We have modified our local cdgSurfarray. This will be blitted to
		# the screen by cdgDisplayUpdate()
		self.UpdatedTiles = 0xFFFFFFFFL
	
	# Set the colours for a 12x6 tile. The main CDG command for display data
	def cdgTileBlockCommon (self, packd, xor):
		# Decode the command parameters
		data_block = packd['data']
		colour0 = data_block[0] & 0x0F
		colour1 = data_block[1] & 0x0F
		column_index = ((data_block[2] & 0x1F) * 12)
		row_index = ((data_block[3] & 0x3F) * 6)
	
		# Set the tile update bitmasks.
		# Note that the screen update area only covers the non-border area
		# excluding the left 6 columns, and top 12 rows. Therefore when
		# calculating whether this block fits into a particular tile, we
		# add 6 or 12 to the x,y positions. Note also that each tile is 6
		# wide and 12 high, so if a block starts less than 6 columns to the
		# left of a block, it will incorporate the adjacent block. Similarly
		# any update starting less than 12 rows above a block, will also
		# incorporate the block below.
		for col in range(TILES_PER_COL):
			for row in range(TILES_PER_ROW):
				if ((row_index >= (TILE_WIDTH * row)) \
					and (row_index <= 6 + (TILE_WIDTH * (row + 1))) \
					and (column_index >= (TILE_HEIGHT * col)) \
					and (column_index <= 12 + (TILE_HEIGHT * (col + 1)))):
					self.UpdatedTiles |= ((1 << row) << (col * 8))
	
		# Set the pixel array for each of the pixels in the 12x6 tile.
		# Normal = Set the colour to either colour0 or colour1 depending
		#          on whether the pixel value is 0 or 1.
		# XOR    = XOR the colour with the colour index currently there.
		for i in range (12):
			byte = (data_block[4 + i] & 0x3F)
			for j in range (6):
				pixel = (byte >> (5 - j)) & 0x01
				if xor == 1:
					# Tile Block XOR
					if (pixel == 0):
						xor_col = colour0
					else:
						xor_col = colour1
					# Get the colour index currently at this location, and xor with it
					currentColourIndex = self.cdgPixelColours[(row_index + j), (column_index + i)]
					new_col = currentColourIndex ^ xor_col
				else:
					# Tile Block Normal
					if (pixel == 0):
						new_col = colour0
					else:
						new_col = colour1
				# Set the pixel with the new colour. We set both the surfarray
				# containing actual RGB values, as well as our array containing
				# the colour indeces into our colour table.
				self.cdgSurfarray[(row_index + j), (column_index + i)] = self.cdgColourTable[new_col]
				self.cdgPixelColours[(row_index + j), (column_index + i)] = new_col
		# The changes to cdgSurfarray will be blitted on the next screen update
		return

	# Set one of the colour indeces as transparent. Don't actually do anything with this
	# at the moment, as there is currently no mechanism for overlaying onto a movie file.
	def cdgDefineTransparentColour (self, packd):
		data_block = packd['data']
		colour = data_block[0] & 0x0F
		self.cdgTransparentColour = colour
		return

	# Load the RGB value for colours 0..7 or 8..15 in the lookup table
	def cdgLoadColourTableCommon (self, packd, table):

		# Need to do this so that cdgUnscaledSurface is ready now that we don't
		# update it in the screen update. Should use the segment surfarrays instead though,
		# to save this call.
		pygame.surfarray.blit_array(self.cdgUnscaledSurface, self.cdgSurfarray[6:,12:])

		if table == 0:
			colourTableStart = 0
		else:
			colourTableStart = 8
		for i in range(8):
			colourEntry = ((packd['data'][2 * i] & CDG_MASK) << 8)
			colourEntry = colourEntry + (packd['data'][(2 * i) + 1] & CDG_MASK)
			colourEntry = ((colourEntry & 0x3F00) >> 2) | (colourEntry & 0x003F)
			red = ((colourEntry & 0x0F00) >> 8) * 17
			green = ((colourEntry & 0x00F0) >> 4) * 17
			blue = ((colourEntry & 0x000F)) * 17
			self.cdgColourTable[i + colourTableStart] = self.cdgUnscaledSurface.map_rgb(red, green, blue)
		# Redraw the entire screen using the new colour table. We still use the 
		# same colour indeces (0 to 15) at each pixel but these may translate to
		# new RGB colours. This handles CDGs that preset the screen before actually
		# loading the colour table. It is done in our local RGB surfarray.

		# Do this with the Numeric module operation take() which can replace all
		# values in an array by alternatives from a lookup table. This is ideal as
		# we already have an array of colour indeces (0 to 15). We can create a
		# new RGB surfarray from that by doing take() which translates the 0-15
		# into an RGB colour and stores them in the RGB surfarray.
		lookupTable = N.array(self.cdgColourTable)
		self.cdgSurfarray.flat[:] = N.take(lookupTable, self.cdgPixelColours.flat)

		# An alternative way of doing the above - was found to be very slightly slower.
		#self.cdgSurfarray.flat[:] =  map(self.cdgColourTable.__getitem__, self.cdgPixelColours.flat)

		# Update the screen for any colour changes
		self.UpdatedTiles = 0xFFFFFFFFL
		return

	# Actually update/refresh the video output
	def cdgDisplayUpdate(self):
		# This routine is responsible for taking the unscaled
		# output pixel data from self.cdgSurfarray, scaling it
		# and blitting it to the actual display surface. The
		# viewable area of the unscaled surface is 294x204 pixels.
		# Because scaling and blitting are heavy operations, we
		# divide the screen into 24 tiles, and only scale and blit
		# those tiles which have been updated recently. Any
		# routines which wish to modify the display set the
		# relevant bitmask in self.UpdatedTiles to notify us which
		# tiles need to be updated to the screen.

		# List of update rectangles (in scaled output window)
		rect_list = []

		# Calculate the scaled width and height for each tile
		scaled_width = self.cdgDisplaySize[0] / TILES_PER_ROW
		scaled_height = self.cdgDisplaySize[1] / TILES_PER_COL

		# Scale and blit only those tiles which have been updated	
		for col in range(TILES_PER_COL):
			for row in range(TILES_PER_ROW):
				if (self.UpdatedTiles & ((1 << row) << (col * 8))):
					# Calculate the row & column starts/ends
					row_start = 6 + (row * TILE_WIDTH)
					row_end = 6 + ((row + 1) * TILE_WIDTH)
					col_start = 12 + (col * TILE_HEIGHT)
					col_end = 12 + ((col + 1) * TILE_HEIGHT)
					pygame.surfarray.blit_array( \
						self.unscaled_tiles[col][row], \
						self.cdgSurfarray[row_start:row_end,col_start:col_end]) 
					scaled = pygame.transform.scale(self.unscaled_tiles[col][row], (scaled_width,scaled_height))
					self.cdgDisplaySurface.blit (scaled, (scaled_width * row, scaled_height * col))
					rect_list.append(pygame.Rect(scaled_width * row, scaled_height * col, scaled_width, scaled_height))
					
		# No tiles need updating now
		self.UpdatedTiles = 0

		# Only update those areas which have changed
		pygame.display.update(rect_list)

def defaultErrorPrint(ErrorString):
	print (ErrorString)

# Initialise an optparse options object
def setupOptions():
	usage = "usage: %prog [options] <CDG file>"
	version = "%prog " + pykversion.PYKARAOKE_VERSION_STRING
	parser = OptionParser(usage = usage, version = version, conflict_handler = "resolve")
	parser.add_option('-x', '--window-x', dest = 'pos_x', type = 'int', metavar='X',
		help = 'position CD+G window X pixels from the left edge of the screen', default = 0)
	parser.add_option('-y', '--window-y', dest = 'pos_y', type = 'int', metavar='Y',
		help = 'position CD+G window Y pixels from the top edge of the screen', default = 0)
	parser.add_option('-w', '--width', dest = 'size_x', type = 'int', metavar='X',
		help = 'draw CD+G window X pixels wide', default = 294)
	parser.add_option('-h', '--height', dest = 'size_y', type = 'int', metavar='Y',
		help = 'draw CD+G window Y pixels high', default = 204)
	parser.add_option('-t', '--title', dest = 'title', type = 'string', metavar='TITLE',
		help = 'set window title to TITLE', default = '')
	parser.add_option('-f', '--fullscreen', dest = 'fullscreen', action = 'store_true', 
		help = 'draw CD+G window fullscreen', default = False)
	parser.add_option('-s', '--fps', dest = 'fps', metavar='N', type = 'int',
		help = 'draw updates at up to N frames per second (be careful; setting this value too high can consume excessive CPU time)', default = 10)
	parser.add_option('-n', '--nomusic', dest = 'nomusic', action = 'store_true',
		help = 'disable music playback, just display graphics', default = False)
	return parser

# Can be called from the command line with the CDG filepath as parameter
def main():

	# Parse the command-line options
	parser = setupOptions()
	(options, args) = parser.parse_args()
	if (not len(args)):
		parser.print_help()
		sys.exit(2)

	cdgFileName = args[0]
	player = cdgPlayer(cdgFileName, options)
	player.Play()

if __name__ == "__main__":
    sys.exit(main())
