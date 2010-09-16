#!/usr/bin/env python

# pykar - KAR/MID Karaoke Player
#
# Copyright (C) 2010 Kelvin Lawson (kelvinl@users.sf.net)
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
# pykar requires the following to be installed on your system:
# . Python (www.python.org)
# . Pygame (www.pygame.org)


# LINUX REQUIREMENTS
#
# To play the MIDI songs on Linux, Timidity++ is also required:
# . Timidity++ (timidity.sourceforge.net)

# OSX REQUIREMENTS
#
# On OSX, pygame will run MIDI natively by default, but if the GUS
# patches are installed in /usr/local/lib/timidity, it will run MIDI
# via Timidity instead, which appears to work better than the native
# support, so we recommend this.

# USAGE INSTRUCTIONS
#
# To start the player, pass the KAR filename/path on the command line:
#       python pykar.py /songs/theboxer.kar
#
# You can also incorporate a KAR player in your own projects by
# importing this module. The class midPlayer is exported by the
# module. You can import and start it as follows:
#   import pykar
#   player = pykar.midPlayer("/songs/theboxer.kar")
#   player.Play()
# If you do this, you must also arrange to call pycdg.manager.Poll()
# from time to time, at least every 100 milliseconds or so, to allow
# the player to do its work.
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
#   def errorPopup (ErrorString):
#       msgBox (ErrorString)
#
# doneCallback can be used to register a callback so that the player
# calls you back when the song is finished playing. The callback should
# take no parameters, e.g.:
#   def songFinishedCallback():
#       msgBox ("Song is finished")
#
# To register callbacks, pass the functions in to the initialiser:
#   midPlayer ("/songs/theboxer.kar", errorPopup, songFinishedCallback)
# These parameters are optional and default to None.
#
# If the initialiser fails (e.g. the song file is not present), __init__
# raises an exception.


# IMPLEMENTATION DETAILS
#
# pykar is implemented as a handful of python modules. Pygame provides
# support for playing MIDI files, so playing a MIDI song using Pygame
# is very easy. However, in order to find the lyrics from the MIDI
# file it was necessary to write a basic parser that understands the
# MIDI file format. This opens the MIDI file and reads all tracks,
# pulling out the lyric text and times. After this first parse of the
# MIDI file, this module does not do any more MIDI decoding for
# playing purposes - Pygame takes care of all actual music generation.
#
# Because a MIDI file might change tempo throughout the song, and
# because tempo changes are technically allowed to appear within any
# track and apply to all tracks, it is necessary to fully parse the
# MIDI file before making observations of tempo, and thus before being
# able to determine the precise time each lyric is to appear onscreen.
# Thus, we initially save only the "click" count of each lyric's
# appearance, and then once the file has been completely read, we can
# convert clicks to milliseconds.
#
# There is an extra complication on Linux which is that the MIDI
# support (provided by Timidity++, which is built into pygame) reports
# the current song time using the first note being played as the
# start. However on Windows the Pygame MIDI player returns the time
# from the start of the actual song (even if there is no sound for a
# few seconds). This meant that for Linux systems, it was necessary to
# parse the whole MIDI file and calculate the time of the first note
# from all tracks. This is then used as an offset in the calculation
# of when to display the lyrics.
#
# Previous implementations ran the player within a thread; this is no
# longer the case.  Instead, it is the caller's responsibility to call
# pykar.manager.Poll() every once in a while to ensure that the player
# gets enough CPU time to do its work.  Ideally, this should be at
# least every 100 milliseconds or so to guarantee good video and audio
# response time.


from pykconstants import *
from pykplayer import pykPlayer
from pykenv import env
from pykmanager import manager
import pygame, sys, os, struct, cStringIO

# At what percentage of the screen height should we try to keep the
# current singing cursor?  33% keeps it on the top third, 50% keeps it
# centered.
VIEW_PERCENT = 33

# Default font size at 480 pixels.
FONT_SIZE = 40

# How much lead time before a new paragraph is scrolled up into view
# (scrolling the old paragraph off), in milliseconds.  This only comes
# into play when there is a large time gap between syllables.
PARAGRAPH_LEAD_TIME = 5000

# text types.
TEXT_LYRIC  = 0
TEXT_INFO   = 1
TEXT_TITLE  = 2

# Debug out MIDI messages as text
debug = False
#debug = True

class midiFile:
    def __init__(self):
        self.trackList = []         # List of TrackDesc track descriptors

        # Chosen lyric list from above.  It is converted by
        # computeTiming() from a list of (clicks, text) into a list of
        # (ms, text).
        self.lyrics = []

        # self.text_encoding = "iso-8859-13"
        self.text_encoding = ""      # The encoding of text in midi file

        self.ClickUnitsPerSMPTE = None
        self.SMPTEFramesPerSec = None
        self.ClickUnitsPerQuarter = None

        # The tempo of the song may change throughout, so we have to
        # record the click at which each tempo change occurred, and
        # the new tempo at that point.  Then, after we have read in
        # all the tracks (and thus collected all the tempo changes),
        # we can go back and apply this knowledge to the other tracks.
        self.Tempo = [(0, 0)]

        self.Numerator = None               # Numerator
        self.Denominator = None             # Denominator
        self.ClocksPerMetronomeTick = None  # MIDI clocks per metronome tick
        self.NotesPer24MIDIClocks = None    # 1/32 Notes per 24 MIDI clocks
        self.earliestNoteMS = 0             # Start of earliest note in song
        self.lastNoteMS = 0                 # End of latest note in song


