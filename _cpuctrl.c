/*
  Copyright (C) 2010  Kelvin Lawson (kelvinl@users.sourceforge.net)

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
  This module provides support for controlling the GP2X CPU speed at
  runtime, via Python.  The core GP2X code in this module is taken
  from:

    cpuctrl.c for GP2X (CPU/LCD/RAM-Tuner Version 2.0)
    Copyright (C) 2006 god_at_hell 
    original CPU-Overclocker (c) by Hermes/PS2Reality 
	the gamma-routine was provided by theoddbot
	parts (c) Rlyehs Work

    gp2xminilib.c
    GP2X minimal library v0.5 by rlyeh, 2005.
    + GP2X video library with double buffering.
    + GP2X soundring buffer library with double buffering.
    + GP2X joystick library.
*/

#include <Python.h>
#include <stdio.h>
#include <fcntl.h>
#include <sys/mman.h>

#define SYS_CLK_FREQ 7372800

static int gp2x_dev_mem_fd = -1;
static volatile unsigned short *gp2x_memregs = 0;

/* If this is not called explicitly, it will be called implicitly. */
static void
init() {
  if (gp2x_dev_mem_fd >= 0) {
    /* Already initialised. */
    return;
  }
    
  /* Get a pointer to the memory-mapped address for the GP2X control
     registers. */

  gp2x_dev_mem_fd = open("/dev/mem", O_RDWR);
  gp2x_memregs = (unsigned short *)mmap(0, 0x10000, PROT_READ|PROT_WRITE, MAP_SHARED, gp2x_dev_mem_fd, 0xc0000000);
}

/* Call this to free up resources. */
static void
shutdown() {
  if (gp2x_dev_mem_fd < 0) {
    /* Already shut down. */
    return;
  }

  munmap((void *)gp2x_memregs, 0x10000);
  gp2x_memregs = NULL;

  close(gp2x_dev_mem_fd);
  gp2x_dev_mem_fd = -1;
}

/* Sets the GP2X CPU speed to the indicated value in MHz.  Legal
   values are in the range 33 .. 340, though values greater than 266
   are overclock values and may crash the machine, depending on the
   individual. 

   Note that there the GP2X also has a separate CPU divider which is
   not modified by this function. */
static void
set_FCLK(unsigned int MHZ) {
  unsigned int v;
  unsigned int mdiv, pdiv = 3, scale = 0;

  if (gp2x_dev_mem_fd < 0) {
    /* Not initialised. */
    printf("Not setting CPU speed to %u: not initialised.\n", MHZ);
    return;
  }

  MHZ *= 1000000;
  mdiv = (MHZ * pdiv) / SYS_CLK_FREQ;
  mdiv = ((mdiv - 8) << 8) & 0xff00;
  pdiv = ((pdiv - 2) << 2) & 0xfc;
  scale &= 3;
  v = mdiv | pdiv | scale;
  
  gp2x_memregs[0x910 >> 1] = v;
}

/* Returns the current CPU speed in MHz.  Note that the GP2X also has
   a separate CPU divider which is not consulted by this function. */
static unsigned int
get_FCLK() {
  unsigned v;
  unsigned mdiv, pdiv, scale;
  unsigned MHZ;

  /* Implicitly initialise if necessary. */
  init();
  
  v = gp2x_memregs[0x910>>1];
  mdiv = ((v & 0xff00) >> 8) + 8;
  pdiv = ((v & 0xfc) >> 2) + 2;
  scale = v & 3;

  if (pdiv == 0) {
    /* This presumably isn't possible. */
    MHZ = 0;
  } else {
    MHZ = (mdiv * SYS_CLK_FREQ) / pdiv;
    MHZ = (MHZ + 500000) / 1000000;
  }
  return MHZ;
}


static PyObject *
wrapper_init() {
  init();

  Py_RETURN_NONE;
}

static PyObject *
wrapper_shutdown() {
  shutdown();

  Py_RETURN_NONE;
}

static PyObject *
wrapper_set_FCLK(PyObject *self, PyObject *args, PyObject *kwds) {
  static char *keyword_list[] = { "MHZ", NULL };
  unsigned int MHZ;

  if (!PyArg_ParseTupleAndKeywords(args, kwds, 
                                   "I:set_FCLK", 
                                   keyword_list, &MHZ)) {
    return NULL;
  }

  set_FCLK(MHZ);

  Py_RETURN_NONE;
}

static PyObject *
wrapper_get_FCLK() {
  unsigned int MHZ;

  MHZ = get_FCLK();

  if ((long)MHZ < 0) {
    return PyLong_FromUnsignedLong((unsigned long)MHZ);
  } else {
    return PyInt_FromLong((long)MHZ);
  }
}

/* Returns a 3-tuple (x, y, tvout) representing the current screen
   width and height, and true if the screen is in tv-out mode. */
static PyObject *
get_screen_info() {
  int x, y, tvout;

  /* Implicitly initialise if necessary. */
  init();
  
  x = gp2x_memregs[0x2816>>1] + 1;
  y = gp2x_memregs[0x2818>>1] + 1;
  tvout = (gp2x_memregs[0x2800>>1] & 0x100) != 0;

  if (tvout && y < 400) {
    /* Not sure why, but this is apparently off by a factor of two in
       TV mode. */
    y *= 2;
  }

  return Py_BuildValue("(iii)", x, y, tvout);
}

static PyMethodDef cpuctrl_methods[] = {
  {"init", (PyCFunction)wrapper_init, METH_NOARGS },
  {"shutdown", (PyCFunction)wrapper_shutdown, METH_NOARGS },
  {"set_FCLK", (PyCFunction)wrapper_set_FCLK, METH_VARARGS | METH_KEYWORDS },
  {"get_FCLK", (PyCFunction)wrapper_get_FCLK, METH_NOARGS },
  {"get_screen_info", (PyCFunction)get_screen_info, METH_NOARGS },
  {NULL}  /* Sentinel */
};

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
init_cpuctrl(void) {
  PyObject *m;

  m = Py_InitModule3("_cpuctrl", cpuctrl_methods, NULL);
}
