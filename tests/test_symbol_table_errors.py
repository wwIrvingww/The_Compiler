# tests/test_symbol_table_errors.py

import pytest
from src.symbol_table import Symbol, SymbolTable

def test_duplicate_declaration_records_error():
    st = SymbolTable()
    ok = st.define(Symbol("a", "int"))
    assert ok
    ok2 = st.define(Symbol("a", "int"))
    assert not ok2
    errs = st.get_errors()
    assert "Duplicate declaration of 'a'" in errs[0]

def test_exit_global_scope_records_error():
    st = SymbolTable()
    st.exit_scope()
    errs = st.get_errors()
    assert "Cannot exit global scope" in errs[0]

def test_exit_flow_without_enter_records_error():
    st = SymbolTable()
    st.exit_flow()
    errs = st.get_errors()
    assert "No flow context to exit" in errs[0]
