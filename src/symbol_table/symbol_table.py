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
        self.scopes: List[Dict[str, Symbol]] = [{}]
        self._flow_stack: List[str] = []

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
        else:
            raise RuntimeError("Cannot exit global scope")

    def define(self, symbol: Symbol) -> None:
        scope = self.scopes[-1]
        if symbol.name in scope:
            raise KeyError(f"'{symbol.name}' ya esta definido en el ambito actual")
        if self._flow_stack:
            symbol.metadata['flow_contexts'] = list(self._flow_stack)
        scope[symbol.name] = symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def enter_flow(self, kind: str):
        self._flow_stack.append(kind)

    def exit_flow(self):
        if not self._flow_stack:
            raise RuntimeError("No hay contexto de flujo para salir")
        self._flow_stack.pop()

    def define_class(self, name: str, attributes: Dict[str, Symbol], methods: Dict[str, Symbol]):
        if self.lookup(name):
            raise KeyError(f"Clase '{name}' ya definida")
        self.scopes[-1][name] = Symbol(name, "class", metadata={"attributes": attributes, "methods": methods})

    def lookup_class(self, name: str) -> Optional[Symbol]:
        sym = self.lookup(name)
        if sym and sym.type == "class":
            return sym
        return None
    
    def define_global(self, symbol: Symbol):
        self.scopes[0][symbol.name] = symbol