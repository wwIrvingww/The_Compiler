# tests/test_symbol_table_runtime.py
from symbol_table.symbol_table import SymbolTable
from symbol_table.runtime_layout import FrameManager, Frame

def test_frame_param_local_attach():
    st = SymbolTable()
    fm = FrameManager()
    fm.enter_frame("f")
    # definir símbolo en tabla como hace el semantic (simula)
    from symbol_table.symbol_table import Symbol
    sym_p = Symbol("a", "integer")
    st.define(sym_p)
    # asignar param
    fm.allocate_param("f", "a", type_name="integer")
    ok = fm.attach_runtime_info(st, "a", "f", category="param")
    assert ok
    pinfo = st.lookup("a").metadata
    assert pinfo["frame"] == "f"
    assert "offset" in pinfo

    # definir local
    sym_l = Symbol("tmp", "integer")
    st.define(sym_l)
    fm.allocate_local("f", "tmp", type_name="integer")
    ok2 = fm.attach_runtime_info(st, "tmp", "f", category="local")
    assert ok2
    linfo = st.lookup("tmp").metadata
    assert linfo["frame"] == "f"
    assert "offset" in linfo
