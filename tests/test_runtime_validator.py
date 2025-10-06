# tests/test_runtime_validator.py
import json
from symbol_table.runtime_validator import validate_runtime_consistency, dump_runtime_info_json
from symbol_table.runtime_layout import FrameManager
from symbol_table.symbol_table import SymbolTable, Symbol

def test_validator_ok_with_real_frame_manager():
    # Preparar symbol table y frame manager reales
    st = SymbolTable()
    fm = FrameManager()

    # crear frame
    fm.enter_frame("main")
    # asignar parametros y locales
    fm.allocate_param("main", "a", "integer", size=4)
    fm.allocate_local("main", "tmp", "integer", size=4)

    # Definir símbolos en symbol table (simulación típica)
    sym_a = Symbol("a", "integer")
    sym_tmp = Symbol("tmp", "integer")
    st.define(sym_a)
    st.define(sym_tmp)

    # attach runtime info (si existe API); si no, el validador buscará por nombre en st.symbols
    try:
        fm.attach_runtime_info(st, "a", "main", category="param", size=4)
        fm.attach_runtime_info(st, "tmp", "main", category="local", size=4)
    except Exception:
        # no crítico; seguir (validador es best-effort)
        pass

    errs = validate_runtime_consistency(st, fm)
    assert isinstance(errs, list)
    assert errs == []  # nada raro

    # JSON dump debe parsear
    j = dump_runtime_info_json(fm)
    parsed = json.loads(j)
    assert "main" in parsed

def test_validator_detects_overlap_with_fake_frame():
    # Construimos un frame_manager "falso" mínimo
    class FakeFrame:
        def __init__(self, symbols):
            self.symbols = symbols
    class FakeFM:
        def __init__(self, frames_map):
            self._frames = frames_map

    # Dos slots solapados: a offset 0 size 8 (0-7), b offset 4 size 4 (4-7)
    frames_map = {
        "F": FakeFrame({
            "a": {"offset": 0, "size": 8, "category": "param", "type_name": "integer"},
            "b": {"offset": 4, "size": 4, "category": "local", "type_name": "integer"},
        })
    }

    fm = FakeFM(frames_map)
    # symbol table with both symbols defined
    st = SymbolTable()
    st.define(Symbol("a", "integer"))
    st.define(Symbol("b", "integer"))

    errs = validate_runtime_consistency(st, fm)
    assert any("overlap" in e.lower() for e in errs), f"Se esperaba detectar overlap, got: {errs}"
