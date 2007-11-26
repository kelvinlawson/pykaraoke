#
# Copyright (C) 2007  Kelvin Lawson (kelvinl@users.sourceforge.net)
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

""" This module guesses the execution environment of the application. """

from pykconstants import *
import os

# Try to guess which environment we're running in.
env = 0
if os.name == "posix":
    (uname, host, release, version, machine) = os.uname()
    if host == "gp2x":
        env = ENV_GP2X
    elif (uname.lower()[:5] == "linux"):
        env = ENV_LINUX
    else:
        env = ENV_OSX
else:
    env = ENV_WINDOWS

#env = ENV_GP2X
