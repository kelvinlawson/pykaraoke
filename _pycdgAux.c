/*
  Copyright (C) 2005  Kelvin Lawson (kelvinl@users.sourceforge.net)

  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 2.1 of the License, or (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/

/*
  This module is the C implementation of certain classes and functions
  that have been ported to C for performance reasons.  This module
  exactly duplicates the functionality presented in pycdgAux.py (which
  is used only if this module is not available for some reason).  

  If you are reading this module for the first time, consider reading
  pycdgAux.py instead, which is logically equivalent and much easier
  to read.  If you do need to read the C code for some reason,
  consider comparing it piece-by-piece with pycdgAux.py, since there
  is a one-to-one correspondence between the methods and classes
  defined there, and those defined here.
*/

#include <Python.h>
#include <stdio.h>
#include "structmember.h"
#include "SDL.h"

/* This struct is defined just so we can pull the SDL_Surface pointer
   out of a pygame PySurfaceObject without having to include pygame.h.
   It's a hack, we really should be including pygame.h, but that looks
   like it requires more work in the setup.py than I want to do right
   now. */
typedef struct {
  PyObject_HEAD
  SDL_Surface* surf;
} PySurfaceObjectHack;
#define PySurface_AsSurface(x) (((PySurfaceObjectHack*)x)->surf)

/* CDG Command Code */
#define CDG_COMMAND                 0x09

/* CDG Instruction Codes */
#define CDG_INST_MEMORY_PRESET      1
#define CDG_INST_BORDER_PRESET      2
#define CDG_INST_TILE_BLOCK         6
#define CDG_INST_SCROLL_PRESET      20
#define CDG_INST_SCROLL_COPY        24
#define CDG_INST_DEF_TRANSP_COL     28
#define CDG_INST_LOAD_COL_TBL_0_7   30
#define CDG_INST_LOAD_COL_TBL_8_15  31
#define CDG_INST_TILE_BLOCK_XOR     38

/* Bitmask for all CDG fields */
#define CDG_MASK                    0x3F

#define CDG_DISPLAY_WIDTH           294
#define CDG_DISPLAY_HEIGHT          204

#define CDG_FULL_WIDTH              300
#define CDG_FULL_HEIGHT             216


#define TILES_PER_ROW    6
#define TILES_PER_COL    4
#define TILE_WIDTH       (CDG_DISPLAY_WIDTH / TILES_PER_ROW)
#define TILE_HEIGHT      (CDG_DISPLAY_HEIGHT / TILES_PER_COL)

#define COLOUR_TABLE_SIZE           16

/* This struct just represents a single 24-byte packet read from
   the CDG stream.  It's not used outside this module. */
typedef struct {
  unsigned char command;
  unsigned char instruction;
  unsigned char parityQ[2];
  unsigned char data[16];
  unsigned char parity[4];
} CdgPacket;

/* This struct holds the data used by the CdgPacketReader class.  It
   is exported as a Python class. */
typedef struct {
  PyObject_HEAD
  
  FILE *__cdgFile;
  
  /* This is just for the purpose of mapping colors. */
  SDL_Surface *__mapperSurface;

  int __cdgColourTable[COLOUR_TABLE_SIZE];
  int __cdgPresetColourIndex;
  int __cdgBorderColourIndex;
  int __cdgTransparentColour;

  /* This is an array of the pixel indices, including border area. */
  unsigned char __cdgPixelColours[CDG_FULL_WIDTH][CDG_FULL_HEIGHT];

  /* This is an array of the actual RGB values.  This will
     be changed by the various commands, and blitted to the
     screen now and again. But the border area will not be
     blitted, only the central 294x204 area. */
  Uint32 __cdgSurfarray[CDG_FULL_WIDTH][CDG_FULL_HEIGHT];

  unsigned int __updatedTiles;

} CdgPacketReader;

