from typing import Any, Dict, List, Optional

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
        self.errors: List[str] = []

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
        else:
            self.errors.append("Cannot exit global scope")

    def define(self, symbol: Symbol) -> bool:
        scope = self.scopes[-1]
        if symbol.name in scope:
            self.errors.append(f"Duplicate declaration of '{symbol.name}' in current scope")
            return False
        if self._flow_stack:
            symbol.metadata['flow_contexts'] = list(self._flow_stack)
        scope[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def enter_flow(self, kind: str):
        self._flow_stack.append(kind)

    def exit_flow(self):
        if not self._flow_stack:
            self.errors.append("No flow context to exit")
        else:
            self._flow_stack.pop()

    def get_errors(self) -> List[str]:
        return list(self.errors)

    def clear_errors(self):
        self.errors.clear()