class TrackDesc:
    def __init__(self, trackNum):
        self.TrackNum = trackNum        # Track number
        self.TotalClicksFromStart = 0   # Store number of clicks elapsed from start
        self.BytesRead = 0              # Number of file bytes read for track
        self.FirstNoteClick = None      # Start of first note in track
        self.FirstNoteMs = None         # The same, in milliseconds
        self.LastNoteClick = None       # End of last note in track
        self.LastNoteMs = None          # In millseconds
        self.LyricsTrack = False        # This track contains lyrics
        self.RunningStatus = 0          # MIDI Running Status byte

        self.text_events = Lyrics()       # Lyrics (0x1 events)
        self.lyric_events = Lyrics()      # Lyrics (0x5 events)


class MidiTimestamp:
    """ This class is used to apply the tempo changes to the click
    count, thus computing a time in milliseconds for any number of
    clicks from the beginning of the song. """

    def __init__(self, midifile):
        self.ClickUnitsPerQuarter = midifile.ClickUnitsPerQuarter
        self.Tempo = midifile.Tempo
        self.ms = 0
        self.click = 0
        self.i = 0

    def advanceToClick(self, click):
        # Moves time forward to the indicated click number.
        clicks = click - self.click
        if clicks < 0:
            # Ignore jumps backward in time.
            return

        while clicks > 0 and self.i < len(self.Tempo):
            # How many clicks remain at the current tempo?
            clicksRemaining = max(self.Tempo[self.i][0] - self.click, 0)
            clicksUsed = min(clicks, clicksRemaining)
            if clicksUsed != 0:
                self.ms += self.getTimeForClicks(clicksUsed, self.Tempo[self.i - 1][1])
            self.click += clicksUsed
            clicks -= clicksUsed
            clicksRemaining -= clicksUsed
            if clicksRemaining == 0:
                self.i += 1

        if clicks > 0:
            # We have reached the last tempo mark of the song, so this
            # tempo holds forever.
            self.ms += self.getTimeForClicks(clicks, self.Tempo[-1][1])
            self.click += clicks

    def getTimeForClicks(self, clicks, tempo):
        microseconds = ( ( float(clicks) / self.ClickUnitsPerQuarter ) * tempo );
        time_ms = microseconds / 1000
        return (time_ms)

class LyricSyllable:
    """ Each instance of this class records a single lyric event,
    e.g. a syllable of a word to be displayed and change color at a
    given time.  The Lyrics class stores a list of these. """

    def __init__(self, click, text, line, type = TEXT_LYRIC):
        self.click = click
        self.ms = None
        self.text = text
        self.line = line
        self.type = type

        # This is filled in when the syllable is drawn onscreen.
        self.left = None
        self.right = None

    def makeCopy(self, text):
        # Returns a new LyricSyllable, exactly like this one, with
        # the text replaced by the indicated string
        syllable = LyricSyllable(self.click, text, self.line, self.type)
        syllable.ms = self.ms
        return syllable

    def __repr__(self):
        return "<%s %s>" % (self.ms, self.text)

