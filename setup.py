#!/usr/bin/env python
#******************************************************************************
#****                                                                      ****
#**** Copyright (C) 2007  Kelvin Lawson (kelvinl@users.sourceforge.net)    ****
#**** Copyright (C) 2009  PyKaraoke Development Team                       ****
#****                                                                      ****
#**** This library is free software; you can redistribute it and/or        ****
#**** modify it under the terms of the GNU Lesser General Public           ****
#**** License as published by the Free Software Foundation; either         ****
#**** version 2.1 of the License, or (at your option) any later version.   ****
#****                                                                      ****
#**** This library is distributed in the hope that it will be useful,      ****
#**** but WITHOUT ANY WARRANTY; without even the implied warranty of       ****
#**** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU    ****
#**** Lesser General Public License for more details.                      ****
#****                                                                      ****
#**** You should have received a copy of the GNU Lesser General Public     ****
#**** License along with this library; if not, write to the                ****
#**** Free Software Foundation, Inc.                                       ****
#**** 59 Temple Place, Suite 330                                           ****
#**** Boston, MA  02111-1307  USA                                          ****
#******************************************************************************

from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext
import pykversion
import sys
import glob
from pykenv import *

import wxversion
wxversion.ensureMinimal('2.6')
import wx

# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords
if sys.version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

gotPy2exe = 0
if env == ENV_WINDOWS:
    # On Windows, we use py2exe to build a binary executable.  But we
    # don't require it, since even without it it's still possible to
    # use distutils to install pykaraoke as a standard Python module.
    try:
        import py2exe
        gotPy2exe = True
    except ImportError:
        pass

# These are the data files that should be installed for all systems,
# including Windows.

data_files = [
    ('share/pykaraoke/icons',
     ['icons/audio_16.png',
      'icons/folder_close_16.png',
      'icons/folder_open_16.png',
      'icons/microphone.ico',
      'icons/microphone.png',
      'icons/pykaraoke.xpm',
      'icons/splash.png']),
    ('share/pykaraoke/fonts', [
    'fonts/DejaVuSans.ttf',
    'fonts/DejaVuSansCondensed.ttf',
    'fonts/DejaVuSansCondensed-Bold.ttf',
    ])]

# These data files only make sense on Unix-like systems.
if env != ENV_WINDOWS:
    data_files += [
        ('bin', ['install/pykaraoke',
                 'install/pykaraoke_mini',
                 'install/pycdg',
                 'install/pykar',
                 'install/pympg',
                 'install/cdg2mpg']),
        ('share/applications', ['install/pykaraoke.desktop',
                                'install/pykaraoke_mini.desktop'])]

# These are the basic keyword arguments we will pass to distutil's
# setup() function.
cmdclass = {}
setupArgs = {
  'name' : "pykaraoke",
  'version' : pykversion.PYKARAOKE_VERSION_STRING,
  'description' : 'PyKaraoke = CD+G/MPEG/KAR Karaoke Player',
  'maintainer' : 'Kelvin Lawson',
  'maintainer_email' : 'kelvin@kibosh.org',
  'url' : 'http://www.kibosh.org/pykaraoke',
  'license' : 'LGPL',
  'long_description' : 'PyKaraoke - CD+G/MPEG/KAR Karaoke Player',
  'py_modules' : [ "pycdgAux", "pycdg", "pykaraoke_mini",
                   "pykaraoke", "pykar", "pykconstants",
                   "pykdb", "pykenv", "pykmanager",
                   "pykplayer", "pykversion", "pympg", "performer_prompt" ],
  'ext_modules' : [Extension("_pycdgAux", ["_pycdgAux.c"],
                             libraries = ['SDL'])],
  'data_files' : data_files,
  'cmdclass' : cmdclass,
  'classifiers' : ['Development Status :: 5 - Production/Stable',
                   'Environment :: X11 Applications',
                   'Environment :: Win32 (MS Windows)',
                   'Intended Audience :: End Users/Desktop',
                   'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
                   'Operating System :: Microsoft :: Windows',
                   'Operating System :: POSIX',
                   'Programming Language :: Python',
                   'Topic :: Games/Entertainment',
                   'Topic :: Multimedia :: Sound/Audio :: Players'],
  }

