# tests/test_symbol_table.py

import pytest
from src.symbol_table import Symbol, SymbolTable

def test_define_and_lookup_global():
    st = SymbolTable()
    sym = Symbol(name="x", sym_type="integer")
    st.define(sym)
    looked = st.lookup("x")
    assert looked is sym
    assert looked.type == "integer"

def test_nested_scope_lookup_and_hide():
    st = SymbolTable()
    st.define(Symbol("a", "boolean"))
    st.enter_scope()
    # 'a' heredada del scope externo
    assert st.lookup("a").type == "boolean"
    # redefinimos 'a' en el scope interno
    inner = Symbol("a", "string")
    st.define(inner)
    assert st.lookup("a") is inner
    st.exit_scope()
    # volvemos al scope global
    assert st.lookup("a").type == "boolean"

def test_define_duplicate_raises():
    st = SymbolTable()
    st.define(Symbol("y", "integer"))
    with pytest.raises(KeyError):
        st.define(Symbol("y", "integer"))