class Lyrics:
    """ This is the complete lyrics of a song, organized as a list of
    syllables sorted by event time. """

    def __init__(self):
        self.list = []
        self.line = 0

    def hasAny(self):
        # Returns true if there are any lyrics.
        return bool(self.list)

    def recordText(self, click, text):
        # Records a MIDI 0x1 text event (a syllable).

        # Make sure there are no stray null characters in the string.
        text = text.replace('\x00', '')
        # Or CR's.
        text = text.replace('\r', '')

        if not text:
            # Ignore blank lines.
            return

        if text[0] == '@':
            if text[1] == 'T':
                # A title.
                type = TEXT_TITLE
            elif text[1] == 'I':
                # An info line.
                type = TEXT_INFO
            else:
                # Any other comment we ignore.
                return

            # Put the comment onscreen.
            for line in text[2:].split('\n'):
                line = line.strip()
                self.line += 1
                self.list.append(LyricSyllable(click, line, self.line, type))
            return

        if text[0] == '\\':
            # Paragraph break.  We treat it the same as line break,
            # but with an extra blank line.
            self.line += 2
            text = text[1:]
        elif text[0] == '/':
            # Line break.
            self.line += 1
            text = text[1:]

        if text:
            lines = text.split('\n')
            self.list.append(LyricSyllable(click, lines[0], self.line))
            for line in lines[1:]:
                self.line += 1
                self.list.append(LyricSyllable(click, line, self.line))

    def recordLyric(self, click, text):
        # Records a MIDI 0x5 lyric event (a syllable).

        # Make sure there are no stray null characters in the string.
        text = text.replace('\x00', '')

        if text == '\n':
            # Paragraph break.  We treat it the same as line break,
            # but with an extra blank line.
            self.line += 2

        elif text == '\r' or text == '\r\n':
            # Line break.
            self.line += 1

        elif text:
            text = text.replace('\r', '')

            if text[0] == '\\':
                # Paragraph break.  This is a text event convention, not a
                # lyric event convention, but some midi files don't play
                # by the rules.
                self.line += 2
                text = text[1:]
            elif text[0] == '/':
                # Line break.  A text convention, but see above.
                self.line += 1
                text = text[1:]

            # Lyrics aren't supposed to include embedded newlines, but
            # sometimes they do anyway.
            lines = text.split('\n')
            self.list.append(LyricSyllable(click, lines[0], self.line))
            for line in lines[1:]:
                self.line += 1
                self.list.append(LyricSyllable(click, line, self.line))

    def computeTiming(self, midifile):
        # Walk through the lyrics and convert the click information to
        # elapsed time in milliseconds.

        ts = MidiTimestamp(midifile)
        for syllable in self.list:
            ts.advanceToClick(syllable.click)
            syllable.ms = int(ts.ms)

        # Also change the firstNoteClick to firstNoteMs, for each track.
        for track_desc in midifile.trackList:
            ts = MidiTimestamp(midifile)
            if track_desc.FirstNoteClick != None:
                ts.advanceToClick(track_desc.FirstNoteClick)
                track_desc.FirstNoteMs = ts.ms
                if debug:
                    print "T%s first note at %s clicks, %s ms" % (
                        track_desc.TrackNum, track_desc.FirstNoteClick,
                        track_desc.FirstNoteMs)
            if track_desc.LastNoteClick != None:
                ts.advanceToClick(track_desc.LastNoteClick)
                track_desc.LastNoteMs = ts.ms

    def analyzeSpaces(self):
        """ Checks for a degenerate case: no (or very few) spaces
        between words.  Sometimes Karaoke writers omit the spaces
        between words, which makes the text very hard to read.  If we
        detect this case, repair it by adding spaces back in. """

        # First, group the syllables into lines.
        lineNumber = None
        lines = []
        currentLine = []

        for syllable in self.list:
            if syllable.line != lineNumber:
                if currentLine:
                    lines.append(currentLine)
                currentLine = []
                lineNumber = syllable.line
            currentLine.append(syllable)

        if currentLine:
            lines.append(currentLine)

        # Now, count the spaces between the syllables of the lines.
        totalNumSyls = 0
        totalNumGaps = 0
        for line in lines:
            numSyls = len(line) - 1
            numGaps = 0
            for i in range(numSyls):
                if line[i].text.rstrip() != line[i].text or \
                   line[i + 1].text.lstrip() != line[i + 1].text:
                    numGaps += 1

            totalNumSyls += numSyls
            totalNumGaps += numGaps

        if totalNumSyls and float(totalNumGaps) / float(totalNumSyls) < 0.1:
            # Too few spaces.  Insert more.
            for line in lines:
                for syllable in line[:-1]:
                    if syllable.text.endswith('-'):
                        # Assume a trailing hyphen means to join syllables.
                        syllable.text = syllable.text[:-1]
                    else:
                        syllable.text += ' '


    def wordWrapLyrics(self, font):
        # Walks through the lyrics and folds each line to the
        # indicated width.  Returns the new lyrics as a list of lists
        # of syllables; that is, each element in the returned list
        # corresponds to a displayable line, and each line is a list
        # of syllabels.

        if not self.list:
            return []

        maxWidth = manager.displaySize[0] - X_BORDER * 2

        lines = []

        x = 0
        currentLine = []
        currentText = ''
        lineNumber = self.list[0].line
        for syllable in self.list:
            # Ensure the screen position of the syllable is cleared,
            # in case we are re-wrapping text that was already
            # displayed.
            syllable.left = None
            syllable.right = None

            while lineNumber < syllable.line:
                # A newline.
                lines.append(currentLine)
                x = 0
                currentLine = []
                currentText = ''
                lineNumber += 1

            width, height = font.size(syllable.text)
            currentLine.append(syllable)
            currentText += syllable.text
            x += width
            while x > maxWidth:
                foldPoint = manager.FindFoldPoint(currentText, font, maxWidth)
                if foldPoint == len(currentText):
                    # Never mind.  Must be just whitespace on the end of
                    # the line; let it pass.
                    break

                # All the characters before foldPoint get output as the
                # first line.
                n = 0
                i = 0
                text = currentLine[i].text
                outputLine = []
                while n + len(text) <= foldPoint:
                    outputLine.append(currentLine[i])
                    n += len(text)
                    i += 1
                    text = currentLine[i].text

                syllable = currentLine[i]
                if i == 0:
                    # One long line.  Break it mid-phrase.
                    a = syllable.makeCopy(syllable.text[:foldPoint])
                    outputLine.append(a)
                    b = syllable.makeCopy('  ' + syllable.text[foldPoint:])
                    currentLine[i] = b

                else:
                    currentLine[i] = syllable.makeCopy('  ' + syllable.text)

                # The remaining characters become the next line.
                lines.append(outputLine)
                currentLine = currentLine[i:]
                currentText = ''
                for syllable in currentLine:
                    currentText += syllable.text
                x, height = font.size(currentText)

        lines.append(currentLine)

        # Indicated that the first syllable of each line is flush with
        # the left edge of the screen.
        for l in lines:
            if l:
                l[0].left = X_BORDER

        #print lines
        return lines

    def write(self):
        # Outputs the lyrics, one line at a time.
        for syllable in self.list:
            print "%s(%s) %s %s" % (syllable.ms, syllable.click, syllable.line, repr(syllable.text))