/* Forward prototypes for private methods defined within this module. */
static void do_rewind(CdgPacketReader *self);
static int __getNextPacket(CdgPacketReader *self, CdgPacket *packd);
static void __cdgPacketProcess(CdgPacketReader *self, CdgPacket *packd);
static void __cdgMemoryPreset(CdgPacketReader *self, CdgPacket *packd);
static void __cdgBorderPreset(CdgPacketReader *self, CdgPacket *packd);
static void __cdgPresetScreenCommon(CdgPacketReader *self);
static void __cdgScrollPreset(CdgPacketReader *self, CdgPacket *packd);
static void __cdgScrollCopy(CdgPacketReader *self, CdgPacket *packd);
static void __cdgScrollCommon(CdgPacketReader *self, CdgPacket *packd, int copy);
static void __cdgDefineTransparentColour(CdgPacketReader *self, CdgPacket *packd);
static void __cdgLoadColourTableCommon(CdgPacketReader *self, CdgPacket *packd, int table);
static void __cdgTileBlockCommon(CdgPacketReader *self, CdgPacket *packd, int xor);

/* The Python destructor for the CdgPacketReader class. */
static void
CdgPacketReader_dealloc(CdgPacketReader *self) {
  if (self->__cdgFile != NULL) {
    fclose(self->__cdgFile);
    self->__cdgFile = NULL;
  }
  self->ob_type->tp_free((PyObject *)self);
}

/* The Python allocator for the CdgPacketReader class.  Not to be
   confused with the initializer, below. */
static PyObject *
CdgPacketReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
  CdgPacketReader *self;

  self = (CdgPacketReader *)type->tp_alloc(type, 0);
  if (self != NULL) {
    self->__cdgFile = NULL;
    self->__mapperSurface = NULL;
  }

  return (PyObject *)self;
}

/* The Python initializer for the CdgPacketReader class.  This
   corresponds to CdgPacketReader.__init__(). */
static int
CdgPacketReader_init(CdgPacketReader *self, PyObject *args, PyObject *kwds) {
  /* Boilerplate code to extract the Python arguments passed in. */

  static char *keyword_list[] = { "fileName", "mapperSurface", NULL };
  char *fileName;
  PyObject *mapperSurface;
  if (!PyArg_ParseTupleAndKeywords(args, kwds, 
                                   "sO:CdgPacketReader.__init__", 
                                   keyword_list, &fileName, 
                                   &mapperSurface)) {
    return -1;
  }

  /* The actual function body begins here. */

  assert(self->__cdgFile == NULL);
  self->__cdgFile = fopen(fileName, "rb");
  if (self->__cdgFile == NULL) {
    PyErr_SetString(PyExc_AssertionError, "Couldn't open file");
    return -1;
  }
  self->__mapperSurface = PySurface_AsSurface(mapperSurface);

  do_rewind(self);

  return 0;
}

/* Rewinds the stream to the beginning, and resets all
   internal state in preparation for decoding the tiles
   again. */
static PyObject *
CdgPacketReader_Rewind(CdgPacketReader *self) {
  do_rewind(self);
  Py_RETURN_NONE;
}

/* The internal implementation of CdgPacketReader_Rewind(). */
static void
do_rewind(CdgPacketReader *self) {
  int defaultColour;

  assert(self->__cdgFile != NULL);
  fseek(self->__cdgFile, 0, SEEK_SET);

  defaultColour = 0;
  memset(self->__cdgColourTable, defaultColour, sizeof(int) * COLOUR_TABLE_SIZE);

  self->__cdgPresetColourIndex = -1;
  self->__cdgBorderColourIndex = -1;

  /* Support only one transparent colour */
  self->__cdgTransparentColour = -1;
    
  memset(self->__cdgPixelColours, 0, CDG_FULL_WIDTH * CDG_FULL_HEIGHT);

  memset(self->__cdgSurfarray, 0, sizeof(Uint32) * CDG_FULL_WIDTH * CDG_FULL_HEIGHT);

  /* Start with all tiles requiring update */
  self->__updatedTiles = 0xFFFFFFFF;
}

/* Marks all the tiles dirty, so that the next call to
   GetDirtyTiles() will return the complete list of tiles. */
static PyObject *
CdgPacketReader_MarkTilesDirty(CdgPacketReader *self) {
  self->__updatedTiles = 0xFFFFFFFF;
  Py_RETURN_NONE;
}

/* Returns a list of (row, col) tuples, corresponding to all
   of the currently-dirty tiles.  Then resets the list of dirty
   tiles to empty. */
