# src/intermediate/labels.py
"""LabelGenerator: genera etiquetas únicas usadas por la generación de código intermedio (TAC).

Características:
- new_label() -> devuelve 'L0', 'L1', ...
- reserve(name) -> reserva una etiqueta específica (por ejemplo 'L42')
- reset() -> reinicia el contador y limpia reservas (útil para tests)
- next_id_hint() -> sugerencia del siguiente id no usado
- allocated() -> lista de etiquetas ya generadas/reservadas
- thread-safe (usa un lock interno)

Notas:
- Las etiquetas normalmente no se reciclan (no hay free_label) porque representan puntos
  de salto únicos; si se necesita reciclaje, se puede añadir más adelante.
- Recomiendo crear una instancia por compilación para reproducibilidad en tests/logs.
"""

from typing import List, Optional
import threading
import re


class LabelGenerator:
    def __init__(self, prefix: str = "L", start: int = 0):
        if not prefix or not isinstance(prefix, str):
            raise ValueError("prefix must be a non-empty string")
        self._prefix = prefix
        self._next_id = int(start)
        self._allocated_ids: List[int] = []
        self._lock = threading.Lock()
        # precompile regex for parsing names like 'L12'
        self._name_re = re.compile(rf"^{re.escape(self._prefix)}(\d+)$")

    def new_label(self) -> str:
        """Return a fresh label name (e.g. 'L0')."""
        with self._lock:
            lid = self._next_id
            self._next_id += 1
            self._allocated_ids.append(lid)
            return f"{self._prefix}{lid}"

    def reserve(self, name: str) -> None:
        """Reserve a specific label name (e.g. 'L42').

        If the label was already reserved/created, raises KeyError.
        If the numeric id is >= next_id, next_id is advanced to avoid collisions.
        """
        lid = self._parse_name(name)
        with self._lock:
            if lid in self._allocated_ids:
                raise KeyError(f"Label {name} already reserved/allocated")
            self._allocated_ids.append(lid)
            if lid >= self._next_id:
                self._next_id = lid + 1

    def next_id_hint(self) -> int:
        """Hint for the next unused numeric id (for diagnostics)."""
        with self._lock:
            return int(self._next_id)

    def allocated(self) -> List[str]:
        """Return a list of allocated label names (sorted by numeric id)."""
        with self._lock:
            return [f"{self._prefix}{i}" for i in sorted(self._allocated_ids)]

    def reset(self) -> None:
        """Reset generator to initial state (useful for tests)."""
        with self._lock:
            self._next_id = 0
            self._allocated_ids.clear()

    def _parse_name(self, name: str) -> int:
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        m = self._name_re.match(name)
        if not m:
            raise ValueError(f"Invalid label name '{name}' for prefix '{self._prefix}'")
        return int(m.group(1))

    def __repr__(self) -> str:
        with self._lock:
            return f"<LabelGenerator prefix={self._prefix!r} next_id={self._next_id} allocated={len(self._allocated_ids)}>"


# Convenience singleton factory: useful to import a shared instance in the pipeline.
_default: Optional[LabelGenerator] = None


def get_default_label_generator() -> LabelGenerator:
    """Return a default shared LabelGenerator for convenience.

    Note: prefer creating a fresh LabelGenerator per compilation for determinism,
    but this helper is handy for quick scripts or tests.
    """
    global _default
    if _default is None:
        _default = LabelGenerator()
    return _default