def midiParseData(midiData, ErrorNotifyCallback, Encoding):

    # Create the midiFile structure
    midifile = midiFile()
    midifile.text_encoding = Encoding

    # Open the file
    filehdl = cStringIO.StringIO(midiData)

    # Check it's a MThd chunk
    packet = filehdl.read(8)
    ChunkType, Length = struct.unpack('>4sL', packet)
    if (ChunkType != "MThd"):
        ErrorNotifyCallback ("No MIDI Header chunk at start")
        return None

    # Read header
    packet = filehdl.read(Length)
    format, tracks, division = struct.unpack('>HHH', packet)
    if (division & 0x8000):
        midifile.ClickUnitsPerSMPTE = division & 0x00FF
        midifile.SMPTEFramesPerSec = division & 0x7F00
    else:
        midifile.ClickUnitsPerQuarter = division & 0x7FFF

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
        ChunkType, Length = struct.unpack('>4sL', packet)
        if (ChunkType != "MTrk"):
            if debug:
                print ("Didn't find expected MIDI Track")

        # Process the track, getting a TrackDesc structure
        track_desc = midiParseTrack(filehdl, midifile, trackNum, Length, ErrorNotifyCallback)
        if track_desc:
            trackBytes = track_desc.BytesRead
            # Store the track descriptor with the others
            midifile.trackList.append(track_desc)
            # Debug out the first note for this track
            if debug:
                print ("T%d: First note(%s)" % (trackNum, track_desc.FirstNoteClick))
            trackNum = trackNum + 1

    # Close the open file
    filehdl.close()

    # Get the lyrics from the best track.  We prefer any tracks that
    # are "lyrics" tracks.  Failing that, we get the track with the
    # most number of syllables.
    bestSortKey = None
    midifile.lyrics = None

    for track_desc in midifile.trackList:
        lyrics = None

        # Decide which list of lyric events to choose. There may be
        # text events (0x01), lyric events (0x05) or sometimes both
        # for compatibility. If both are available, we choose the one
        # with the most syllables, or text if they're the same.
        if track_desc.text_events.hasAny() and track_desc.lyric_events.hasAny():
            if len(track_desc.lyric_events.list) > len(track_desc.text_events.list):
                lyrics = track_desc.lyric_events
            else:
                lyrics = track_desc.text_events
        elif track_desc.text_events.hasAny():
            lyrics = track_desc.text_events
        elif track_desc.lyric_events.hasAny():
            lyrics = track_desc.lyric_events

        if not lyrics:
            continue
        sortKey = (track_desc.LyricsTrack, len(lyrics.list))
        if sortKey > bestSortKey:
            bestSortKey = sortKey
            midifile.lyrics = lyrics

    if not midifile.lyrics:
        ErrorNotifyCallback ("No lyrics in the track")
        return None

    midifile.lyrics.computeTiming(midifile)
    midifile.lyrics.analyzeSpaces()

    # Calculate the song start (earliest note event in all tracks), as
    # well as the song end (last note event in all tracks).
    earliestNoteMS = None
    lastNoteMS = None
    for track in midifile.trackList:
        if track.FirstNoteMs != None:
            if (track.FirstNoteMs < earliestNoteMS) or (earliestNoteMS == None):
                earliestNoteMS = track.FirstNoteMs
        if track.LastNoteMs != None:
            if (track.LastNoteMs > lastNoteMS) or (lastNoteMS == None):
                lastNoteMS = track.LastNoteMs
    midifile.earliestNoteMS = earliestNoteMS
    midifile.lastNoteMS = lastNoteMS

    if debug:
        print "first = %s" % (midifile.earliestNoteMS)
        print "last = %s" % (midifile.lastNoteMS)

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
    click, varBytes = varLength(filehdl)
    if varBytes == 0:
        return 0
    bytesRead = bytesRead + varBytes
    track_desc.TotalClicksFromStart += click
    byteStr = filehdl.read(1)
    bytesRead = bytesRead + 1
    status_byte = ord(byteStr)

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
##     if debug:
##         print "Event: 0x%X" % event_type

    # Handle all event types
    if event_type == 0xFF:
        byteStr = filehdl.read(1)
        bytesRead = bytesRead + 1
        event = ord(byteStr)
        if debug:
            print "MetaEvent: 0x%X" % event
        if event == 0x00:
            # Sequence number (discarded)
            packet = filehdl.read(2)
            bytesRead = bytesRead + 2
            zero, type = map(ord, packet)
            if type == 0x02:
                # Discard next two bytes as well
                discard = filehdl.read(2)
            elif type == 0x00:
                # Nothing left to discard
                pass
            else:
                if debug:
                    print ("Invalid sequence number (%d)" % type)
        elif event == 0x01:
            # Text Event
            Length, varBytes = varLength(filehdl)
            bytesRead = bytesRead + varBytes
            text = filehdl.read(Length)
            bytesRead = bytesRead + Length
            if Length > 1000:
                # This must be a mistake.
                if debug:
                    print ("Ignoring text of length %s" % (Length))
            else:
                if (midifile.text_encoding != "") :
                    text = text.decode(midifile.text_encoding, 'replace')
                # Take out any Sysex text events, and append to the lyrics list
                if (" SYX" not in text) and ("Track-" not in text) \
                    and ("%-" not in text) and ("%+" not in text):
                    track_desc.text_events.recordText(track_desc.TotalClicksFromStart, text)
                if debug:
                    print ("Text: %s" % (repr(text)))
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
                print ("Track Title: " + repr(title))
            if title == "Words":
                track_desc.LyricsTrack = True
        elif event == 0x04:
            # Instrument (discard)
            Length, varBytes = varLength(filehdl)
            bytesRead = bytesRead + varBytes
            discard = filehdl.read(Length)
            bytesRead = bytesRead + Length
        elif event == 0x05:
            # Lyric Event (a new style text record)
            Length, varBytes = varLength(filehdl)
            bytesRead = bytesRead + varBytes
            lyric = filehdl.read(Length)
            if (midifile.text_encoding != "") :
                lyric = lyric.decode(midifile.text_encoding, 'replace')
            bytesRead = bytesRead + Length
            # Take out any Sysex text events, and append to the lyrics list
            if (" SYX" not in lyric) and ("Track-" not in lyric) \
                and ("%-" not in lyric) and ("%+" not in lyric):
                track_desc.lyric_events.recordLyric(track_desc.TotalClicksFromStart, lyric)
            if debug:
                print ("Lyric: %s" % (repr(lyric)))
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
            valid = ord(byteStr)
            if valid != 0:
                print ("Invalid End of track")
        elif event == 0x51:
            # Set Tempo
            packet = filehdl.read(4)
            bytesRead = bytesRead + 4
            valid, tempoA, tempoB, tempoC = map(ord, packet)
            if valid != 0x03:
                print ("Error: Invalid tempo")
            tempo = (tempoA << 16) | (tempoB << 8) | tempoC
            midifile.Tempo.append((track_desc.TotalClicksFromStart, tempo))
            if debug:
                ms_per_quarter = (tempo/1000)
                print ("Tempo: %d (%d ms per quarter note)"% (tempo, ms_per_quarter))
        elif event == 0x54:
            # SMPTE (discard)
            packet = filehdl.read(6)
            bytesRead = bytesRead + 6
        elif event == 0x58:
            # Meta Event: Time Signature
            packet = filehdl.read(5)
            bytesRead = bytesRead + 5
            valid, num, denom, clocks, notes = map(ord, packet)
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
            valid, sf, mi = map(ord, packet)
            if valid != 0x02:
                print ("Error: Invalid key signature (valid=%d, sf=%d, mi=%d)" % (valid,sf,mi))
        elif event == 0x7F:
            # Sequencer Specific Meta Event
            Length, varBytes = varLength(filehdl)
            bytesRead = bytesRead + varBytes
            byteStr = filehdl.read(1)
            bytesRead = bytesRead + 1
            ID = ord(byteStr)
            if ID == 0:
                packet = filehdl.read(2)
                bytesRead = bytesRead + 2
                ID = struct.unpack('>H', packet)[0]
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
            if debug:
                print ("Unknown meta-event: 0x%X" % event)
            Length, varBytes = varLength(filehdl)
            bytesRead = bytesRead + varBytes
            discard = filehdl.read(Length)
            bytesRead = bytesRead + Length

    elif (event_type & 0xF0) == 0x80:
        # Note off
        packet = filehdl.read(2)
        bytesRead = bytesRead + 2
        track_desc.LastNoteClick = track_desc.TotalClicksFromStart
    elif (event_type & 0xF0) == 0x90:
        # Note on (discard but note if the start time of the first in the track)
        packet = filehdl.read(2)
        bytesRead = bytesRead + 2
        #print ("T%d: 0x%X" % (track_desc.TrackNum, event_type))
        if track_desc.FirstNoteClick == None:
            track_desc.FirstNoteClick = track_desc.TotalClicksFromStart
        track_desc.LastNoteClick = track_desc.TotalClicksFromStart
    elif (event_type & 0xF0) == 0xA0:
        # Key after-touch (discard)
        packet = filehdl.read(2)
        bytesRead = bytesRead + 2
    elif (event_type & 0xF0) == 0xB0:
        # Control change (discard)
        packet = filehdl.read(2)
        bytesRead = bytesRead + 2
        if debug:
            c, v = map(ord, packet)
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
        end = ord(end_byte)
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
        if debug:
            print ("Unknown event: 0x%x" % event_type)
        Length, varBytes = varLength(filehdl)
        bytesRead = bytesRead + varBytes
        discard = filehdl.read(Length)
        bytesRead = bytesRead + Length
    return bytesRead


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
            byteVal = ord(byteStr)
            convertedInt = (convertedInt << 7) | (byteVal & 0x7F)
            #print ("<0x%X/0x%X>"% (byteVal, convertedInt))
            if (byteVal & 0x80):
                bitShift = bitShift + 7
            else:
                break
        else:
            return (0, 0)
    return (convertedInt, bytesRead)


