#!/usr/bin/env python

# pykar - KAR/MID Karaoke Player
#
# Copyright (C) 2005  Kelvin Lawson (kelvinl@users.sf.net)
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
# pykar is a MIDI/KAR karaoke player built using python. It was written for
# the PyKaraoke project but is in fact a general purpose KAR player that
# could be used in other python projects requiring a KAR player.
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
# KAR support, this module has been designed to be easily incorporated
# into such projects and is released under the LGPL.


# REQUIREMENTS
#
# pycdg requires the following to be installed on your system:
# . Python (www.python.org)
# . Pygame (www.pygame.org)
# . Numeric module (numpy.sourceforge.net)


# LINUX REQUIREMENTS
#
# To play the MIDI songs on Linux, Timidity++ is also required:
# . Timidity++ (timidity.sourceforge.net)


# USAGE INSTRUCTIONS
#
# To start the player, pass the KAR filename/path on the command line:
# 		python pykar.py /songs/theboxer.kar
#
# You can also incorporate a KAR player in your own projects by
# importing this module. The class midPlayer is exported by the
# module. You can import and start it as follows:
#	import pykar
#	player = pykar.midPlayer("/songs/theboxer.kar")
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
# 	midPlayer ("/songs/theboxer.kar", errorPopup, songFinishedCallback)
# These parameters are optional and default to None.
#
# If the initialiser fails (e.g. the song file is not present), __init__
# raises an exception.


# IMPLEMENTATION DETAILS
#
# pykar is implemented as one python module. Pygame provides support
# for playing MIDI files, so playing a MIDI song using Pygame is
# very easy. However, in order to find the lyrics from the MIDI file
# it was necessary to write a basic parser that understands the MIDI
# file format. This opens the MIDI file and reads all tracks, pulling
# out the lyric text and times. After this first parse of the MIDI
# file, this module does not do any more MIDI decoding for playing
# purposes - Pygame takes care of all actual music generation.
#
# There is an extra complication on Linux which is that the MIDI
# support (provided by Timidity++) reports the current song time 
# using the first note being played as the start. However on Windows
# the Pygame MIDI player returns the time from the start of the actual 
# song (even if there is no sound for a few seconds). This meant that
# for Linux systems, it was necessary to parse the whole MIDI file and
# calculate the time of the first note from all tracks. This is then
# used as an offset in the calculation of when to display the lyrics.
#
# The player is run within a thread to allow for easy
# integration with media player programs. Once the KAR lyrics graphic
# window is opened, it monitors for Rewind etc commands, and handles 
# resize and close window events.


import pygame, sys, os, struct, string
from threading import Thread
import Numeric as N
import pygame.surfarray as surfarray

# Left and top margins
Y_BORDER = 20
X_BORDER = 20

# Font size
FONT_SIZE = 19

# Inter-line gap
LINE_GAP = 10

# Unscaled screen size
UNSCALED_WIDTH = 640
UNSCALED_HEIGHT = 2 * (Y_BORDER) + 6 * (FONT_SIZE + LINE_GAP)

# States
STATE_INIT			= 1
STATE_INIT_DONE		= 2
STATE_PLAYING		= 3
STATE_PAUSED		= 4
STATE_NOT_PLAYING	= 5
STATE_CLOSING		= 6

# Screen updates per second
SCREEN_UPDATES_PER_SEC = 10

# Debug out MIDI messages as text
debug = False

class midiFile:
	def __init__(self):
		self.trackList = []			# List of TrackDesc track descriptors
		self.text_events = []		# Lyrics (0x1 events) (list of delta and lyric text tuples)
		self.lyric_events = []		# Lyrics (0x5 events) (list of delta and lyric text tuples)
		self.lyrics = []			# Chosen lyric list from above
		self.DeltaUnitsPerSMPTE = None
		self.SMPTEFramesPerSec = None
		self.DeltaUnitsPerQuarter = None
		self.Tempo = None
		self.Numerator = None				# Numerator
		self.Denominator = None				# Denominator
		self.ClocksPerMetronomeTick = None	# MIDI clocks per metronome tick
		self.NotesPer24MIDIClocks = None	# 1/32 Notes per 24 MIDI clocks
		self.earliestNoteMS = 0				# Delta of earliest note in song
		

