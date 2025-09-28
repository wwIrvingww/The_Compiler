# src/ir/temps.py
"""
TempAllocator: gestiona temporales para la generación de código intermedio (TAC).

Características:
- new_temp() / new_typed_temp(type_name) => devuelve nombres "t0", "t1", ...
- free_temp(name) => libera y recicla el temporal
- reserve(name) => reserva explícitamente un temporal (útil para debugging o pruebas)
- context manager .temporary(...) => crea temporal dentro de un `with` y lo libera al salir
- inspección: allocated(), free_list(), next_id_hint()
- configurable prefijo de temporales y comportamiento ante errores

No usa typing.Any (evitamos 'any' por convención del proyecto).
"""

from typing import Dict, List, Optional, Iterator
import threading
import re


class TempAllocator:
    def __init__(self, prefix: str = "t", start: int = 0, raise_on_invalid_free: bool = False):
        """
        prefix: prefijo de los temporales (por defecto 't' => 't0', 't1', ...)
        start: id inicial para temporales
        raise_on_invalid_free: si True, free_temp de un temporal no asignado lanza ValueError
        """
        if not prefix or not isinstance(prefix, str):
            raise ValueError("prefix must be a non-empty string")
        self._prefix = prefix
        self._next_id = int(start)
        self._free_ids: List[int] = []  # LIFO stack of free ids
        self._allocated: Dict[int, Optional[str]] = {}  # id -> optional type_name
        self._lock = threading.Lock()
        self._raise_on_invalid_free = bool(raise_on_invalid_free)
        # Precompiled regex for parsing names like 't12'
        self._name_re = re.compile(rf"^{re.escape(self._prefix)}(\d+)$")

    # ---------- allocation API ----------

    def new_temp(self) -> str:
        """Allocate a fresh temporary name (without type)."""
        return self._new_temp_internal(type_name=None)

    def new_typed_temp(self, type_name: str) -> str:
        """
        Allocate a fresh temporary and attach a type name (string).
        type_name is stored for debugging or future register allocation use.
        """
        return self._new_temp_internal(type_name=str(type_name))

    def _new_temp_internal(self, type_name: Optional[str]) -> str:
        with self._lock:
            if self._free_ids:
                tid = self._free_ids.pop()
            else:
                tid = self._next_id
                self._next_id += 1
            self._allocated[tid] = type_name
            return f"{self._prefix}{tid}"

    # ---------- free / reserve ----------

    def free_temp(self, name: str) -> None:
        """
        Free a previously-allocated temporary so it can be reused.
        If name was not allocated and raise_on_invalid_free is False, the call is ignored.
        """
        tid = self._parse_name(name)
        with self._lock:
            if tid not in self._allocated:
                if self._raise_on_invalid_free:
                    raise ValueError(f"Attempt to free unallocated temp: {name}")
                # ignore silently
                return
            # mark as free and remove type info
            self._allocated.pop(tid, None)
            # push onto free list (LIFO)
            self._free_ids.append(tid)

    def reserve(self, name: str, type_name: Optional[str] = None) -> None:
        """
        Reserve a specific temporary name (e.g., 't42').
        Useful for tests/debugging or when a deterministic name is needed.
        """
        tid = self._parse_name(name)
        with self._lock:
            if tid in self._allocated:
                raise KeyError(f"Temporary {name} is already reserved/allocated")
            self._allocated[tid] = type_name
            # ensure next id moves past reserved tid
            if tid >= self._next_id:
                self._next_id = tid + 1
            # remove tid from free list if it was previously there
            try:
                self._free_ids.remove(tid)
            except ValueError:
                pass

    # ---------- helpers / introspection ----------

    def allocated(self) -> List[str]:
        """Return a list of currently allocated temporal names (unsorted by allocation order)."""
        with self._lock:
            return [f"{self._prefix}{tid}" for tid in sorted(self._allocated.keys())]

    def free_list(self) -> List[str]:
        """Current free list (order in which ids will be reused: last element is next used)."""
        with self._lock:
            return [f"{self._prefix}{tid}" for tid in reversed(self._free_ids)]

    def temp_type_map(self) -> Dict[str, Optional[str]]:
        """Return mapping name -> type_name (type_name may be None)."""
        with self._lock:
            return {f"{self._prefix}{tid}": t for tid, t in self._allocated.items()}

    def next_id_hint(self) -> int:
        """Hint of next unused id (for diagnostics)."""
        with self._lock:
            return int(self._next_id)

    def reset(self) -> None:
        """Clear allocator to initial state (useful for tests)."""
        with self._lock:
            self._next_id = 0
            self._free_ids.clear()
            self._allocated.clear()

    # ---------- context manager convenience ----------

    class _TempContext:
        def __init__(self, allocator: "TempAllocator", name: str):
            self._allocator = allocator
            self._name = name
            self._freed = False

        def name(self) -> str:
            return self._name

        def free(self) -> None:
            if not self._freed:
                self._allocator.free_temp(self._name)
                self._freed = True

        def __enter__(self) -> str:
            return self._name

        def __exit__(self, exc_type, exc, tb) -> Optional[bool]:
            self.free()
            return None

    def temporary(self, type_name: Optional[str] = None) -> "TempAllocator._TempContext":
        """
        Context-manager helper:

        with temps.temporary() as t:
            emit("t = a + b")
            # when exiting block, t is automatically freed

        If type_name is provided, new_typed_temp(type_name) is used.
        """
        if type_name is None:
            name = self.new_temp()
        else:
            name = self.new_typed_temp(type_name)
        return TempAllocator._TempContext(self, name)

    # ---------- internal utils ----------

    def _parse_name(self, name: str) -> int:
        """
        Parse a temporal name like 't12' and return the numeric id.
        Raises ValueError if format doesn't match allocator prefix.
        """
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        m = self._name_re.match(name)
        if not m:
            raise ValueError(f"Invalid temp name '{name}' for prefix '{self._prefix}'")
        return int(m.group(1))

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"<TempAllocator prefix={self._prefix!r} next_id={self._next_id} "
                f"allocated={len(self._allocated)} free={len(self._free_ids)}>"
            )
