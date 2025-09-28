# tests/conftest.py
# Agrega la raíz del repo al sys.path para que "import src.xxx" funcione en pytest.
import sys
import os

# calculamos la ruta a la raíz del repositorio (un nivel arriba de tests/)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