static PyObject *
CdgPacketReader_GetDirtyTiles(CdgPacketReader *self) {
  int row, col;
  PyObject *tiles;

  tiles = PyList_New(0);

  if (self->__updatedTiles != 0) {
    for (col = 0; col < TILES_PER_COL; ++col) {
      for (row = 0; row < TILES_PER_ROW; ++row) {
        if (self->__updatedTiles & ((1 << row) << (col * 8))) {
          PyObject *tuple = PyTuple_New(2);
          PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(row));
          PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(col));
          PyList_Append(tiles, tuple);
          Py_DECREF(tuple);
        }
      }
    }
  }

  self->__updatedTiles = 0;

  return tiles;
}

/* Returns the current border colour, as a mapped integer
   ready to apply to the surface.  Returns None if the border
   colour has not yet been specified by the CDG stream. */
static PyObject *
CdgPacketReader_GetBorderColour(CdgPacketReader *self) {
  if (self->__cdgBorderColourIndex == -1) {
    Py_RETURN_NONE;
  }

  return PyInt_FromLong(self->__cdgColourTable[self->__cdgBorderColourIndex]);
}

/* Reads numPackets 24-byte packets from the CDG stream, and
   processes their instructions on the internal tables stored
   within this object.  Returns True on success, or False when
   the end-of-file has been reached and no more packets can be
   processed. */
static PyObject *
CdgPacketReader_DoPackets(CdgPacketReader *self, PyObject *args, PyObject *kwds) {
  static char *keyword_list[] = { "numPackets", NULL };
  int numPackets;
  int i;
  CdgPacket packd;

  /* Boilerplate code to extract the Python arguments passed in. */

  if (!PyArg_ParseTupleAndKeywords(args, kwds, 
                                   "i:CdgPacketReader.DoPackets", 
                                   keyword_list, &numPackets)) {
    return NULL;
  }

  /* The actual function body begins here. */

  for (i = 0; i < numPackets; ++i) {
    /* Extract the next packet */
    if (!__getNextPacket(self, &packd)) {
      /* No more packets.  Return False, but only if we
         reached this condition on the first packet. */
      if (i != 0) {
        Py_RETURN_TRUE;
      } else {
        Py_RETURN_FALSE;
      }
    }

    __cdgPacketProcess(self, &packd);
  }

  Py_RETURN_TRUE;
}

/* Fills in the pixels on the indicated one-tile surface
   (which must be a TILE_WIDTH x TILE_HEIGHT sized surface) with
   the pixels from the indicated tile. */
static PyObject *
CdgPacketReader_FillTile(CdgPacketReader *self, PyObject *args, PyObject *kwds) {
  static char *keyword_list[] = { "surface", "row", "col", NULL };
  PyObject *py_surface;
  int row, col;
  SDL_Surface *surface;
  int row_start, row_end, col_start, col_end;
  int ri, ci;
  int pitch;
  Uint8 *start;
  Uint8 *pixels8;
  Uint16 *pixels16;
  Uint32 *pixels32;

  /* Boilerplate code to extract the Python arguments passed in. */

  if (!PyArg_ParseTupleAndKeywords(args, kwds, 
                                   "Oii:CdgPacketReader.FillTile", 
                                   keyword_list, &py_surface,
                                   &row, &col)) {
    return NULL;
  }

  surface = PySurface_AsSurface(py_surface);

  /* The actual function body begins here. */

  /* Calculate the row & column starts/ends */
  row_start = 6 + (row * TILE_WIDTH);
  row_end = 6 + ((row + 1) * TILE_WIDTH);
  col_start = 12 + (col * TILE_HEIGHT);
  col_end = 12 + ((col + 1) * TILE_HEIGHT);

  SDL_LockSurface(surface);
  start = (Uint8 *)surface->pixels;
  pitch = surface->pitch;

  switch (surface->format->BytesPerPixel) {
  case 1:
    for (ci = col_start; ci < col_end; ++ci) {
      pixels8 = start;
      start += pitch;
      for (ri = row_start; ri < row_end; ++ri) {
        (*pixels8++) = self->__cdgSurfarray[ri][ci];
      }
    }
    break;

  case 2:
    for (ci = col_start; ci < col_end; ++ci) {
      pixels16 = (Uint16 *)start;
      start += pitch;
      for (ri = row_start; ri < row_end; ++ri) {
        (*pixels16++) = self->__cdgSurfarray[ri][ci];
      }
    }
    break;

  case 4:
    for (ci = col_start; ci < col_end; ++ci) {
      pixels32 = (Uint32 *)start;
      start += pitch;
      for (ri = row_start; ri < row_end; ++ri) {
        (*pixels32++) = self->__cdgSurfarray[ri][ci];
      }
    }
    break;

  default:
    fprintf(stderr, "No code to fill %d-byte pixels.\n", surface->format->BytesPerPixel);
  }
  SDL_UnlockSurface(surface);

  Py_RETURN_NONE;
}


