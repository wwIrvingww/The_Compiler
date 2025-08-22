# tests/test_symbol_table_flowinfo.py

import pytest
from symbol_table import Symbol, SymbolTable

def test_define_in_if_has_flow_context():
    st = SymbolTable()
    st.enter_scope()
    st.enter_flow('if')
    s = Symbol('x', 'integer')
    st.define(s)
    st.exit_flow()
    found = st.lookup('x')
    assert found is s
    assert 'flow_contexts' in found.metadata
    assert found.metadata['flow_contexts'] == ['if']

def test_nested_flow_contexts_recorded():
    st = SymbolTable()
    st.enter_scope()
    st.enter_flow('for')
    st.enter_flow('while')
    s = Symbol('y', 'boolean')
    st.define(s)
    st.exit_flow()
    st.exit_flow()
    found = st.lookup('y')
    assert found.metadata['flow_contexts'] == ['for', 'while']

def test_define_without_flow_context():
    st = SymbolTable()
    st.enter_scope()
    s = Symbol('z', 'string')
    st.define(s)
    found = st.lookup('z')
    assert 'flow_contexts' not in found.metadata

def test_flow_stack_errors():
    st = SymbolTable()
    with pytest.raises(RuntimeError):
        st.exit_flow()