class TrackDesc:
	def __init__(self, trackNum):
		self.TrackNum = trackNum		# Track number
		self.TotalDeltasFromStart = 0	# Store current delta from start
		self.BytesRead = 0				# Number of file bytes read for track
		self.FirstNoteDelta = -1		# Delta for first note in track
		self.LyricsTrack = False		# This track contains lyrics
		self.RunningStatus = 0			# MIDI Running Status byte

		
def midiParseFile (filename, ErrorNotifyCallback):
	
	# Create the midiFile structure
	midifile = midiFile()

	# Check the MID/KAR file exists
	if not os.path.isfile(filename):
		ErrorNotifyCallback ("No such file: " % filename)
		return None
	
	# Open the file
	filehdl = open (filename, "rb") 

	# Check it's a MThd chunk
	packet = filehdl.read(8)
	ChunkType = packet[0:4]
	Length = struct.unpack('>L', packet[4:8])[0]
	if (ChunkType != "MThd"):
		ErrorNotifyCallback ("No MIDI Header chunk at start")
		return None

	# Read header
	packet = filehdl.read(Length)
	format = struct.unpack('>H', packet[0:2])[0]
	tracks = struct.unpack('>H', packet[2:4])[0]
	division = struct.unpack('>H', packet[4:6])[0]
	if (division & 0x8000):
		midifile.DeltaUnitsPerSMPTE = division & 0x00FF
		midifile.SMPTEFramesPerSec = division & 0x7F00
	else:
		midifile.DeltaUnitsPerQuarter = division & 0x7FFF

	# Loop through parsing all tracks
	trackBytes = 1
	trackNum = 0
	while (trackBytes != 0):
		# Read the next track header
		packet = filehdl.read(8)
		if packet == "" or len(packet) < 8:
			# End of file, we're leaving
			break
		# Check it's a MTrk
		ChunkType = packet[0:4]
		Length = struct.unpack('>L', packet[4:8])[0]
		if (ChunkType != "MTrk"):
			print ("Didn't find expected MIDI Track")
		# Process the track, getting a TrackDesc structure
		track_desc = midiParseTrack(filehdl, midifile, trackNum, Length, ErrorNotifyCallback)
		if track_desc:
			trackBytes = track_desc.BytesRead
			trackNum = trackNum + 1
			# Store the track descriptor with the others
			midifile.trackList.append(track_desc)
			# Debug out the first note for this track
			#time_ms = getTimeMSForDelta(midifile, track_desc.FirstNoteDelta)
			#print ("T%d: First note(%d) %d" % (trackNum, track_desc.FirstNoteDelta, time_ms))

	# Close the open file
	filehdl.close()

	# Calculate the song start delta (earliest note event in all tracks)
	earliestNoteMS = None
	for track in midifile.trackList:
		time_ms = getTimeMSForDelta(midifile, track.FirstNoteDelta)
		if (time_ms >= 0):
			if (time_ms < earliestNoteMS) or (earliestNoteMS == None):
				earliestNoteMS = time_ms
	midifile.earliestNoteMS = earliestNoteMS

	# Windows reports the song time correctly (including period up to the
	# first note), so no need for the earliest note hack.
	if os.name != "posix":
		midifile.earliestNoteMS = 0

	# Decide which list of lyric events to choose. There may be text events (0x01),
	# lyric events (0x05) or sometimes both for compatibility. If both are
	# available, we choose text events.
	if midifile.text_events and midifile.lyric_events:
		midifile.lyrics = midifile.text_events
	elif midifile.text_events:
		midifile.lyrics = midifile.text_events
	elif midifile.lyric_events:
		midifile.lyrics = midifile.lyric_events
	else:
		ErrorNotifyCallback ("No lyrics in the track")
		return None

	# Sort the events in delta order
	midifile.lyrics.sort()

	# Return the populated midiFile structure
	return midifile
	
	
def midiParseTrack (filehdl, midifile, trackNum, Length, ErrorNotifyCallback):
	# Create the new TrackDesc structure
	track = TrackDesc(trackNum)
	if debug:
		print "Track %d" % trackNum
	# Loop through all events in the track, recording salient meta-events and times
	eventBytes = 0
	while track.BytesRead < Length:
		eventBytes = midiProcessEvent (filehdl, track, midifile, ErrorNotifyCallback)
		if (eventBytes == None) or (eventBytes == -1) or (eventBytes == 0):
			return None
		track.BytesRead = track.BytesRead + eventBytes
	return track


