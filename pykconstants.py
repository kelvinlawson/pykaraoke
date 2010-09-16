#
# Copyright (C) 2010  Kelvin Lawson (kelvinl@users.sourceforge.net)
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

""" This module defines various constants that are used throughout
this package. """

# Environment
ENV_WINDOWS = 1
ENV_POSIX = 2
ENV_OSX = 3
ENV_GP2X = 4
ENV_UNKNOWN = 5

# States
STATE_INIT          = 0
STATE_PLAYING       = 1
STATE_PAUSED        = 2
STATE_NOT_PLAYING   = 3
STATE_CLOSING       = 4
STATE_CLOSED        = 5
STATE_CAPTURING     = 6

# GP2X joystick button mappings
GP2X_BUTTON_UP            = (0)
GP2X_BUTTON_DOWN          = (4)
GP2X_BUTTON_LEFT          = (2)
GP2X_BUTTON_RIGHT         = (6)
GP2X_BUTTON_UPLEFT        = (1)
GP2X_BUTTON_UPRIGHT       = (7)
GP2X_BUTTON_DOWNLEFT      = (3)
GP2X_BUTTON_DOWNRIGHT     = (5)
GP2X_BUTTON_CLICK         = (18)
GP2X_BUTTON_A             = (12)
GP2X_BUTTON_B             = (13)
GP2X_BUTTON_X             = (14)
GP2X_BUTTON_Y             = (15)
GP2X_BUTTON_L             = (10)
GP2X_BUTTON_R             = (11)
GP2X_BUTTON_START         = (8) 
GP2X_BUTTON_SELECT        = (9)
GP2X_BUTTON_VOLUP         = (16)
GP2X_BUTTON_VOLDOWN       = (17)

# Left and top margins
Y_BORDER = 20
X_BORDER = 20