/*  The remaining methods are all private; they are not part of the
    public interface.  As such, there's no need to wrap any of these
    with the klunky Python calling interface. */


/* Read the next CDG command from the file (24 bytes each) */
static int
__getNextPacket(CdgPacketReader *self, CdgPacket *packd) {
  size_t objsRead;

  assert(self->__cdgFile != NULL);

  objsRead = fread(packd, sizeof(*packd), 1, self->__cdgFile);
  if (objsRead != 1) {
    /* End of file. */
    return 0;
  }

  return 1;
}

/* Decode and perform the CDG commands in the indicated packet. */
static void
__cdgPacketProcess(CdgPacketReader *self, CdgPacket *packd) {
  int inst_code;

  if ((packd->command & CDG_MASK) == CDG_COMMAND) {
    inst_code = (packd->instruction & CDG_MASK);
    switch (inst_code) {
    case CDG_INST_MEMORY_PRESET:
      __cdgMemoryPreset(self, packd);
      break;

    case CDG_INST_BORDER_PRESET:
      __cdgBorderPreset(self, packd);
      break;
      
    case CDG_INST_TILE_BLOCK:
      __cdgTileBlockCommon(self, packd, 0);
      break;

    case CDG_INST_SCROLL_PRESET:
      __cdgScrollPreset(self, packd);
      break;

    case CDG_INST_SCROLL_COPY:
      __cdgScrollCopy(self, packd);
      break;

    case CDG_INST_DEF_TRANSP_COL:
      __cdgDefineTransparentColour(self, packd);
      break;

    case CDG_INST_LOAD_COL_TBL_0_7:
      __cdgLoadColourTableCommon(self, packd, 0);
      break;

    case CDG_INST_LOAD_COL_TBL_8_15:
      __cdgLoadColourTableCommon(self, packd, 1);
      break;

    case CDG_INST_TILE_BLOCK_XOR:
      __cdgTileBlockCommon(self, packd, 1);
      break;

    default:
      /* Don't use the error popup, ignore the unsupported command */
      fprintf(stderr, "CDG file may be corrupt, cmd: %d\n", inst_code);
    }
  }
}

/* Set the preset colour */
static void
__cdgMemoryPreset(CdgPacketReader *self, CdgPacket *packd) {
  int colour;

  colour = packd->data[0] & 0x0F;
  /* Ignore repeat because this is a reliable data stream */
  /* repeat = packd->data[1] & 0x0F; */

  self->__cdgPresetColourIndex = colour;
  if (self->__cdgBorderColourIndex == -1) {
    self->__cdgBorderColourIndex = self->__cdgPresetColourIndex;
  }
  __cdgPresetScreenCommon(self);
}

/* Set the border colour */
static void
__cdgBorderPreset(CdgPacketReader *self, CdgPacket *packd) {
  int colour;

  colour = packd->data[0] & 0x0F;
  self->__cdgBorderColourIndex = colour;
  if (self->__cdgPresetColourIndex == -1) {
    self->__cdgPresetColourIndex = self->__cdgBorderColourIndex;
  }
  __cdgPresetScreenCommon(self);
}

