#
# Copyright (C) 2010 Kelvin Lawson (kelvinl@users.sourceforge.net)
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

""" This module is the Python implementation of the auxiliary classes
and functions which have been moved into C for performance reasons.
On the off-chance a C compiler is not available or not reliable for
some reason, you can use this implementation instead. """

import pygame
try:
    import Numeric as N
except ImportError:
    import numpy.oldnumeric as N

# CDG Command Code
CDG_COMMAND             = 0x09

# CDG Instruction Codes
CDG_INST_MEMORY_PRESET      = 1
CDG_INST_BORDER_PRESET      = 2
CDG_INST_TILE_BLOCK         = 6
CDG_INST_SCROLL_PRESET      = 20
CDG_INST_SCROLL_COPY        = 24
CDG_INST_DEF_TRANSP_COL     = 28
CDG_INST_LOAD_COL_TBL_0_7   = 30
CDG_INST_LOAD_COL_TBL_8_15  = 31
CDG_INST_TILE_BLOCK_XOR     = 38

# Bitmask for all CDG fields
CDG_MASK            = 0x3F

# This is the size of the display as defined by the CDG specification.
# The pixels in this region can be painted, and scrolling operations
# rotate through this number of pixels.
CDG_FULL_WIDTH      = 300
CDG_FULL_HEIGHT     = 216

# This is the size of the array that we operate on.  We add an
# additional border on the right and bottom edge of 6 and 12 pixels,
# respectively, to allow for display shifting.  (It's not clear from
# the spec which colour should be visible when the display is shifted
# to the right or down.  We say it should be the border colour.)

# This is the size of the screen that is actually intended to be
# visible.  It is the center area of CDG_FULL.  The remaining border
# area surrounding it is not meant to be visible.
CDG_DISPLAY_WIDTH   = 288
CDG_DISPLAY_HEIGHT  = 192

# Screen tile positions
# The viewable area of the screen (288x192) is divided into
# 24 tiles (6x4 of 49x51 each). This is used to only update
# those tiles which have changed on every screen update,
# thus reducing the CPU load of screen updates. A bitmask of
# tiles requiring update is held in cdgPlayer.UpdatedTiles.
# This stores each of the 4 columns in separate bytes, with 6 bits used
# to represent the 6 rows.
TILES_PER_ROW           = 6
TILES_PER_COL           = 4
TILE_WIDTH              = CDG_DISPLAY_WIDTH / TILES_PER_ROW
TILE_HEIGHT             = CDG_DISPLAY_HEIGHT / TILES_PER_COL

COLOUR_TABLE_SIZE       = 16

class CdgPacket:
    """ This class just represents a single 24-byte packet read from
    the CDG stream.  It's not used outside this module. """
    
    def __init__(self, packetData):
        self.command = packetData[0]
        self.instruction = packetData[1]
        #self.parityQ = packetData[2:4]
        self.data = packetData[4:20]
        #self.parity = packetData[20:24]

