#!/usr/bin/python

# pympg - MPEG Karaoke Player
#
# Copyright (C) 2004  Kelvin Lawson (kelvinl@users.sourceforge.net)
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

import pygame, sys, os
from threading import Thread

# OVERVIEW
#
# pympg is an MPEG player built using python. It was written for the
# PyKaraoke project but is in fact a general purpose MPEG player that
# could be used in other python projects requiring an MPEG player.
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
# MPG support, this module has been designed to be easily incorporated
# into such projects and is released under the LGPL.


# REQUIREMENTS
#
# pycdg requires the following to be installed on your system:
# . Python (www.python.org)
# . Pygame (www.pygame.org)


# USAGE INSTRUCTIONS
#
# To start the player, pass the MPEG filename/path on the command line:
# 		python pympg.py /songs/theboxer.mpg
#
# You can also incorporate a MPG player in your own projects by
# importing this module. The class mpgPlayer is exported by the
# module. You can import and start it as follows:
#	import pympg
#	player = pympg.mpgPlayer("/songs/theboxer.mpg")
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
# 	mpgPlayer ("/songs/theboxer.mpg", errorPopup, songFinishedCallback)
# These parameters are optional and default to None.
#
# If the initialiser fails (e.g. the song file is not present), __init__
# raises an exception.


# IMPLEMENTATION DETAILS
#
# pympg is implemented as one python module. Pygame provides all
# of the MPEG decoding and display capabilities, and can play an
# MPEG file with just a few lines of code. Hence this module is
# rather small. What it provides on top of the basic pygame
# features, is a player-like class interface with Play, Pause,
# Rewind etc. It also implements a resizable player window.
#
# The player is run within a thread to allow for easy
# integration with media player programs. Once the pygame MPEG
# player window is opened, it monitors for Rewind etc commands,
# and handles resize and close window events.


# States
STATE_NOT_PLAYING	= 1
STATE_PLAYING		= 2
STATE_CLOSING		= 3


# mpgPlayer Class
class mpgPlayer(Thread):
	# Initialise the player instace
	def __init__(self, mpgFileName, errorNotifyCallback=None, doneCallback=None):
		Thread.__init__(self)

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
					
		# Check the MPEG filename
		self.FileName = mpgFileName
		if not os.path.isfile(mpgFileName):
			ErrorString = "No such file: " + mpgFileName
			self.ErrorNotifyCallback (ErrorString)
			raise NoSuchFile
			return
		
		# Initialise the pygame movie library
		pygame.init()
		pygame.mixer.quit()
		pygame.display.set_caption(mpgFileName)
		self.Movie = pygame.movie.Movie(mpgFileName)
		# Default to movie display size
		self.DisplaySize = self.Movie.get_size()
		self.DisplaySurface = pygame.display.set_mode(self.DisplaySize, pygame.RESIZABLE, 32)
		self.Movie.set_display (self.DisplaySurface, (0, 0, self.DisplaySize[0], self.DisplaySize[1]))
		self.State = STATE_NOT_PLAYING
		
		# Automatically start the thread which handles pygame events
		# The movie doesn't start playing until Play() is called
		self.start()
		
	# Start the thread running
	def Play(self):
		self.Movie.play()
		self.State = STATE_PLAYING

	# Pause the mpg - Use Pause() again to unpause
	def Pause(self):
		if self.State == STATE_PLAYING:
			self.Movie.pause()
			self.State = STATE_NOT_PLAYING
		elif self.State == STATE_NOT_PLAYING:
			self.Movie.play()
			self.State = STATE_PLAYING

	# Close the whole thing down
	def Close(self):
		self.State = STATE_CLOSING

	# Rewind to the beginning - also stops the movie, so 
	# you must call Play() to restart
	def Rewind(self):
		self.Movie.stop()
		self.Movie.rewind()
		self.State = STATE_NOT_PLAYING

	# Stop the movie and returns to the beginning - Play()
	# restarts. For a pause, use Pause() instead.
	def Stop(self):
		self.Rewind()
			
	# Get the movie length (in seconds)
	def GetLength(self):
		return self.Movie.get_length()
		
	# Get the current time (in milliseconds)
	def GetPos(self):
		return (self.Movie.get_time() * 1000)

	# Get the current display size
	def GetDisplaySize(self):
		return self.DisplaySize

	# Set the display size
	def SetDisplaySize(self, displaySizeTuple):
		self.DisplaySize = displaySizeTuple
		# The pygame library needs to be paused while resizing
		if self.State == STATE_PLAYING:
			self.Movie.pause()
		# Resize the screen
		pygame.display.set_mode (self.DisplaySize, pygame.RESIZABLE, 32)
		self.Movie.set_display (self.DisplaySurface, (0, 0, self.DisplaySize[0], self.DisplaySize[1]))
		# Unpause if it was playing
		if self.State == STATE_PLAYING:
			self.Movie.play()
	
	# Start the thread but don't play until Play()
	def run(self):
		while 1:
			# Check for and handle pygame events and close requests
			for event in pygame.event.get():
				if event.type == pygame.VIDEORESIZE:
					self.SetDisplaySize(event.size)
				# If the pygame window is closed quit the thread
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					self.State = STATE_CLOSING
				elif event.type == pygame.QUIT:
					self.State = STATE_CLOSING
			# Common handling code for a close request or if the
			# pygame window was quit
			if  self.State == STATE_CLOSING:
					self.Movie.stop()
					self.Movie = None
					pygame.quit()
					# If the caller gave us a callback, let them know we're finished
					if self.SongFinishedCallback != None:
						self.SongFinishedCallback()
					return

def defaultErrorPrint(ErrorString):
	print (ErrorString)

def usage():
    print "Usage:  %s <mpg filename>" % os.path.basename(sys.argv[0])

def main():
	args = sys.argv[1:]
	if (len(sys.argv) != 2) or ("-h" in args) or ("--help" in args):
		usage()
		sys.exit(2)
	player = mpgPlayer(sys.argv[1])
	player.Play()
	
if __name__ == "__main__":
    sys.exit(main())
