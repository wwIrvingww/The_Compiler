# conftest.py

import sys
import os

# Inserta la carpeta del proyecto (donde está src/) en sys.path
ROOT = os.path.dirname(__file__)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
