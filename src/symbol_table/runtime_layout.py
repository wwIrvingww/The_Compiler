# src/symbol_table/runtime_layout.py
"""
Runtime layout / Frame manager.

Proporciona:
- FrameManager: crea y gestiona frames (por función), asigna offsets a parámetros
  y variables locales, y registra la metadata runtime en los símbolos existentes.
- Convención:
    * Parámetros: offsets incrementales desde 0 (offset positivo relativo al base pointer).
    * Locales: offsets negativos desde -align (ej. -4, -8, ...) (relativo al base pointer / stack pointer).
  Esto es una convención simple y coherente con muchos esquemas de calling frame.
- Tamaños por tipo: por defecto 'integer' -> 4, 'float'/'double' -> 8, 'boolean' -> 1, etc.
  Puedes pasar size explícito a allocate_param/allocate_local si lo prefieres.
- Thread-safe para uso concurrente en pipelines (usa un lock en el manager).

Uso típico:
    fm = FrameManager()
    fm.enter_frame("main")
    fm.allocate_param("x", "integer")        # offset 0
    fm.allocate_param("y", "float")          # offset 4 (aligned)
    fm.allocate_local("tmp", "integer")      # offset -4
    fm.attach_runtime_info(symbol_table, "x", "main", category="param")
    fm.attach_runtime_info(symbol_table, "tmp", "main", category="local")
    layout = fm.frame_layout("main")
"""

from __future__ import annotations
from typing import Dict, Optional, Tuple, List
import threading
import math

# Import local Symbol class using relative import (same package)
try:
    from .symbol_table import Symbol, SymbolTable
except Exception:  # pragma: no cover - fallback for direct execution in other envs
    # NOTE: if this file is executed outside the package context, imports may need adjusting.
    Symbol = None
    SymbolTable = None


def _align(value: int, align: int) -> int:
    """Align value (positive integer) up to multiple of align."""
    if align <= 0:
        return value
    return int(math.ceil(value / align) * align)


class Frame:
    """
    Representación simple de un activation record (frame).
    Parámetros:
      - name: id del frame (normalmente nombre de función).
      - param_offset_cursor: próxima posición (byte) libre para parámetros (crece >= 0).
      - local_offset_cursor: próxima posición (byte) libre para locales (crece en negativo: -4, -8, ...).
      - alignment: alineamiento mínimo en bytes (default 4).
    """

    def __init__(self, name: str, alignment: int = 4):
        self.name: str = name
        self.alignment: int = int(alignment) if alignment > 0 else 4
        self._param_cursor: int = 0  # next free param offset (positive)
        self._local_cursor: int = -self.alignment  # start negative
        # maps name -> (offset, size, category)
        self.params: Dict[str, Tuple[int, int, str]] = {}
        self.locals: Dict[str, Tuple[int, int, str]] = {}
        # total footprint (computed lazily)
        self._finalized: bool = False

    def allocate_param(self, name: str, size: int, category: str = "param") -> int:
        """
        Asigna un slot de parámetro y devuelve su offset (>=0).
        Lanza KeyError si el nombre ya está asignado en params.
        """
        if name in self.params:
            raise KeyError(f"Parameter '{name}' already allocated in frame '{self.name}'")
        # align cursor before assignment
        off = _align(self._param_cursor, self.alignment)
        self.params[name] = (off, size, category)
        self._param_cursor = off + size
        self._finalized = False
        return off

    def allocate_local(self, name: str, size: int, category: str = "local") -> int:
        """
        Asigna un slot local y devuelve su offset (negativo).
        Lanza KeyError si el nombre ya está asignado en locals.
        """
        if name in self.locals:
            raise KeyError(f"Local '{name}' already allocated in frame '{self.name}'")
        # local offsets grow negatively; we ensure alignment of the absolute value
        # compute next free offset: already negative, we align its absolute value
        abs_next = _align(abs(self._local_cursor), self.alignment)
        off = -abs_next
        self.locals[name] = (off, size, category)
        # move cursor to next negative slot
        self._local_cursor = off - size
        self._finalized = False
        return off

    def get_symbol(self, name: str) -> Optional[Tuple[int, int, str]]:
        """Busca en params y locals. Devuelve (offset, size, category) o None."""
        if name in self.params:
            return self.params[name]
        if name in self.locals:
            return self.locals[name]
        return None

    def frame_size(self) -> int:
        """
        Calcula tamaño total del frame en bytes (espacio para locales + padding).
        We return the space required for locals as a positive number.
        """
        # deepest local offset is the smallest negative value in locals or _local_cursor+size
        if not self.locals:
            return 0
        # compute absolute used by locals: abs(min_offset) rounded up to alignment
        min_off = min((off for off, _, _ in self.locals.values()), default=0)
        return _align(abs(min_off) + self.alignment, self.alignment)

    def param_size(self) -> int:
        return _align(self._param_cursor, self.alignment)

    def summary(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "alignment": self.alignment,
            "params": dict(self.params),
            "locals": dict(self.locals),
            "param_size": self.param_size(),
            "local_area": self.frame_size(),
        }

    def __repr__(self) -> str:
        return f"<Frame {self.name} params={len(self.params)} locals={len(self.locals)}>"