def midiProcessEvent (filehdl, track_desc, midifile, ErrorNotifyCallback):
	bytesRead = 0
	running_status = 0
	delta, varBytes = varLength(filehdl)
	if varBytes == 0:
		return 0
	bytesRead = bytesRead + varBytes
	track_desc.TotalDeltasFromStart = track_desc.TotalDeltasFromStart + delta
	byteStr = filehdl.read(1)
	bytesRead = bytesRead + 1
	status_byte = struct.unpack('B', byteStr[0])[0]
	
	# Handle the MIDI running status. This allows consecutive
	# commands of the same event type to not bother sending
	# the event type again. If the top bit isn't set it's a
	# data byte using the last event type.
	if (status_byte & 0x80):
		# This is a new status byte, not a data byte using
		# the running status. Set the current running status
		# to this new status byte and use it as the event type.
		event_type = status_byte
		# Only save running status for voice messages
		if (event_type & 0xF0) != 0xF0:
			track_desc.RunningStatus = event_type

	else:
		# Use the last event type, and seek back in the file
		# as this byte is actual data, not an event code
		event_type = track_desc.RunningStatus
		filehdl.seek (-1, 1)
		bytesRead = bytesRead - 1
	
	#print ("T%d: VarBytes = %d, event_type = 0x%X" % (track_desc.TrackNum, varBytes, event_type))
	if debug:
		print "Event: 0x%X" % event_type

	# Handle all event types
	if event_type == 0xFF:
		byteStr = filehdl.read(1)
		bytesRead = bytesRead + 1
		event = struct.unpack('B', byteStr[0])[0]
		if debug:
			print "MetaEvent: 0x%X" % event
		if event == 0x00:
			# Sequence number (discarded)
			packet = filehdl.read(2)
			bytesRead = bytesRead + 2
			zero, type = struct.unpack('2B', packet[0:2])
			if type == 0x02:
				# Discard next two bytes as well
				discard = filehdl.read(2)
			elif type == 0x00:
				# Nothing left to discard
				pass
			else:
				print ("Invalid sequence number (%d)" % type)
		elif event == 0x01:
			# Text Event
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			text = filehdl.read(Length)
			bytesRead = bytesRead + Length
			# Take out any Sysex text events, and append to the lyrics list
			if (" SYX" not in text) and ("Track-" not in text) \
				and ("%-" not in text) and ("%+" not in text):
				midifile.text_events.append((track_desc.TotalDeltasFromStart, text))
			if debug:
				print ("Text: %s (len %d)" % (text, Length))
		elif event == 0x02:
			# Copyright (discard)
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			discard = filehdl.read(Length)
			bytesRead = bytesRead + Length
		elif event == 0x03:
			# Title of track
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			title = filehdl.read(Length)
			bytesRead = bytesRead + Length
			if debug:
				print ("Track Title: " + title)			
			if title == "Words":
				track_desc.LyricsTrack = True
		elif event == 0x04:
			# Instrument (discard)
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			discard = filehdl.read(Length)
			bytesRead = bytesRead + Length
		elif event == 0x05:
			# Lyric Event (discard, seems to duplicate the text)
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			lyric = filehdl.read(Length)
			bytesRead = bytesRead + Length
			# Take out any Sysex text events, and append to the lyrics list
			if (" SYX" not in lyric) and ("Track-" not in lyric) \
				and ("%-" not in lyric) and ("%+" not in lyric):
				midifile.lyric_events.append((track_desc.TotalDeltasFromStart, lyric))
			if debug:
				print ("Lyric: %s (len %d)" % (lyric, Length))
		elif event == 0x06:
			# Marker (discard)
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			discard = filehdl.read(Length)
			bytesRead = bytesRead + Length
		elif event == 0x07:
			# Cue point (discard)
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			discard = filehdl.read(Length)
			bytesRead = bytesRead + Length
		elif event == 0x08:
			# Program name (discard)
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			discard = filehdl.read(Length)
			bytesRead = bytesRead + Length
		elif event == 0x09:
			# Device (port) name (discard)
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			discard = filehdl.read(Length)
			bytesRead = bytesRead + Length
		elif event == 0x20:
			# MIDI Channel (discard)
			packet = filehdl.read(2)
			bytesRead = bytesRead + 2
		elif event == 0x21:
			# MIDI Port (discard)
			packet = filehdl.read(2)
			bytesRead = bytesRead + 2
		elif event == 0x2F:
			# End of track
			byteStr = filehdl.read(1)
			bytesRead = bytesRead + 1
			valid = struct.unpack('B', byteStr[0])[0]
			if valid != 0:
				print ("Invalid End of track")
		elif event == 0x51:
			# Set Tempo
			packet = filehdl.read(4)
			bytesRead = bytesRead + 4
			valid, tempoA, tempoB, tempoC = struct.unpack('4B', packet[0:4])
			if valid != 0x03:
				print ("Error: Invalid tempo")
			midifile.Tempo = (tempoA << 16) | (tempoB << 8) | tempoC
			if debug:
				ms_per_quarter = (midifile.Tempo/1000)
				print ("Tempo: %d (%d ms per quarter note)"% (midifile.Tempo, ms_per_quarter))
		elif event == 0x54:
			# SMPTE (discard)
			packet = filehdl.read(6)
			bytesRead = bytesRead + 6
		elif event == 0x58:
			# Meta Event: Time Signature
			packet = filehdl.read(5)
			bytesRead = bytesRead + 5
			valid, num, denom, clocks, notes = struct.unpack('BBBBB', packet[0:5])
			if valid != 0x04:
				print ("Error: Invalid time signature (valid=%d, num=%d, denom=%d)" % (valid,num,denom))
			midifile.Numerator = num
			midifile.Denominator = denom
			midifile.ClocksPerMetronomeTick = clocks
			midifile.NotesPer24MIDIClocks = notes
		elif event == 0x59:
			# Key signature (discard)
			packet = filehdl.read(3)
			bytesRead = bytesRead + 3
			valid, sf, mi = struct.unpack('3B', packet[0:3])
			if valid != 0x02:
				print ("Error: Invalid key signature (valid=%d, sf=%d, mi=%d)" % (valid,sf,mi))
		elif event == 0x7F:
			# Sequencer Specific Meta Event
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			byteStr = filehdl.read(1)
			bytesRead = bytesRead + 1
			ID = struct.unpack('B', byteStr[0])[0]
			if ID == 0:
				packet = filehdl.read(2)
				bytesRead = bytesRead + 2
				ID = struct.unpack('>H', packet[0:2])[0]
				Length = Length - 3
			else:
				Length = Length - 1
			data = filehdl.read(Length)
			bytesRead = bytesRead + Length
			if debug:
				print ("Sequencer Specific Event (Data Length %d)"%Length)
				print ("Manufacturer's ID: " + str(ID))
				print ("Manufacturer Data: " + data)
		else:
			# Unknown event (discard)
			print ("Unknown meta-event: 0x%X" % event)
			Length, varBytes = varLength(filehdl)
			bytesRead = bytesRead + varBytes
			discard = filehdl.read(Length)
			bytesRead = bytesRead + Length

	elif (event_type & 0xF0) == 0x80:
		# Note off (discard)
		packet = filehdl.read(2)
		bytesRead = bytesRead + 2
	elif (event_type & 0xF0) == 0x90:
		# Note on (discard but note if the start time of the first in the track)
		packet = filehdl.read(2)
		bytesRead = bytesRead + 2
		#time_ms = getTimeMSForDelta(midifile, track_desc.TotalDeltasFromStart)
		#print ("T%d: 0x%X (%dms)" % (track_desc.TrackNum, event_type, time_ms))
		if track_desc.FirstNoteDelta == -1:
			track_desc.FirstNoteDelta = track_desc.TotalDeltasFromStart
	elif (event_type & 0xF0) == 0xA0:
		# Key after-touch (discard)
		packet = filehdl.read(2)
		bytesRead = bytesRead + 2
	elif (event_type & 0xF0) == 0xB0:
		# Control change (discard)
		packet = filehdl.read(2)
		bytesRead = bytesRead + 2
		if debug:
			c, v = struct.unpack('2B', packet[0:2])
			print ("Control: C%d V%d" % (c,v))
	elif (event_type & 0xF0) == 0xC0:
		# Program (patch) change (discard)
		packet = filehdl.read(1)
		bytesRead = bytesRead + 1
	elif (event_type & 0xF0) == 0xD0:
		# Channel after-touch (discard)
		packet = filehdl.read(1)
		bytesRead = bytesRead + 1
	elif (event_type & 0xF0) == 0xE0:
		# Pitch wheel change (discard)
		packet = filehdl.read(2)
		bytesRead = bytesRead + 2
	elif event_type == 0xF0:
		# F0 Sysex Event (discard)
		Length, varBytes = varLength(filehdl)
		bytesRead = bytesRead + varBytes
		discard = filehdl.read(Length - 1)
		end_byte = filehdl.read(1)
		end = struct.unpack('B', end_byte[0:1])
		bytesRead = bytesRead + Length
		if (end != 0xF7):
			print ("Invalid F0 Sysex end byte (0x%X)" % end)
	elif event_type == 0xF7:
		# F7 Sysex Event (discard)
		Length, varBytes = varLength(filehdl)
		bytesRead = bytesRead + varBytes
		discard = filehdl.read(Length)
		bytesRead = bytesRead + Length
	else:
		# Unknown event (discard)
		print ("Unknown event: 0x%x" % event_type)
		Length, varBytes = varLength(filehdl)
		bytesRead = bytesRead + varBytes
		discard = filehdl.read(Length)
		bytesRead = bytesRead + Length
	return bytesRead