/* Common function for border and preset colours, to set the pixels */
static void
__cdgPresetScreenCommon(CdgPacketReader *self) {
  /* Note that this may be done before any load colour table
     commands by some CDGs. So the load colour table itself
     actual recalculates the RGB values for all pixels when
     the colour table changes. */

  int ri, ci;
  int borderColourIndex = self->__cdgBorderColourIndex;
  Uint32 borderColour = self->__cdgColourTable[borderColourIndex];
  int presetColourIndex = self->__cdgPresetColourIndex;
  Uint32 presetColour = self->__cdgColourTable[presetColourIndex];

  /* Set the border colour for every pixel. Must be stored in 
     the pixel colour table indeces array, as well as
     the screen RGB surfarray.
     NOTE: The preset area starts at (6,12) and extends all
     the way to the right and bottom edges. */

  /* Also set the border and preset colour in our local surfarray.
     This will be blitted next time there is a screen update. */

  for (ri = 0; ri < CDG_FULL_WIDTH; ++ri) {
    for (ci = 0; ci < 12; ++ci) {
      self->__cdgPixelColours[ri][ci] = borderColourIndex;
      self->__cdgSurfarray[ri][ci] = borderColour;
    }
  }
  for (ri = 0; ri < 6; ++ri) {
    for (ci = 12; ci < CDG_FULL_HEIGHT; ++ci) {
      self->__cdgPixelColours[ri][ci] = borderColourIndex;
      self->__cdgSurfarray[ri][ci] = borderColour;
    }
  }
  for (ri = 6; ri < CDG_FULL_WIDTH; ++ri) {
    for (ci = 12; ci < CDG_FULL_HEIGHT; ++ci) {
      self->__cdgPixelColours[ri][ci] = presetColourIndex;
      self->__cdgSurfarray[ri][ci] = presetColour;
    }
  }

  self->__updatedTiles = 0xFFFFFFFF;
}

/* CDG Scroll Command - Set the scrolled in area with a fresh colour */
static void
__cdgScrollPreset(CdgPacketReader *self, CdgPacket *packd) {
  __cdgScrollCommon(self, packd, 0);
}

/* CDG Scroll Command - Wrap the scrolled out area into the opposite side */
static void
__cdgScrollCopy(CdgPacketReader *self, CdgPacket *packd) {
  __cdgScrollCommon(self, packd, 1);
}

/* Common function to handle the actual pixel scroll for Copy and Preset */
static void
__cdgScrollCommon(CdgPacketReader *self, CdgPacket *packd, int copy) {
  int colour, hScroll, vScroll, hSCmd, hOffset, vSCmd, vOffset;
  int vScrollPixels, hScrollPixels;
  int vInc, hInc;
  int ri, ci;
  unsigned char temp[CDG_FULL_WIDTH][CDG_FULL_HEIGHT];

  /* Decode the scroll command parameters */
  colour = packd->data[0] & 0x0F;
  hScroll = packd->data[1] & 0x3F;
  vScroll = packd->data[2] & 0x3F;
  hSCmd = (hScroll & 0x30) >> 4;
  hOffset = (hScroll & 0x07);
  vSCmd = (vScroll & 0x30) >> 4;
  vOffset = (vScroll & 0x0F);

  /* Scroll Vertical - Calculate number of pixels */
  vScrollPixels = 0;
  if (vSCmd == 2 && vOffset == 0) {
    vScrollPixels = -12;
  } else if (vSCmd == 2) {
    vScrollPixels = -vOffset;
  } else if (vSCmd == 1 && vOffset == 0) {
    vScrollPixels = 12;
  } else if (vSCmd == 1) {
    vScrollPixels = vOffset;
  }

  /* Scroll Horizontal- Calculate number of pixels */
  hScrollPixels = 0;
  if (hSCmd == 2 && hOffset == 0) {
    hScrollPixels = 6;
  } else if (hSCmd == 2) {
    hScrollPixels = hOffset;
  } else if (hSCmd == 1 && hOffset == 0) {
    hScrollPixels = -6;
  } else if (hSCmd == 1) {
    hScrollPixels = -hOffset;
  }

  /* Perform the actual scroll. */

  /* NOTE: Only Vertical Scroll with Copy has been tested as no CDGs
     were available with horizontal scrolling or Scroll Preset. */

  /* For the circular add, we add hScrollPixels and then modulo
     CDG_FULL_WIDTH.  We also add CDG_FULL_WIDTH before the modulo to
     avoid a negative increment (which doesn't work properly with the
     C modulo operator).  A similar story in the vertical direction. */
  hInc = hScrollPixels + CDG_FULL_WIDTH;
  vInc = vScrollPixels + CDG_FULL_HEIGHT;
  for (ri = 0; ri < CDG_FULL_WIDTH; ++ri) {
    for (ci = 0; ci < CDG_FULL_HEIGHT; ++ci) {
      temp[(ri + hInc) % CDG_FULL_WIDTH][(ci + vInc) % CDG_FULL_HEIGHT] = 
        self->__cdgPixelColours[ri][ci];
    }
  }

  /* We just performed a circular scroll: the pixels that scrolled off
     the side were copied back in on the opposite side.  But if copy
     is false, we were supposed to fill in the new pixels with a new
     colour.  Go back and do that now. */
  if (!copy) {
    if (vScrollPixels > 0) {
      for (ri = 0; ri < CDG_FULL_WIDTH; ++ri) {
        for (ci = 0; ci < vScrollPixels; ++ci) {
          temp[ri][ci] = colour;
        }
      }
    } else if (vScrollPixels < 0) {
      for (ri = 0; ri < CDG_FULL_WIDTH; ++ri) {
        for (ci = CDG_FULL_HEIGHT + vScrollPixels; ci < CDG_FULL_HEIGHT; ++ci) {
          temp[ri][ci] = colour;
        }
      }
    }
    if (hScrollPixels > 0) {
      for (ri = 0; ri < hScrollPixels; ++ri) {
        for (ci = 0; ci < CDG_FULL_HEIGHT; ++ci) {
          temp[ri][ci] = colour;
        }
      }
    } else if (hScrollPixels < 0) {
      for (ri = CDG_FULL_WIDTH + hScrollPixels; ri < CDG_FULL_WIDTH; ++ri) {
        for (ci = 0; ci < CDG_FULL_HEIGHT; ++ci) {
          temp[ri][ci] = colour;
        }
      }
    }
  }

  /* Now copy the temporary buffer back to our array. */
  memcpy(self->__cdgPixelColours, temp, CDG_FULL_WIDTH * CDG_FULL_HEIGHT);

  /* We have now scrolled cdgPixelColours array.  Now apply that to
     cdgSurfarray by reapplying the colour indices. */
  for (ri = 6; ri < CDG_FULL_WIDTH; ++ri) {
    for (ci = 12; ci < CDG_FULL_HEIGHT; ++ci) {
      self->__cdgSurfarray[ri][ci] = self->__cdgColourTable[temp[ri][ci]];
    }
  }

  /* We have modified our local cdgSurfarray. This will be blitted to
     the screen by cdgDisplayUpdate(). */
  self->__updatedTiles = 0xFFFFFFFF;
}

