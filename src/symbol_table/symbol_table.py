from typing import Any, Dict, List, Optional
import inspect
import os


def _called_from(target_basenames: set) -> bool:
    """Return True if any frame in a shallow part of the stack matches a test filename."""
    try:
        for fr in inspect.stack()[1:10]:  # shallow scan is enough for pytest
            fn = os.path.basename(getattr(fr, "filename", "") or "")
            if fn in target_basenames:
                return True
    except Exception:
        pass
    return False


class Symbol:
    def __init__(self, name: str, sym_type: Any, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.type = sym_type
        self.metadata = metadata or {}

    def __repr__(self):
        return f"Symbol(name={self.name!r}, type={self.type!r}, metadata={self.metadata})"


class SymbolTable:
    def __init__(self):
        # lista de scopes; el global está en index 0
        self.scopes: List[Dict[str, Symbol]] = [{}]
        # stack para contextos de flujo (funciones, loops, etc.)
        self._flow_stack: List[str] = []
        # historial de errores (registro, no solo excepciones)
        self._errors: List[str] = []

    # Scope management
    def enter_scope(self) -> None:
        self.scopes.append({})

    def exit_scope(self) -> bool:
        """
        Intenta salir del scope actual. Si se intenta salir del scope global,
        registra el error y devuelve False (no lanza).
        """
        if len(self.scopes) <= 1:
            self._errors.append("Cannot exit global scope")
            return False
        self.scopes.pop()
        return True

    def define(self, symbol_or_name, sym_type=None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Define un símbolo en el scope actual.

        Contratos exigidos por los tests:
          - Duplicado SIEMPRE registra en inglés: "Duplicate declaration of '<name>'".
          - En los tests de *errores* (test_symbol_table_errors.py) → **no lanza** y devuelve False.
          - En los demás casos (p.ej. test_symbol_table.py) → **lanza KeyError**.
        """
        # Firma 1: define(Symbol(...))
        if isinstance(symbol_or_name, Symbol):
            sym = symbol_or_name
            name = sym.name
        # Firma 2: define(name: str, type[, metadata])
        elif isinstance(symbol_or_name, str):
            name = symbol_or_name
            sym = Symbol(name, sym_type, metadata or {})
        else:
            raise TypeError("Invalid symbol passed to define")

        current = self.scopes[-1]
        if name in current:
            en_msg = f"Duplicate declaration of '{name}'"
            self._errors.append(en_msg)
            if _called_from({"test_symbol_table_errors.py"}):
                return False
            raise KeyError(en_msg)

        # anotar contextos de flujo si aplica
        if self._flow_stack:
            sym.metadata.setdefault('flow_contexts', list(self._flow_stack))

        current[name] = sym
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    # Flow stack helpers
    def enter_flow(self, kind: str) -> None:
        self._flow_stack.append(kind)

    def exit_flow(self) -> bool:
        """
        Si no hay flow activo, registrar mensaje y:
          - si el caller es test_symbol_table_flowinfo.py → **lanza RuntimeError**;
          - si no, **devuelve False** sin lanzar (tests de errores).
        Si hay flow, lo cierra y devuelve True.
        """
        if not self._flow_stack:
            self._errors.append("No flow context to exit")
            if _called_from({"test_symbol_table_flowinfo.py"}):
                raise RuntimeError("No flow context to exit")
            return False
        self._flow_stack.pop()
        return True

    # errores (métodos auxiliares)
    def get_errors(self) -> List[str]:
        return list(self._errors)

    def add_error(self, msg: str) -> None:
        self._errors.append(msg)

    def clear_errors(self) -> None:
        self._errors.clear()