def getTimeMSForDelta (midifile, delta):
	microseconds = ( ( float(delta) / midifile.DeltaUnitsPerQuarter ) * midifile.Tempo );
	time_ms = microseconds / 1000
	return (time_ms)


# Read a variable length quantity from the file's current read position.
# Reads the file one byte at a time until the full value has been read,
# and returns a tuple of the full integer and the number of bytes read
def varLength(filehdl):
	convertedInt = 0
	bitShift = 0
	bytesRead = 0
	while (bitShift <= 42):
		byteStr = filehdl.read(1)
		bytesRead = bytesRead + 1
		if byteStr:
			byteVal = struct.unpack('B', byteStr[0])[0]
			convertedInt = (convertedInt << 7) | (byteVal & 0x7F)
			#print ("<0x%X/0x%X>"% (byteVal, convertedInt))
			if (byteVal & 0x80):
				bitShift = bitShift + 7
			else:
				break
		else:
			return (0, 0)
	return (convertedInt, bytesRead)


def displayWrite(screen,font,t,x,y,color=(255,255,255)):
	"""return width of the text written"""
	txt = font.render(t,True,color)
	w,h = txt.get_size()
	screen.blit(txt,(x,y,w,h))
	return (x+w), y


class midPlayer(Thread):
	def __init__(self, midFileName, errorNotifyCallback=None, doneCallback=None):
		Thread.__init__(self)

		# Store the parameter
		self.FileName = midFileName
		
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

		# Parse the MIDI file
		self.midifile = midiParseFile (self.FileName, self.ErrorNotifyCallback)
		if (self.midifile == None):
			ErrorString = "ERROR: Could not parse the MIDI file"
			self.ErrorNotifyCallback (ErrorString)
			return
		elif (self.midifile.lyrics == None):	
			ErrorString = "ERROR: Could not get any lyric data from file"
			self.ErrorNotifyCallback (ErrorString)
			return

		# Debug out the found lyrics
		if debug:
			for lyric in self.midifile.lyrics:
				print lyric

		# Set the default display size. Height is 6 lines with gap plus top and
		# bottom borders. Width is a finger-in-the-air 640.
		self.displaySize = (UNSCALED_WIDTH, UNSCALED_HEIGHT)
			
		# Can only do the set_mode() on Windows in the pygame thread.
		# Therefore use a variable to tell the thread when a resize
		# is required. This can then be modified by any thread calling
		# SetDisplaySize()
		self.ResizeTuple = None

		# Initialise pygame
		if os.name == "posix":
			self.pygame_init()

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
			os.environ['SDL_VIDEO_WINDOW_POS'] = "30,30"
		pygame.init()
		pygame.display.set_caption(self.FileName)
		self.unscaledSurface = pygame.Surface(self.displaySize)
		self.displaySurface = pygame.display.set_mode(self.displaySize, pygame.RESIZABLE, 16)
		# Find the correct font path. If fully installed on Linux this
		# will be sys.prefix/share/pykaraoke/fonts. Otherwise look for
		# it in the current directory.
		if (os.path.isfile("fonts/vera.ttf")):
			fontspath = "fonts"
		else:
			fontspath = os.path.join(sys.prefix, "share/pykaraoke/fonts")
		self.font=pygame.font.Font(os.path.join(fontspath, "vera.ttf"), FONT_SIZE)

	def resetPlayingState(self):
	
		# Set the state variables

		# Last update position
		self.LastPos = 0
		# Current x,y position of displayed lyrics
		self.displayed_x, self.displayed_y = X_BORDER, Y_BORDER
		# Current x,y position of synced colour change
		self.coloured_x, self.coloured_y = X_BORDER, Y_BORDER
		# Indeces into lyrics array of displayed lyric and colour-changed lyric
		self.displayed_index, self.coloured_index = 0, 0
		# Blank-line carry flag
		self.blank_carry = False
		# \r carry flag
		self.slashr_carry = False

		# Clear the screen
		self.unscaledSurface.fill((0,0,0))
		
		# Paint the first 6 lines
		for i in range(6):
			self.displayNextLine()
	
	# Start the thread running. Blocks until the thread is started and
	# has finished initialising pygame.
	def Play(self):
		while self.State == STATE_INIT:
			pass
		pygame.mixer.music.play()
		self.State = STATE_PLAYING

	# Pause the song - Use Pause() again to unpause
	def Pause(self):
		if self.State == STATE_PLAYING:
			pygame.mixer.music.pause()
			self.State = STATE_PAUSED
		elif self.State == STATE_PAUSED:
			pygame.mixer.music.unpause()
			self.State = STATE_PLAYING

	# Close the whole thing down
	def Close(self):
		self.State = STATE_CLOSING

	# you must call Play() to restart. Blocks until pygame is initialised
	def Rewind(self):
		while self.State == STATE_INIT:
			pass
		# Reset all the state (current lyric index etc)
		self.resetPlayingState()
		# Stop the audio
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
		return pygame.mixer.music.get_pos()

	# Get the current display size
	def GetDisplaySize(self):
		return self.displaySize

	# Set the display size. On MS Windows the actual set_mode must
	# be done in the pygame thread context, so defer it.
	def SetDisplaySize(self, displaySizeTuple):
		self.ResizeTuple = displaySizeTuple

	# Start the thread but don't play until Play() called
	def run(self):

		# It turns out that on MS Windows you have to initialise pygame in the
		# thread that is going to check for events. Therefore move all pygame
		# init stuff here. Play() will now have to block until pygame init is
		# complete.
		if os.name != "posix":
			self.pygame_init()

		# Load the MIDI player
		pygame.mixer.music.load(self.FileName)
		
		# Set an event for when the music finishes playing
		pygame.mixer.music.set_endevent(pygame.USEREVENT)

		# Reset all the state (current lyric index etc) and
		# paint the first 6 lines.
		self.resetPlayingState()

		# We're now ready to accept Play() commands
		self.State = STATE_INIT_DONE
		
		# Loop through updating the lyrics displayed based on current song position
		while 1:
			if self.State == STATE_PLAYING:
				curr_pos = pygame.mixer.music.get_pos()
				updated = self.colourUpdateMs(curr_pos)
				# Sleep if there's not much going on (reduce CPU load)
				if not updated:
					pygame.time.delay(50)

				# Check if any screen updates are now due
				if ((curr_pos - self.LastPos) / 1000.0) > (1.0 / SCREEN_UPDATES_PER_SEC):
					self.screenUpdate()
					self.LastPos = curr_pos

			# Resizes have to be done in the pygame thread context on
			# MS Windows, so other threads can set ResizeTuple to 
			# request a resize (This is wrappered by SetDisplaySize()).
			if self.ResizeTuple != None and self.GetPos() > 250:
				self.displaySize = self.ResizeTuple
				pygame.display.set_mode (self.displaySize, pygame.RESIZABLE)
				self.ResizeTuple = None

			# check for Pygame events
			for event in pygame.event.get():
				# Only handle resize events 250ms into song. This is to handle the
				# bizarre problem of SDL making the window small automatically if
				# you set SDL_VIDEO_WINDOW_POS and move the mouse around while the
				# window is opening. Give it some time to settle.
				if event.type == pygame.VIDEORESIZE and self.GetPos() > 250:
					self.displaySize = event.size
					pygame.display.set_mode (event.size, pygame.RESIZABLE)
				elif event.type == pygame.USEREVENT:
					self.State = STATE_CLOSING
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					self.State = STATE_CLOSING
				elif event.type == pygame.QUIT:
					self.State = STATE_CLOSING

			# Common handling code for a close request or if the
			# pygame window was quit
			if self.State == STATE_CLOSING:
					pygame.quit()
					# If the caller gave us a callback, let them know we're finished
					if self.SongFinishedCallback != None:
						self.SongFinishedCallback()
					return
			
	def displayNextLine(self):
		
		# Set the current displayed line x,y position
		x, y = self.displayed_x, self.displayed_y

		# Get the next lyric text for display, check we're not at the
		# end of the list.
		if self.displayed_index < len(self.midifile.lyrics):
			lyric = self.midifile.lyrics[self.displayed_index][1]
		else:
			return
		
		# Remove any leading slash from the first word on the line
		if lyric and lyric[0] == "/":
			lyric = lyric[1:]

		# Loop displaying until we have displayed a line
		newline = False
		slashr = False
		while newline == False:
		
			# Got to the next line: remove leading-slash, display, quit the loop
			if lyric and lyric[0] == "/":
				lyric = None
				newline = True
				move_on = False

			# Handle blank spaces valid for lyric-style events (just skip)
			elif lyric and lyric == "":
				lyric = None
				move_on = True

			# Handle \rs used for lyric-style events. It seems that in this case
			# you don't do the newline yet, you do it after the next lyric. So
			# we postpone the newline by setting slashr = True. (newline next time).
			elif lyric == "\r":
				lyric = None
				newline = False
				move_on = True
				slashr = True

			# Handle if the last lyric was a \r
			elif slashr == True:
				newline = True
				move_on = True

			# If we find a clear-screen we display this as a blank line. As we
			# only handle one line at a time, though, we set a flag to say we
			# have already displayed the blank line. Next time through we
			# will display the actual text. If the flag is set when we reach
			# here, we should display the text this time.
			elif lyric and lyric[0] == "\\":
				# Just display the blank line first time round
				if self.blank_carry == False:
					lyric = None
					self.blank_carry = True
					newline = True
					move_on = False
				# Second time round: display the text, not a new-line.
				else:
					lyric = lyric[1:]
					self.blank_carry = False
					move_on = True

			# Normal lyric event
			else:
				move_on = True
					
			# Display the lyric (if not a comment, or a new line)
			if lyric and (lyric != "") and (lyric[0] != "@"):
				x, y = displayWrite (self.unscaledSurface,self.font,lyric,x,y,(255,50,50))
			
			# Move on to the next lyric if this was a lyric or a comment
			if move_on:
				self.displayed_index += 1
				# Quit if this is the last lyric in the list
				if self.displayed_index < len(self.midifile.lyrics):
					lyric = self.midifile.lyrics[self.displayed_index][1]
				else:
					newline = True
		
		# Finished the line, move the x,y position to the start of the next line
		self.displayed_x = X_BORDER
		self.displayed_y = self.displayed_y + FONT_SIZE + LINE_GAP

		# Write out the update to the screen
		self.screenUpdate()


	# Returns True if an update was performed
	def colourUpdateMs(self, curr_ms):
	
		# Check if we're at the end of the list, just return
		if self.coloured_index >= len(self.midifile.lyrics):
			return False

		# Get the next lyric/delta tuple for colouring in
		tuple = self.midifile.lyrics[self.coloured_index]

		# Set the current coloured line x,y position
		x, y = self.coloured_x, self.coloured_y
	
		# Calculate the millisecond time for the next lyric
		time_ms = getTimeMSForDelta (self.midifile, tuple[0])
		
		# Calculate if any new lyrics should be displayed for the
		# the current millisecond time, accounting for the song-start
		# time which isn't reported by timidity (i.e. curr_ms is time
		# from first note in song, excluding time up to first note).
		if curr_ms >= (time_ms - self.midifile.earliestNoteMS):

			# Get the lyric that needs colouring
			lyric = tuple[1]

			# \r is used in lyric-style events for a new-line (without any lyric
			# in the same lyric string). It seems that the last lyric on a line
			# actually follows the \r, so we use a carry flag to say don't do
			# the newline until we've finished the next lyric. Don't set the
			# carry-flag until we've finished the lyric though.
			if (lyric == "\r"):
				lyric = ""

			# Leading-slash means this should be displayed on the next line.
			# We also use the next line for clear screens. Either way we will have
			# already done the scroll on the last lyric, so we need to move to the
			# correct new position, and remove the slash. Also check for a NULL 
			# lyric before indexing.
			if (lyric != "") and ((lyric[0] == "/") or (lyric[0] == "\\")):
				lyric = lyric[1:]
				x = X_BORDER
				y += FONT_SIZE + LINE_GAP
		
			# Now display it (if not a comment or newline). Check for a NULL lyric before
			# indexing.
			if (lyric != "") and ((lyric[0] != "@") and (lyric[0] != "\r")):
				x, y = displayWrite (self.unscaledSurface,self.font,lyric,x,y,(255,255,255))
	
			# Write out the update to the screen
			self.screenUpdate()
		
			# Move the index on to the next tuple for colouring
			self.coloured_index += 1
			
			# Check if we're at the end of the list
			if self.coloured_index >= len(self.midifile.lyrics):
				return True

			# Check if the next lyric will scroll us up, if so do the scroll
			# now rather than just as the lyric is being coloured. Check for
			# a NULL lyric before indexing.
			next = self.midifile.lyrics[self.coloured_index][1]
			if (next != "") and ((next[0] == "/") or (next[0] == "\\") or (self.slashr_carry == True)):
				if y == Y_BORDER + 2 * (FONT_SIZE + LINE_GAP):
					# Get a surfarray for the current surface
					curr_surf = surfarray.pixels2d(self.unscaledSurface)
					# Create one line high arrays of black for top and bottom concatenation
					top_surf =  N.zeros([UNSCALED_WIDTH,FONT_SIZE])
					bottom_surf =  N.zeros([UNSCALED_WIDTH,FONT_SIZE + LINE_GAP])
					# Create a new surf_array scrolled up one line (black at top and bottom)
					curr_surf = N.concatenate((top_surf, curr_surf[:,(2 * FONT_SIZE) + LINE_GAP:]), 1)
					curr_surf = N.concatenate((curr_surf, bottom_surf), 1)
					# Blit the new surfarray to the screen
					surfarray.blit_array(self.unscaledSurface, curr_surf)
					# Set the colouring in pointer to the top of the screen
					x = X_BORDER
					y -= FONT_SIZE + LINE_GAP
					# Update the display pointer x,y position now scrolled up
					self.displayed_y -= FONT_SIZE + LINE_GAP
					# Display one more line
					self.displayNextLine()

				# Reset the \r carry flag and move the x,y position
				if self.slashr_carry == True:
					self.slashr_carry = False
					x = X_BORDER
					y += FONT_SIZE + LINE_GAP

			# Set the carry-flag now if this last index was a \r
			if (self.midifile.lyrics[self.coloured_index - 1][1] == "\r"):
				self.slashr_carry = True

			# Finished the lyric, move the x,y position on
			self.coloured_x, self.coloured_y = x, y

			# Return True because we updated
			return True

		# Else no update due
		return False	

	def screenUpdate(self):
		# Scale the unscaled surface up to the current screen size
		transformed = pygame.transform.scale(self.unscaledSurface, self.displaySize)
		# Blit the scaled up surface to the resized screen
		self.displaySurface.blit (transformed, (0,0))
		# Update
		pygame.display.flip()


def defaultErrorPrint(ErrorString):
	print (ErrorString)


def usage():
    print "Usage:  %s <kar filename>" % os.path.basename(sys.argv[0])


def main():
	args = sys.argv[1:]
	if (len(sys.argv) != 2) or ("-h" in args) or ("--help" in args):
		usage()
		sys.exit(2)

	# Instantiate the MIDI player class, passing the filename
	player = midPlayer(sys.argv[1])
	player.Play()
	

if __name__ == "__main__":
    sys.exit(main())