class CdgPacketReader:
    """ This class does the all work of reading packets from the CDG
    file, and evaluating them to fill in pixels in a Numeric array.
    Its public interface is in five methods. """

    # In this class, we are aggressive with the use of the leading
    # double underscore, Python's convention to indicate private
    # members.  We do this to clearly delineate the private data and
    # methods from the public data and methods, since only the public
    # members are of interest to the C port of this class.  (Though,
    # in practice, the C port follows this class structure quite
    # closely, including duplicating the private members.)
    
    def __init__(self, cdgData, mapperSurface):
        self.__cdgData = cdgData
        self.__cdgDataPos = 0

        # This is just for the purpose of mapping colors.
        self.__mapperSurface = mapperSurface

        self.Rewind()
        
    def Rewind(self):
        """ Rewinds the stream to the beginning, and resets all
        internal state in preparation for decoding the tiles
        again. """
        
        self.__cdgDataPos = 0

        # Initialise the colour table. Set a default value for any
        # CDG files that don't actually load the colour table
        # before doing something with it.
        defaultColour = 0
        self.__cdgColourTable = [defaultColour] * COLOUR_TABLE_SIZE

        self.__justClearedColourIndex = -1
        self.__cdgPresetColourIndex = -1
        self.__cdgBorderColourIndex = -1
        # Support only one transparent colour
        self.__cdgTransparentColour = -1

        # These values are used to implement screen shifting.  The CDG
        # specification allows the entire screen to be shifted, up to
        # 5 pixels right and 11 pixels down.  This shift is persistent
        # until it is reset to a different value.  In practice, this
        # is used in conjunction with scrolling (which always jumps in
        # integer blocks of 6x12 pixels) to perform
        # one-pixel-at-a-time scrolls.
        self.__hOffset = 0
        self.__vOffset = 0
        
        # Build a 306x228 array for the pixel indeces, including border area
        self.__cdgPixelColours = N.zeros((CDG_FULL_WIDTH, CDG_FULL_HEIGHT))

        # Build a 306x228 array for the actual RGB values. This will
        # be changed by the various commands, and blitted to the
        # screen now and again. But the border area will not be
        # blitted, only the central 288x192 area.
        self.__cdgSurfarray = N.zeros((CDG_FULL_WIDTH, CDG_FULL_HEIGHT))

        # Start with all tiles requiring update
        self.__updatedTiles = 0xFFFFFFFFL

    def MarkTilesDirty(self):
        """ Marks all the tiles dirty, so that the next call to
        GetDirtyTiles() will return the complete list of tiles. """
        
        self.__updatedTiles = 0xFFFFFFFFL

    def GetDirtyTiles(self):
        """ Returns a list of (row, col) tuples, corresponding to all
        of the currently-dirty tiles.  Then resets the list of dirty
        tiles to empty. """
        
        tiles = []
        if self.__updatedTiles != 0:
            for col in range(TILES_PER_COL):
                for row in range(TILES_PER_ROW):
                    if (self.__updatedTiles & ((1 << row) << (col * 8))):
                        tiles.append((row, col))

        self.__updatedTiles = 0
        return tiles

    def GetBorderColour(self):
        """ Returns the current border colour, as a mapped integer
        ready to apply to the surface.  Returns None if the border
        colour has not yet been specified by the CDG stream. """
        
        if self.__cdgBorderColourIndex == -1:
            return None
        return self.__cdgColourTable[self.__cdgBorderColourIndex]

    def DoPackets(self, numPackets):
        """ Reads numPackets 24-byte packets from the CDG stream, and
        processes their instructions on the internal tables stored
        within this object.  Returns True on success, or False when
        the end-of-file has been reached and no more packets can be
        processed."""
        
        for i in range(numPackets):
            # Extract the nexxt packet
            packd = self.__getNextPacket()
            if not packd:
                # No more packets.  Return False, but only if we
                # reached this condition on the first packet.
                return (i != 0)

            self.__cdgPacketProcess (packd)

        return True

    def FillTile(self, surface, row, col):
        """ Fills in the pixels on the indicated one-tile surface
        (which must be a TILE_WIDTH x TILE_HEIGHT sized surface) with
        the pixels from the indicated tile. """
        
        # Calculate the row & column starts/ends
        row_start = 6 + self.__hOffset + (row * TILE_WIDTH)
        row_end = 6 + self.__hOffset + ((row + 1) * TILE_WIDTH)
        col_start = 12 + self.__vOffset + (col * TILE_HEIGHT)
        col_end = 12 + self.__vOffset + ((col + 1) * TILE_HEIGHT)
        pygame.surfarray.blit_array( \
            surface, \
            self.__cdgSurfarray[row_start:row_end, col_start:col_end])


    # The remaining methods are all private; they are not part of the
    # public interface.

    # Read the next CDG command from the file (24 bytes each)
    def __getNextPacket(self):
        packetData = map(ord, self.__cdgData[self.__cdgDataPos : self.__cdgDataPos + 24])
        self.__cdgDataPos += 24
        if (len(packetData) == 24):
            return CdgPacket(packetData)
        else:
            self.__cdgDataPos = len(self.__cdgData)
            return None

    # Decode and perform the CDG commands in the indicated packet.
    def __cdgPacketProcess (self, packd):
        if (packd.command & CDG_MASK) == CDG_COMMAND:
            inst_code = (packd.instruction & CDG_MASK)
            if inst_code == CDG_INST_MEMORY_PRESET:
                self.__cdgMemoryPreset (packd)
            elif inst_code == CDG_INST_BORDER_PRESET:
                self.__cdgBorderPreset (packd)
            elif inst_code == CDG_INST_TILE_BLOCK:
                self.__cdgTileBlockCommon(packd, xor = 0)
            elif inst_code == CDG_INST_SCROLL_PRESET:
                self.__cdgScrollPreset (packd)
            elif inst_code == CDG_INST_SCROLL_COPY:
                self.__cdgScrollCopy (packd)
            elif inst_code == CDG_INST_DEF_TRANSP_COL:
                self.__cdgDefineTransparentColour (packd)
            elif inst_code == CDG_INST_LOAD_COL_TBL_0_7:
                self.__cdgLoadColourTableCommon (packd, 0)
            elif inst_code == CDG_INST_LOAD_COL_TBL_8_15:
                self.__cdgLoadColourTableCommon (packd, 1)
            elif inst_code == CDG_INST_TILE_BLOCK_XOR:
                self.__cdgTileBlockCommon(packd, xor = 1)
            else:
                # Don't use the error popup, ignore the unsupported command
                ErrorString = "CDG file may be corrupt, cmd: " + str(inst_code)
                print (ErrorString)

    # Memory preset (clear the viewable area + border)
    def __cdgMemoryPreset (self, packd):
        colour = packd.data[0] & 0x0F
        repeat = packd.data[1] & 0x0F

        # The "repeat" flag is nonzero if this is a repeat of a
        # previously-appearing preset command.  (Often a CDG will
        # issue several copies of this command in case one gets
        # corrupted.)

        # We could ignore the entire command if repeat is nonzero, but
        # our data stream is not 100% reliable, since it might have
        # come from a bad rip.  So we should honor every preset
        # command; but we shouldn't waste CPU time clearing the screen
        # repeatedly, needlessly.  So we store a flag indicating the
        # last color that we just cleared to, and don't bother
        # clearing again if it hasn't changed.
        
        if colour == self.__justClearedColourIndex:
            return
        self.__justClearedColourIndex = colour

        # Our new interpretation of CD+G Revealed is that memory preset
        # commands should also change the border
        self.__cdgPresetColourIndex = colour
        self.__cdgBorderColourIndex = self.__cdgPresetColourIndex
        
        # Note that this may be done before any load colour table
        # commands by some CDGs. So the load colour table itself
        # actual recalculates the RGB values for all pixels when
        # the colour table changes.

        # Set the border colour for every pixel. Must be stored in 
        # the pixel colour table indeces array, as well as
        # the screen RGB surfarray.

        # NOTE: The preset area--that is, the visible area--starts at
        # (6, 12) and extends to pixel (294, 204).  The border area is
        # the two stripes of 6 pixels on the left and right of the
        # screen, and the stripes of 12 pixels on the top and bottom
        # of the screen.
        
        # The most efficient way of setting the values in a Numeric
        # array, is to create a zero array and do addition on the
        # the border and preset slices.
        self.__cdgPixelColours = N.zeros([CDG_FULL_WIDTH, CDG_FULL_HEIGHT])
        self.__cdgPixelColours[:,:] = self.__cdgPixelColours[:,:] + colour
        
        # Now set the border and preset colour in our local surfarray. 
        # This will be blitted next time there is a screen update.
        self.__cdgSurfarray = N.zeros([CDG_FULL_WIDTH, CDG_FULL_HEIGHT])
        self.__cdgSurfarray[:,:] = self.__cdgSurfarray[:,:] + self.__cdgColourTable[colour]

        self.__updatedTiles = 0xFFFFFFFFL

    # Border Preset (clear the border area only) 
    def __cdgBorderPreset (self, packd):
        colour = packd.data[0] & 0x0F
        if colour == self.__cdgBorderColourIndex:
            return
        
        self.__cdgBorderColourIndex = colour

        # See cdgMemoryPreset() for a description of what's going on.
        # In this case we are only clearing the border area.

        # Set up the border area of the pixel colours array
        self.__cdgPixelColours[:,:12] = N.zeros([CDG_FULL_WIDTH, 12])
        self.__cdgPixelColours[:,:12] = self.__cdgPixelColours[:,:12] + self.__cdgBorderColourIndex
        self.__cdgPixelColours[:,-12:] = N.zeros([CDG_FULL_WIDTH, 12])
        self.__cdgPixelColours[:,-12:] = self.__cdgPixelColours[:,-12:] + self.__cdgBorderColourIndex
        self.__cdgPixelColours[:6,12:-12] = N.zeros([6, CDG_FULL_HEIGHT - 24]) 
        self.__cdgPixelColours[:6,12:-12] = self.__cdgPixelColours[:6,12:-12] + self.__cdgBorderColourIndex
        self.__cdgPixelColours[-6:,12:-12] = N.zeros([6, CDG_FULL_HEIGHT - 24]) 
        self.__cdgPixelColours[-6:,12:-12] = self.__cdgPixelColours[-6:,12:-12] + self.__cdgBorderColourIndex

        # Now that we have set the PixelColours, apply them to
        # the Surfarray.
        lookupTable = N.array(self.__cdgColourTable)
        self.__cdgSurfarray.flat[:] = N.take(lookupTable, N.ravel(self.__cdgPixelColours))

        return

    # CDG Scroll Command - Set the scrolled in area with a fresh colour
    def __cdgScrollPreset (self, packd):
        self.__cdgScrollCommon (packd, copy = False)
        return

    # CDG Scroll Command - Wrap the scrolled out area into the opposite side
    def __cdgScrollCopy (self, packd):
        self.__cdgScrollCommon (packd, copy = True)
        return

    # Common function to handle the actual pixel scroll for Copy and Preset
    def __cdgScrollCommon (self, packd, copy):

        # Decode the scroll command parameters
        data_block = packd.data
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
        if vSCmd == 2:
            vScrollUpPixels = 12
        elif vSCmd == 1:
            vScrollDownPixels = 12

        # Scroll Horizontal- Calculate number of pixels
        hScrollLeftPixels = 0
        hScrollRightPixels = 0
        if hSCmd == 2:
            hScrollLeftPixels = 6
        elif hSCmd == 1:
            hScrollRightPixels = 6

        if hOffset != self.__hOffset or vOffset != self.__vOffset:
            # Changing the screen shift.
            self.__hOffset = min(hOffset, 5)
            self.__vOffset = min(vOffset, 11)
            self.__updatedTiles = 0xFFFFFFFFL

        if hScrollLeftPixels == 0 and \
           hScrollRightPixels == 0 and \
           vScrollUpPixels == 0 and \
           vScrollDownPixels == 0:
            # Never mind.
            return

        # Perform the actual scroll. Use surfarray and slicing to make
        # this efficient. A copy scroll (where the data scrolls round)
        # can be achieved by slicing and concatenating again.
        # For non-copy, the new slice is filled in with a new colour.
        if (copy == True):
            if (vScrollUpPixels > 0):
                self.__cdgPixelColours = N.concatenate((self.__cdgPixelColours[:,vScrollUpPixels:], self.__cdgPixelColours[:,:vScrollUpPixels]), 1)
            elif (vScrollDownPixels > 0):
                self.__cdgPixelColours = N.concatenate((self.__cdgPixelColours[:,-vScrollDownPixels:], self.__cdgPixelColours[:,:-vScrollDownPixels]), 1)
            elif (hScrollLeftPixels > 0):
                self.__cdgPixelColours = N.concatenate((self.__cdgPixelColours[hScrollLeftPixels:,:], self.__cdgPixelColours[:hScrollLeftPixels,:]), 0)
            elif (hScrollRightPixels > 0):
                self.__cdgPixelColours = N.concatenate((self.__cdgPixelColours[-hScrollRightPixels:,:], self.__cdgPixelColours[:-hScrollRightPixels,:]), 0)
        elif (copy == False):
            if (vScrollUpPixels > 0):
                copyBlockActualColour = N.zeros([CDG_FULL_WIDTH,vScrollUpPixels]) + self.__cdgColourTable[colour]
                copyBlockColourIndex = N.zeros([CDG_FULL_WIDTH,vScrollUpPixels]) + colour
                self.__cdgPixelColours = N.concatenate((self.__cdgPixelColours[:,vScrollUpPixels:], copyBlockColourIndex), 1)
            elif (vScrollDownPixels > 0):
                copyBlockActualColour = N.zeros([CDG_FULL_WIDTH,vScrollDownPixels]) + self.__cdgColourTable[colour]
                copyBlockColourIndex = N.zeros([CDG_FULL_WIDTH,vScrollDownPixels]) + colour
                self.__cdgPixelColours = N.concatenate((copyBlockColourIndex, self.__cdgPixelColours[:,:-vScrollDownPixels]), 1)
            elif (hScrollLeftPixels > 0):
                copyBlockActualColour = N.zeros([hScrollLeftPixels, CDG_FULL_HEIGHT]) + self.__cdgColourTable[colour]
                copyBlockColourIndex = N.zeros([hScrollLeftPixels, CDG_FULL_HEIGHT]) + colour
                self.__cdgPixelColours = N.concatenate((self.__cdgPixelColours[hScrollLeftPixels:,:], copyBlockColourIndex), 0)
            elif (hScrollRightPixels > 0):
                copyBlockActualColour = N.zeros([hScrollRightPixels, CDG_FULL_HEIGHT]) + self.__cdgColourTable[colour]
                copyBlockColourIndex = N.zeros([hScrollRightPixels, CDG_FULL_HEIGHT]) + colour
                self.__cdgPixelColours = N.concatenate((copyBlockColourIndex, self.__cdgPixelColours[:-hScrollRightPixels,:]), 0)

        # Now that we have scrolled the PixelColours, apply them to
        # the Surfarray.
        
        lookupTable = N.array(self.__cdgColourTable)
        self.__cdgSurfarray.flat[:] = N.take(lookupTable, N.ravel(self.__cdgPixelColours))
        
        # We have modified our local cdgSurfarray. This will be blitted to
        # the screen by cdgDisplayUpdate()
        self.__updatedTiles = 0xFFFFFFFFL

    # Set one of the colour indeces as transparent. Don't actually do anything with this
    # at the moment, as there is currently no mechanism for overlaying onto a movie file.
    def __cdgDefineTransparentColour (self, packd):
        data_block = packd.data
        colour = data_block[0] & 0x0F
        self.__cdgTransparentColour = colour
        return

    # Load the RGB value for colours 0..7 or 8..15 in the lookup table
    def __cdgLoadColourTableCommon (self, packd, table):
        if table == 0:
            colourTableStart = 0
        else:
            colourTableStart = 8
        for i in range(8):
            colourEntry = ((packd.data[2 * i] & CDG_MASK) << 8)
            colourEntry = colourEntry + (packd.data[(2 * i) + 1] & CDG_MASK)
            colourEntry = ((colourEntry & 0x3F00) >> 2) | (colourEntry & 0x003F)
            red = ((colourEntry & 0x0F00) >> 8) * 17
            green = ((colourEntry & 0x00F0) >> 4) * 17
            blue = ((colourEntry & 0x000F)) * 17
            self.__cdgColourTable[i + colourTableStart] = self.__mapperSurface.map_rgb(red, green, blue)
        # Redraw the entire screen using the new colour table. We still use the 
        # same colour indeces (0 to 15) at each pixel but these may translate to
        # new RGB colours. This handles CDGs that preset the screen before actually
        # loading the colour table. It is done in our local RGB surfarray.

        # Do this with the Numeric module operation take() which can replace all
        # values in an array by alternatives from a lookup table. This is ideal as
        # we already have an array of colour indeces (0 to 15). We can create a
        # new RGB surfarray from that by doing take() which translates the 0-15
        # into an RGB colour and stores them in the RGB surfarray.
        lookupTable = N.array(self.__cdgColourTable)
        self.__cdgSurfarray.flat[:] = N.take(lookupTable, N.ravel(self.__cdgPixelColours))

        # An alternative way of doing the above - was found to be very slightly slower.
        #self.__cdgSurfarray.flat[:] =  map(self.__cdgColourTable.__getitem__, self.__cdgPixelColours.flat)

        # Update the screen for any colour changes
        self.__updatedTiles = 0xFFFFFFFFL
        return

    # Set the colours for a 12x6 tile. The main CDG command for display data
    def __cdgTileBlockCommon(self, packd, xor):
        # Decode the command parameters
        data_block = packd.data
        if data_block[1] & 0x20:
            # I don't know why, but some disks seem to stick an extra
            # bit here to mean "ignore this command".
            return

        colour0 = data_block[0] & 0x0F
        colour1 = data_block[1] & 0x0F
        
        column_index = ((data_block[2] & 0x1F) * 12)
        row_index = ((data_block[3] & 0x3F) * 6)

        # Sanity check the x,y offset read from the CDG in case a 
        # corrupted CDG sends us outside of our array bounds
        if (column_index > (CDG_FULL_HEIGHT - 12)):
            column_index = (CDG_FULL_HEIGHT - 12)
        if (row_index > (CDG_FULL_WIDTH - 6)):
            row_index = (CDG_FULL_WIDTH - 6)

        # Set the tile update bitmasks.
        # Note that the screen update area only covers the non-border area
        # excluding the left 6 columns, and top 12 rows. Therefore when
        # calculating whether this block fits into a particular tile, we
        # add 6 or 12 to the x,y positions. Note also that each tile is 6
        # wide and 12 high, so if a block starts less than 6 columns to the
        # left of a block, it will incorporate the adjacent block. Similarly
        # any update starting less than 12 rows above a block, will also
        # incorporate the block below.

        firstRow = max((row_index - 6 - self.__hOffset) / TILE_WIDTH, 0)
        lastRow = (row_index - 1 - self.__hOffset) / TILE_WIDTH

        firstCol = max((column_index - 12 - self.__vOffset) / TILE_HEIGHT, 0)
        lastCol = (column_index - 1 - self.__vOffset) / TILE_HEIGHT

        for col in range(firstCol, lastCol + 1):
            for row in range(firstRow, lastRow + 1):
                self.__updatedTiles |= ((1 << row) << (col * 8))

        # Set the pixel array for each of the pixels in the 12x6 tile.
        # Normal = Set the colour to either colour0 or colour1 depending
        #          on whether the pixel value is 0 or 1.
        # XOR    = XOR the colour with the colour index currently there.
        for i in range (12):
            byte = (data_block[4 + i] & 0x3F)
            for j in range (6):
                pixel = (byte >> (5 - j)) & 0x01
                if xor:
                    # Tile Block XOR
                    if (pixel == 0):
                        xor_col = colour0
                    else:
                        xor_col = colour1
                    # Get the colour index currently at this location, and xor with it
                    currentColourIndex = self.__cdgPixelColours[(row_index + j), (column_index + i)]
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
                self.__cdgSurfarray[(row_index + j), (column_index + i)] = self.__cdgColourTable[new_col]
                self.__cdgPixelColours[(row_index + j), (column_index + i)] = new_col

        # Now the screen has some data on it, so a subsequent clear
        # should be respected.
        self.__justClearedColourIndex = -1
        
        # The changes to cdgSurfarray will be blitted on the next screen update
        return