class FrameManager:
    """
    Manager global de frames. Mantiene un stack de frames (entry/exit)
    y un diccionario de frames por id.

    API principal:
      - enter_frame(frame_id)
      - exit_frame() -> frame_id
      - allocate_param(frame_id, name, type_name, size=None)
      - allocate_local(frame_id, name, type_name, size=None)
      - get_symbol_location(frame_id, name) -> dict with offset,size,category
      - attach_runtime_info(symbol_table, name, frame_id, category, size=None) -> bool
    """

    def __init__(self, default_alignment: int = 4):
        self._frames: Dict[str, Frame] = {}
        self._stack: List[str] = []
        self._lock = threading.Lock()
        self._default_alignment = int(default_alignment)

    # ---------- frame lifecycle ----------

    def enter_frame(self, frame_id: str, alignment: Optional[int] = None) -> None:
        """
        Create and push a new frame. If frame_id already exists, uses the existing frame but still pushes it.
        """
        if not frame_id or not isinstance(frame_id, str):
            raise ValueError("frame_id must be a non-empty string")
        with self._lock:
            if frame_id not in self._frames:
                self._frames[frame_id] = Frame(frame_id, alignment or self._default_alignment)
            self._stack.append(frame_id)

    def exit_frame(self) -> Optional[str]:
        """
        Pop the top frame and return its id. Returns None if stack is empty.
        """
        with self._lock:
            if not self._stack:
                return None
            return self._stack.pop()

    def current_frame_id(self) -> Optional[str]:
        with self._lock:
            return self._stack[-1] if self._stack else None

    def current_frame(self) -> Optional[Frame]:
        fid = self.current_frame_id()
        if fid is None:
            return None
        return self._frames.get(fid)

    # ---------- allocation helpers ----------

    def allocate_param(self, frame_id: str, name: str, type_name: Optional[str] = None, size: Optional[int] = None) -> int:
        """
        Allocate a parameter slot in the given frame and return the offset (>=0).
        If size is None, uses size_of_type(type_name).
        """
        if size is None:
            size = self.size_of_type(type_name)
        with self._lock:
            if frame_id not in self._frames:
                self._frames[frame_id] = Frame(frame_id, self._default_alignment)
            return self._frames[frame_id].allocate_param(name, int(size), category="param")

    def allocate_local(self, frame_id: str, name: str, type_name: Optional[str] = None, size: Optional[int] = None) -> int:
        """
        Allocate a local slot (negative offset) and return the offset (<0).
        """
        if size is None:
            size = self.size_of_type(type_name)
        with self._lock:
            if frame_id not in self._frames:
                self._frames[frame_id] = Frame(frame_id, self._default_alignment)
            return self._frames[frame_id].allocate_local(name, int(size), category="local")

    def get_symbol_location(self, frame_id: str, name: str) -> Optional[Dict[str, object]]:
        """
        Devuelve diccionario con keys: offset (int), size (int), category (str).
        """
        with self._lock:
            frame = self._frames.get(frame_id)
            if not frame:
                return None
            info = frame.get_symbol(name)
            if not info:
                return None
            off, size, category = info
            return {"offset": int(off), "size": int(size), "category": category, "frame": frame_id}

    def frame_layout(self, frame_id: str) -> Optional[Dict[str, object]]:
        with self._lock:
            frame = self._frames.get(frame_id)
            if not frame:
                return None
            return frame.summary()

    # ---------- integration helpers with SymbolTable ----------

    def attach_runtime_info(self, st: "SymbolTable", name: str, frame_id: str, category: str = "local", size: Optional[int] = None) -> bool:
        """
        Attach runtime metadata to a symbol already present in symbol table `st`.
        - If the slot was already allocated in the frame, reuse it.
        - Otherwise allocate (param or local).
        - Returns True if the symbol was found in the symbol table and metadata attached.
        Returns False if the symbol is not present in the symbol table (caller may try again).
        """
        if size is None:
            # try to infer type/size from symbol table if possible
            try:
                sym = st.lookup(name)
                type_name = getattr(sym, "type", None) if sym is not None else None
            except Exception:
                type_name = None
            size = self.size_of_type(type_name)

        with self._lock:
            # ensure frame exists
            if frame_id not in self._frames:
                self._frames[frame_id] = Frame(frame_id, self._default_alignment)
            frame = self._frames[frame_id]

            # If the symbol already has a slot in the frame, reuse it
            existing = frame.get_symbol(name)
            if existing is not None:
                offset, existing_size, existing_cat = existing
            else:
                # allocate new slot
                try:
                    if category == "param":
                        offset = frame.allocate_param(name, int(size), category=category)
                    else:
                        offset = frame.allocate_local(name, int(size), category=category)
                except KeyError:
                    # In rare race-cases another caller just allocated it: fetch existing then
                    existing = frame.get_symbol(name)
                    if existing is not None:
                        offset, existing_size, existing_cat = existing
                    else:
                        # propagate as an error-like False (avoid raising inside semantic pass)
                        return False

        # attach runtime metadata onto symbol if present in symbol table
        sym = st.lookup(name)
        if sym is None:
            # symbol not yet defined in table; caller must define first and call again
            return False

        if getattr(sym, "metadata", None) is None:
            sym.metadata = {}
        sym.metadata.update({"offset": int(offset), "frame": frame_id, "category": category, "size": int(size)})
        return True


    # ---------- utility ----------

    @staticmethod
    def size_of_type(type_name: Optional[str]) -> int:
        """Return size in bytes for a given type name. Reasonable defaults provided."""
        if not type_name:
            return 4
        t = str(type_name).lower()
        if t in ("int", "integer", "i32"):
            return 4
        if t in ("i64", "long"):
            return 8
        if t in ("float", "double", "f64", "f32"):
            # consider double 8, float 4 but default to 8 for safety if unknown format
            return 8
        if t in ("bool", "boolean"):
            return 1
        if t in ("char",):
            return 1
        # fallback
        return 4

    def all_frames(self) -> Dict[str, Dict[str, object]]:
        """Return summary for all frames (frame_id -> layout summary)."""
        with self._lock:
            return {fid: frame.summary() for fid, frame in self._frames.items()}

    def reset(self) -> None:
        """Clear all frames and stack (useful for tests)."""
        with self._lock:
            self._frames.clear()
            self._stack.clear()

    def __repr__(self) -> str:
        with self._lock:
            return f"<FrameManager frames={len(self._frames)} stack={len(self._stack)}>"