/* Set one of the colour indeces as transparent. Don't actually do
   anything with this at the moment, as there is currently no
   mechanism for overlaying onto a movie file. */
static void
__cdgDefineTransparentColour(CdgPacketReader *self, CdgPacket *packd) {
  self->__cdgTransparentColour = packd->data[0] & 0x0F;
}

/* Load the RGB value for colours 0..7 or 8..15 in the lookup table */
static void
__cdgLoadColourTableCommon(CdgPacketReader *self, CdgPacket *packd, int table) {
  int colourTableStart;
  int i;
  int colourEntry;
  int red, green, blue;
  int ri, ci;

  if (table == 0) {
    colourTableStart = 0;
  } else {
    colourTableStart = 8;
  }

  for (i = 0; i < 8; ++i) {
    colourEntry = ((packd->data[2 * i] & CDG_MASK) << 8);
    colourEntry = colourEntry + (packd->data[(2 * i) + 1] & CDG_MASK);
    colourEntry = ((colourEntry & 0x3F00) >> 2) | (colourEntry & 0x003F);

    red = ((colourEntry & 0x0F00) >> 8) * 17;
    green = ((colourEntry & 0x00F0) >> 4) * 17;
    blue = ((colourEntry & 0x000F)) * 17;

    self->__cdgColourTable[i + colourTableStart] = SDL_MapRGB(self->__mapperSurface->format, red, green, blue);
  }

  /* Redraw the entire screen using the new colour table. We still use the 
     same colour indeces (0 to 15) at each pixel but these may translate to
     new RGB colours. This handles CDGs that preset the screen before actually
     loading the colour table. It is done in our local RGB surfarray. */

  for (ri = 6; ri < CDG_FULL_WIDTH; ++ri) {
    for (ci = 12; ci < CDG_FULL_HEIGHT; ++ci) {
      self->__cdgSurfarray[ri][ci] = self->__cdgColourTable[self->__cdgPixelColours[ri][ci]];
    }
  }

  /* Update the screen for any colour changes */
  self->__updatedTiles = 0xFFFFFFFF;
}

