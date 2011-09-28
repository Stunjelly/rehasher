from distutils.core import setup
import py2exe

setup(
    name = 'Stunjelly EPUB rehasher',
    description = 'Tool to rehash EPUB files for iPad cache avoidance',
    version = '1.01',
    dest_base = "Stunjelly-Rehasher",

    windows = [
                  {
                      'script': 'main.py',
                      "icon_resources": [(1, "images/logo.ico")]
                  }
              ],

    options = {
                  'py2exe': {
                      'packages': ['encodings', 'lib', 'gtk.glade'],
                      'includes': 'cairo, pango, pangocairo, atk, gobject, gio, gtk',
                      "skip_archive": False,
                      "optimize": 2
                  }
              },

    data_files=[
                   ('gui',['gui/main.glade']),('images',['images/logo2.png']), 
               ]
)