# src/symbol_table.py

from typing import Any, Dict, Optional, List

class Symbol:
    def __init__(self, name: str, sym_type: str, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.type = sym_type
        self.metadata = metadata or {}

    def __repr__(self):
        return f"Symbol(name={self.name!r}, type={self.type!r}, metadata={self.metadata})"

class SymbolTable:
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = [{}]  # pila de entornos

    def enter_scope(self):
        """Crear un nuevo entorno anidado."""
        self.scopes.append({})

    def exit_scope(self):
        """Salir del entorno actual."""
        if len(self.scopes) > 1:
            self.scopes.pop()
        else:
            raise RuntimeError("Cannot exit global scope")

    def define(self, symbol: Symbol) -> None:
        """Insertar un símbolo en el entorno actual."""
        scope = self.scopes[-1]
        if symbol.name in scope:
            raise KeyError(f"'{symbol.name}' ya está definido en el ámbito actual")
        scope[symbol.name] = symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        """Buscar un símbolo recorriendo entornos de interno a externo."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None