class midPlayer(pykPlayer):
    def __init__(self, song, songDb, errorNotifyCallback=None, doneCallback=None):
        """The first parameter, song, may be either a pykdb.SongStruct
        instance, or it may be a filename. """

        pykPlayer.__init__(self, song, songDb, errorNotifyCallback, doneCallback)
        settings = self.songDb.Settings

        self.SupportsFontZoom = True
        self.isValid = False

        # Parse the MIDI file
        self.midifile = midiParseData(self.SongDatas[0].GetData(), self.ErrorNotifyCallback, settings.KarEncoding)
        if (self.midifile == None):
            ErrorString = "ERROR: Could not parse the MIDI file"
            self.ErrorNotifyCallback (ErrorString)
            return
        elif (self.midifile.lyrics == None):
            ErrorString = "ERROR: Could not get any lyric data from file"
            self.ErrorNotifyCallback (ErrorString)
            return

        self.isValid = True

        # Debug out the found lyrics
        if debug:
            self.midifile.lyrics.write()

        manager.setCpuSpeed('kar')
        manager.InitPlayer(self)
        manager.OpenDisplay()

        if not manager.options.nomusic:
            manager.OpenAudio(frequency = manager.settings.MIDISampleRate,
                              channels = 1)

        # Account for the size of the playback buffer in the lyrics
        # display.  Assume that the buffer will be mostly full.  On a
        # slower computer that's struggling to keep up, this may not
        # be the right amount of delay, but it should usually be
        # pretty close.
        self.InternalOffsetTime = -manager.GetAudioBufferMS()

        self.screenDirty = False
        self.initFont()

        # Windows reports the song time correctly (including period up
        # to the first note), so no need for the earliest note hack
        # there.  On timidity-based platforms, we anticipate our
        # lyrics display by the time of the first note.

        # Note: pygame on OSX can run MIDI natively, or if the GUS
        # patches are installed in /usr/local/lib/timidity, it will
        # run MIDI via Timidity instead, which appears to work better
        # than the native support, so we recommend this.
        if env != ENV_WINDOWS:
            self.InternalOffsetTime += self.midifile.earliestNoteMS

        # Now word-wrap the text to fit our window.
        self.lyrics = self.midifile.lyrics.wordWrapLyrics(self.font)

        # By default, we will use the get_pos() functionality returned
        # by pygame to get the current time through the song, to
        # synchronize lyric display with the music.
        self.useMidiTimer = True

        if env == ENV_WINDOWS:
            # Unless we're running on Windows (i.e., not timidity).
            # For some reason, hardware MIDI playback can report an
            # unreliable time.  To avoid that problem, we'll always
            # use the CPU timer instead of the MIDI timer.
            self.useMidiTimer = False

        # Load the MIDI player
        if manager.options.nomusic:
            # If we're not playing music, use the CPU timer instead of
            # the MIDI timer.
            self.useMidiTimer = False

        else:
            # Load the sound normally for playback.
            audio_path = self.SongDatas[0].GetFilepath()
            if type(audio_path) == unicode:
                audio_path = audio_path.encode(sys.getfilesystemencoding())
            pygame.mixer.music.load(audio_path)

            # Set an event for when the music finishes playing
            pygame.mixer.music.set_endevent(pygame.USEREVENT)

        # Reset all the state (current lyric index etc) and
        # paint the first numRows lines.
        self.resetPlayingState()

    def GetPos(self):
        if self.useMidiTimer:
            return pygame.mixer.music.get_pos()
        else:
            return pykPlayer.GetPos(self)

    def SetupOptions(self):
        """ Initialise and return optparse OptionParser object,
        suitable for parsing the command line options to this
        application. """

        parser = pykPlayer.SetupOptions(self, usage = "%prog [options] <KAR file>")

        # Remove irrelevant options.
        parser.remove_option('--fps')
        parser.remove_option('--zoom')

        return parser


    def initFont(self):
        fontSize = int(FONT_SIZE * manager.GetFontScale() * manager.displaySize[1] / 480.)
        self.font = self.findPygameFont(self.songDb.Settings.KarFont, fontSize)
        self.lineSize = max(self.font.get_height(), self.font.get_linesize())
        self.numRows = int((manager.displaySize[1] - Y_BORDER * 2) / self.lineSize)

        # Put the current singing row at the specified fraction of the
        # screen.
        self.viewRow = int(self.numRows * VIEW_PERCENT / 100)

    def resetPlayingState(self):

        # Set the state variables

        # The current point the user was hearing within the song, as
        # of the last screen update.
        self.currentMs = 0

        # The line currently on display at the top of the screen.
        self.topLine = 0

        # The line on which the player is currently singing (that is,
        # the lowest line onscreen containing white syllables).
        self.currentLine = 0

        # The time at which this current syllable was sung.
        self.currentColourMs = 0

        # The next line with syllables that will need to be painted
        # white.
        self.nextLine = 0

        # The next syllable within the line that needs to be painted.
        self.nextSyllable = 0

        # The time at which the next syllable is to be painted.
        self.nextColourMs = 0

        # The time at which something is next scheduled to change
        # onscreen (usually the same as self.nextColourMs).
        self.nextChangeMs = 0

        self.repaintScreen()

    def repaintScreen(self):
        # Redraws the contents of the currently onscreen text.

        # Clear the screen
        settings = self.songDb.Settings
        manager.surface.fill(settings.KarBackgroundColour)

        # Paint the first numRows lines
        for i in range(self.numRows):
            l = self.topLine + i
            x = X_BORDER
            if l < len(self.lyrics):
                for syllable in self.lyrics[l]:
                    syllable.left = x
                    self.drawSyllable(syllable, i, None)
                    x = syllable.right

        manager.Flip()
        self.screenDirty = False

    def drawSyllable(self, syllable, row, x):
        """Draws a new syllable on the screen in the appropriate
        color, either red or white, according to self.currentMs.  The
        syllable is draw on the screen at the specified row, numbering
        0 from the top of the screen.  The value x indicates the x
        position of the end of the previous syllable, which is used to
        fill in the syllable's x position if it is not already known.
        x may be none if the syllable's x position is already
        known."""

        if syllable.left == None:
            syllable.left = x
            if syllable.left == None:
                return

        y = Y_BORDER + row * self.lineSize

        settings = self.songDb.Settings

        if syllable.type == TEXT_LYRIC:
            if self.currentMs < syllable.ms:
                color = settings.KarReadyColour
            else:
                color = settings.KarSweepColour
        elif syllable.type == TEXT_INFO:
            color = settings.KarInfoColour
        elif syllable.type == TEXT_TITLE:
            color = settings.KarTitleColour

        # Render text on a black background (instead of transparent)
        # to save a hair of CPU time.
        text = self.font.render(syllable.text, True, color,
                                settings.KarBackgroundColour)

        width, height = text.get_size()
        syllable.right = syllable.left + width

        manager.surface.blit(text, (syllable.left, y, width, height))

    def __hasLyrics(self):
        """ Returns true if the midi file contains any lyrics at all,
        false if it doesn't (or contains only comments). """

        if not self.midifile or not self.midifile.lyrics:
            return False

        for syllable in self.midifile.lyrics.list:
            if syllable.type == TEXT_LYRIC:
                return True
        return False

    def doValidate(self):
        if not self.__hasLyrics():
            return False

        return True

    def doPlay(self):
        if not manager.options.nomusic:
            pygame.mixer.music.play()

            # For some reason, timidity sometimes reports a bogus
            # get_pos() until the first few milliseconds have elapsed.  As
            # a cheesy way around this, we'll just wait a bit right up
            # front.
            pygame.time.wait(50)

    def doPause(self):
        if not manager.options.nomusic:
            pygame.mixer.music.pause()

    def doUnpause(self):
        if not manager.options.nomusic:
            pygame.mixer.music.unpause()

    def doRewind(self):
        # Reset all the state (current lyric index etc)
        self.resetPlayingState()
        # Stop the audio
        if not manager.options.nomusic:
            pygame.mixer.music.rewind()
            pygame.mixer.music.stop()

    def GetLength(self):
        """Give the number of seconds in the song."""
        return self.midifile.lastNoteMS / 1000

    def shutdown(self):
        # This will be called by the pykManager to shut down the thing
        # immediately.
        if not manager.options.nomusic:
            if manager.audioProps:
                pygame.mixer.music.stop()
        pykPlayer.shutdown(self)


    def doStuff(self):
        pykPlayer.doStuff(self)

        if self.State == STATE_PLAYING or self.State == STATE_CAPTURING:
            self.currentMs = int(self.GetPos() + self.InternalOffsetTime + manager.settings.SyncDelayMs)
            self.colourUpdateMs()

            # If we're not using the automatic midi timer, we have to
            # know to when stop the song at the end ourselves.
            if self.currentMs > self.midifile.lastNoteMS:
                self.Close()

    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and (event.mod & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT | pygame.KMOD_LMETA | pygame.KMOD_RMETA)):
            # Shift/meta return: start/stop song.  Useful for keybinding apps.
            self.Close()
            return
        
        pykPlayer.handleEvent(self, event)

    def doResize(self, newSize):
        # This will be called internally whenever the window is
        # resized for any reason, either due to an application resize
        # request being processed, or due to the user dragging the
        # window handles.
        self.initFont()
        self.lyrics = self.midifile.lyrics.wordWrapLyrics(self.font)

        self.topLine = 0
        self.currentLine = 0
        self.currentColourMs = 0
        self.nextLine = 0
        self.nextSyllable = 0
        self.nextColourMs = 0
        self.nextChangeMs = 0

        self.screenDirty = True
        self.colourUpdateMs()

    def colourUpdateMs(self):
        # If there's nothing yet to happen, just return.
        if self.nextChangeMs == None or self.currentMs < self.nextChangeMs:
            return False

        syllables = self.getNewSyllables()
        self.nextChangeMs = self.nextColourMs

        # Is it time to scroll?
        syllables = self.considerScroll(syllables)

        if self.screenDirty:
            # If the whole screen needs to be redrawn anyway, just do
            # that.
            self.repaintScreen()

        else:
            # Otherwise, draw only the syllables that have changed.
            x = None
            for syllable, line in syllables:
                self.drawSyllable(syllable, line - self.topLine, x)
                x = syllable.right

            manager.Flip()

        return True

    def getNewSyllables(self):
        """Scans the list of syllables and returns a list of (syllable,
        line) tuples that represent the syllables that need to be
        updated (changed color) onscreen.

        Also updates self.currentLine, self.currentColourMs, self.nextLine,
        self.nextSyllable, and self.nextColourMs. """

        syllables = []

        while self.nextLine < len(self.lyrics):
            line = self.lyrics[self.nextLine]
            while self.nextSyllable < len(line):
                syllable = line[self.nextSyllable]
                if self.currentMs < syllable.ms:
                    # This is the first syllable we should *not*
                    # display.  Stop here.
                    self.nextColourMs = syllable.ms
                    return syllables

                syllables.append((syllable, self.nextLine))
                self.currentLine = self.nextLine
                self.currentColourMs = syllable.ms
                self.nextSyllable += 1

            self.nextLine += 1
            self.nextSyllable = 0

        # There are no more syllables to be displayed.
        self.nextColourMs = None
        return syllables


    def considerScroll(self, syllables):
        """Determines whether it is time to scroll the screen.  If it
        is, performs the scroll (without flipping the display yet),
        and returns the new list of syllables that need to be painted.
        If it is not yet time to scroll, does nothing and does not
        modify the syllable list. """

        # If the player's still singing the top line, we can't scroll
        # it off yet.
        if self.currentLine <= self.topLine:
            return syllables

        # If the rest of the lines fit onscreen, don't bother scrolling.
        if self.topLine + self.numRows >= len(self.lyrics):
            return syllables

        # But don't scroll unless we have less than
        # PARAGRAPH_LEAD_TIME milliseconds to go.
        timeGap = 0
        if self.nextColourMs != None:
            timeGap = self.nextColourMs - self.currentColourMs
            scrollTime = self.nextColourMs - PARAGRAPH_LEAD_TIME
            if self.currentMs < scrollTime:
                self.nextChangeMs = scrollTime
                return syllables

        # Put the current line on self.viewRow by choosing
        # self.topLine appropriately.  If there is a long gap between
        # lyrics, go straight to the next line.
        currentLine = self.currentLine
        if timeGap > PARAGRAPH_LEAD_TIME:
            currentLine = self.nextLine
        topLine = max(min(currentLine - self.viewRow, len(self.lyrics) - self.numRows), 0)
        if topLine == self.topLine:
            # No need to scroll.
            return syllables

        # OK, we have to scroll.  How many lines?
        linesScrolled = topLine - self.topLine
        self.topLine = topLine
        if linesScrolled < 0 or linesScrolled >= self.numRows:
            # Never mind; we'll need to repaint the whole screen anyway.
            self.screenDirty = True
            return []

        linesRemaining = self.numRows - linesScrolled

        # Blit the lower part of the screen to the top.
        y = Y_BORDER + linesScrolled * self.lineSize
        h = linesRemaining * self.lineSize
        rect = pygame.Rect(X_BORDER, y,
                           manager.displaySize[0] - X_BORDER * 2, h)
        manager.surface.blit(manager.surface, (X_BORDER, Y_BORDER), rect)

        # And now fill the lower part of the screen with black.
        y = Y_BORDER + linesRemaining * self.lineSize
        h = linesScrolled * self.lineSize
        rect = pygame.Rect(X_BORDER, y,
                           manager.displaySize[0] - X_BORDER * 2, h)
        settings = self.songDb.Settings
        manager.surface.fill(settings.KarBackgroundColour, rect)

        # We can remove any syllables from the list that might have
        # scrolled off the screen now.
        i = 0
        while i < len(syllables) and syllables[i][1] < self.topLine:
            i += 1
        if i:
            syllables = syllables[i:]

        # And furthermore, we need to draw all the syllables that are
        # found in the newly-appearing lines.
        for i in range(self.topLine + self.numRows - linesScrolled,
                       self.topLine + self.numRows):
            line = self.lyrics[i]
            for syllable in line:
                syllables.append((syllable, i))

        return syllables


def usage():
    print "Usage:  %s <kar filename>" % os.path.basename(sys.argv[0])


# Can be called from the command line with the CDG filepath as parameter
def main():
    player = midPlayer(None, None)
    if player.isValid:
        player.Play()
        manager.WaitForPlayer()

if __name__ == "__main__":
    sys.exit(main())
    #import profile
    #result = profile.run('main()', 'pykar.prof')
    #sys.exit(result)
