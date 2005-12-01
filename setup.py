from distutils.core import setup
import pykversion

setup(name="pykaraoke",
      version=pykversion.PYKARAOKE_VERSION_STRING,
      py_modules=["pykaraoke", "pycdg","pympg","pykar","pykversion"],
      data_files=[('bin', ['install/pykaraoke',
                           'install/pycdg',
                           'install/pykar',
                           'install/pympg']),
                  ('share/pykaraoke/icons',
                       ['icons/audio_16.png',
                        'icons/folder_close_16.png',
                        'icons/folder_open_16.png', 
                        'icons/note.ico']),
                  ('share/pykaraoke/fonts', ['fonts/vera.ttf'])])