static void
__cdgTileBlockCommon(CdgPacketReader *self, CdgPacket *packd, int xor) {
  int colour0, colour1;
  int column_index, row_index;
  int col, row;
  int i, j, byte, pixel, xor_col, currentColourIndex, new_col;

  colour0 = packd->data[0] & 0x0f;
  colour1 = packd->data[1] & 0x0f;
  column_index = ((packd->data[2] & 0x1f) * 12);
  row_index = ((packd->data[3] & 0x3f) * 6);

  for (col = 0; col < TILES_PER_COL; ++col) {
    for (row = 0; row < TILES_PER_ROW; ++row) {
      if ((row_index >= (TILE_WIDTH * row))                    
          && (row_index <= 6 + (TILE_WIDTH * (row + 1)))      
          && (column_index >= (TILE_HEIGHT * col))                    
          && (column_index <= 12 + (TILE_HEIGHT * (col + 1)))) {
        self->__updatedTiles |= ((1 << row) << (col * 8));
      }
    }
  }

  /*
    Set the pixel array for each of the pixels in the 12x6 tile.
    Normal = Set the colour to either colour0 or colour1 depending
    on whether the pixel value is 0 or 1.
    XOR    = XOR the colour with the colour index currently there.
  */
  for (i = 0; i < 12; ++i) {
    byte = (packd->data[4 + i] & 0x3F);
    for (j = 0; j < 6; ++j) {
      pixel = (byte >> (5 - j)) & 0x01;
      if (xor) {
        /* Tile Block XOR */
        if (pixel == 0) {
          xor_col = colour0;
        } else {
          xor_col = colour1;
        }
        /* Get the colour index currently at this location, and xor with it */
        currentColourIndex = self->__cdgPixelColours[row_index + j][column_index + i];
        new_col = currentColourIndex ^ xor_col;

      } else {
        if (pixel == 0) {
          new_col = colour0;
        } else {
          new_col = colour1;
        }
      }

      /* Set the pixel with the new colour. We set both the surfarray
         containing actual RGB values, as well as our array containing
         the colour indeces into our colour table. */
      self->__cdgSurfarray[row_index + j][column_index + i] = self->__cdgColourTable[new_col];
      self->__cdgPixelColours[row_index + j][column_index + i] = new_col;      
    }
  }
}

/* The rest of the lines in this module are boilerplate Python
   constructs to formally export the appropriate the classes and
   methods from this module. */

static PyMethodDef CdgPacketReader_methods[] = {
  {"Rewind", (PyCFunction)CdgPacketReader_Rewind, METH_NOARGS },
  {"MarkTilesDirty", (PyCFunction)CdgPacketReader_MarkTilesDirty, METH_NOARGS },
  {"GetDirtyTiles", (PyCFunction)CdgPacketReader_GetDirtyTiles, METH_NOARGS },
  {"GetBorderColour", (PyCFunction)CdgPacketReader_GetBorderColour, METH_NOARGS },
  {"DoPackets", (PyCFunction)CdgPacketReader_DoPackets, METH_VARARGS | METH_KEYWORDS },
  {"FillTile", (PyCFunction)CdgPacketReader_FillTile, METH_VARARGS | METH_KEYWORDS },
  {NULL}  /* Sentinel */
};

static PyTypeObject CdgPacketReaderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size */
    "_pycdgAux.CdgPacketReader",  /* tp_name */
    sizeof(CdgPacketReader),   /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)CdgPacketReader_dealloc,  /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_compare */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,        /* tp_flags */
    0,                         /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    CdgPacketReader_methods,   /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)CdgPacketReader_init,  /* tp_init */
    0,                         /* tp_alloc */
    CdgPacketReader_new,       /* tp_new */
};



static PyMethodDef pycdgAux_methods[] = {
  {NULL}  /* Sentinel */
};

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
init_pycdgAux(void) {
  PyObject* m;

  CdgPacketReaderType.tp_new = CdgPacketReader_new;
  if (PyType_Ready(&CdgPacketReaderType) < 0) {
    return;
  }
  
  m = Py_InitModule3("_pycdgAux", pycdgAux_methods, NULL);

  Py_INCREF(&CdgPacketReaderType);
  PyModule_AddObject(m, "CdgPacketReader", (PyObject *)&CdgPacketReaderType);
}