# Let's extend build_ext so we can allow the user to specify
# explicitly the location of the SDL installation (or we can try to
# guess where it might be.)
class my_build_ext(build_ext):
    user_options = build_ext.user_options
    user_options += [('sdl-location=', None,
                      "Specify the path to the SDL source directory, assuming sdl_location/include and sdl_location/lib exist beneath that.  (Otherwise, use --include-dirs and --library-dirs.)"),
                     ]

    def initialize_options(self):
        build_ext.initialize_options(self)
        self.sdl_location = None

    def finalize_options(self):
        build_ext.finalize_options(self)
        if self.sdl_location is None:

            # The default SDL location.  This is useful only if your
            # SDL source is installed under a common root, with
            # sdl_loc/include and sdl_loc/lib directories beneath that
            # root.  This is the standard way that SDL is distributed
            # on Windows, but not on Unix.  For a different
            # configuration, just specify --include-dirs and
            # --library-dirs separately.

            if env == ENV_WINDOWS:
                # For a default location on Windows, look around for SDL
                # in the current directory.
                sdl_dirs = glob.glob('SDL*')

                # Sort them in order, so that the highest-numbered version
                # will (probably) fall to the end.
                sdl_dirs.sort()

                for dir in sdl_dirs:
                    if os.path.isdir(os.path.join(dir, 'include')):
                        self.sdl_location = dir

        if self.sdl_location is not None:
            # Now append the system paths.
            self.include_dirs.append(os.path.join(self.sdl_location, 'include'))
            self.library_dirs.append(os.path.join(self.sdl_location, 'lib'))

            # Also put the lib dir on the PATH, so py2exe can find SDL.dll.
            if env == ENV_WINDOWS:
                libdir = os.path.join(self.sdl_location, 'lib')
                os.environ["PATH"] = '%s;%s' % (libdir, os.environ["PATH"])


cmdclass['build_ext'] = my_build_ext


# On Windows, we might want to build an installer.  This means
# subclassing from py2exe to add new behavior.
if gotPy2exe:
    class BuildInstaller(py2exe.build_exe.py2exe):

        user_options = py2exe.build_exe.py2exe.user_options
        user_options += [('makensis=', None,
                          "path to makensis.exe, the NSIS compiler."),
                         ]

        def isSystemDLL(self, pathname):
            # Trap and flag as non-system DLLs those that py2exe
            # would otherwise get incorrect.
            if os.path.basename(pathname).lower() in ["sdl_ttf.dll"]:
                return 0
            elif os.path.basename(pathname).lower() in ["libogg-0.dll"]:
                return 0
            else:
                return self.origIsSystemDLL(pathname)

        def initialize_options(self):
            py2exe.build_exe.py2exe.initialize_options(self)
            self.makensis = None

        def finalize_options(self):
            py2exe.build_exe.py2exe.finalize_options(self)
            if self.makensis is None:
                try:
                    import win32api
                    self.makensis = win32api.FindExecutable('makensis')
                except:
                    # Default path for makensis.  This is where it gets
                    # installed by default.
                    self.makensis = os.path.join(os.environ['ProgramFiles'], 'NSIS\\makensis')

        def run(self):
            # Make sure the dist directory doesn't exist already--make
            # the user delete it first if it does.  (This is safer
            # than calling rm_rf() on it, in case the user has
            # specified '/' or some equally foolish directory as the
            # dist directory.)
            if os.path.exists(self.dist_dir):
                print "Error, the directory %s already exists." % (self.dist_dir)
                print "Please remove it before starting this script."
                sys.exit(1)

            # Override py2exe's isSystemDLL because it erroneously
            # flags sdl_ttf.dll and libogg-0.dll as system DLLs
            self.origIsSystemDLL = py2exe.build_exe.isSystemDLL
            py2exe.build_exe.isSystemDLL = self.isSystemDLL

            # Build the .exe files, etc.
            py2exe.build_exe.py2exe.run(self)

            # Now run NSIS to build the installer.
            cmd = '"%(makensis)s" /DVERSION=%(version)s install\\windows_installer.nsi' % {
                'makensis' : self.makensis,
                'version' : pykversion.PYKARAOKE_VERSION_STRING,
                }
            print cmd
            os.system(cmd)

            # Now that we've got an installer, we can empty the dist
            # dir again.
            self.rm_rf(self.dist_dir)

        def rm_rf(self, dirname):
            """Recursively removes a directory's contents."""
            if os.path.isdir(dirname):
                for root, dirs, files in os.walk(dirname, topdown=False):
                    for name in files:
                        pathname = os.path.join(root, name)
                        try:
                            os.remove(pathname)
                        except:
                            # Try to make it writable first, then remove it.
                            os.chmod(pathname, 0666)
                            os.remove(pathname)

                    for name in dirs:
                        pathname = os.path.join(root, name)
                        os.rmdir(pathname)
                os.rmdir(dirname)

    cmdclass['nsis'] = BuildInstaller

    # tell py2exe what the front end applications are.
    setupArgs['windows'] = [
        { "script": "pykaraoke.py",
          "icon_resources" : [(0, "icons\\microphone.ico")],
        },
        { "script": "pykaraoke_mini.py",
          "icon_resources" : [(0, "icons\\microphone.ico")],
        },
        ]

setup(**setupArgs)
