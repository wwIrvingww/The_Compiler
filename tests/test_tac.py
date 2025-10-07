import pytest
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from src.parser.CompiscriptLexer import CompiscriptLexer
from src.parser.CompiscriptParser import CompiscriptParser
from src.semantic.ast_and_semantic import AstAndSemantic
from src.intermediate.tac_generator import TacGenerator
from src.intermediate.tac_nodes import TACOP

# -------------------------
# Helpers
# -------------------------

def _tac(code: str):
    inp = InputStream(code)
    lx  = CompiscriptLexer(inp)
    ts  = CommonTokenStream(lx)
    ps  = CompiscriptParser(ts)
    tree = ps.program()

    sem = AstAndSemantic()
    ParseTreeWalker().walk(sem, tree)
    assert sem.errors == [], f"Semánticos: {sem.errors}"

    gen = TacGenerator(sem.table)
    gen.visit(tree)
    return gen.get_code()

def _ops(tac, op):
    return [i for i in tac if getattr(i, "op", None) == op]

def _any_op(tac, op):
    return any(getattr(i, "op", None) == op for i in tac)

def _labels(tac):
    return [ (i.result if getattr(i, "op", None) == "label" else None) or getattr(i, "arg1", None)
             for i in tac if getattr(i, "op", None) == "label" ]

def _has_if_or_goto_at(idx, tac):
    return tac[idx].op in {"if-goto", "goto"}

def _has_subsequence(tac, ops_seq):
    """
    Verifica que aparezcan, en ese orden (no necesariamente contiguos),
    instrucciones con op coincidente.
    """
    it = iter(tac)
    for expected in ops_seq:
        for inst in it:
            if inst.op == expected:
                break
        else:
            return False
    return True

# -------------------------
# 1) Var / Const / Assign
# -------------------------

def test_var_const_assign():
    code = """
    let a: integer = 1 + 2;
    const c: integer = 3;
    a = a + c;
    """
    tac = _tac(code)

    # Debe haber '+' por las sumas
    assert _any_op(tac, "+")
    # Asignaciones generadas
    assigns = _ops(tac, "=")
    assert len(assigns) >= 3  # tX=1; tY=2; a=tZ; c=3; a=tW ...

def test_property_assign_simple():
    code = """
    class P { var nombre: string; function set(n: string){ this.nombre = n; } }
    """
    tac = _tac(code)
    # Debe existir STORE_PROP para 'nombre'
    assert any(i.op == "STORE_PROP" and i.arg2 == "nombre" for i in tac)

# -------------------------
# 2) Funciones
# -------------------------

def test_function_decl_and_return():
    code = """
    function f(a: integer, b: integer): integer { 
        return a + b; 
    }
    """
    tac = _tac(code)
    # Debe haber label de entrada y salida
    assert any(i.op == "label" and isinstance(i.result, str) and i.result.endswith("f_entry") for i in tac)
    assert any(i.op == "label" and isinstance(i.result, str) and i.result.endswith("f_exit")  for i in tac)
    # Debe haber '+' y 'return'
    assert _any_op(tac, "+")
    assert _any_op(tac, "return")

# -------------------------
# 3) Clases
# -------------------------

def test_class_decl_simple():
    code = """
    class Persona {
        var nombre: string;
        var edad: integer;
        function saludar(){ print(this.nombre); }
    }
    """
    tac = _tac(code)
    # class / attr / method / endclass
    assert any(i.op == "class"    and i.arg1 == "Persona" for i in tac)
    assert any(i.op == "attr"     and i.arg1 == "Persona" and i.arg2 == "nombre" for i in tac)
    assert any(i.op == "attr"     and i.arg1 == "Persona" and i.arg2 == "edad"   for i in tac)
    m = next((i for i in tac if i.op == "method" and i.arg1 == "Persona" and i.arg2 == "saludar"), None)
    assert m is not None and isinstance(m.result, str) and "saludar_entry" in m.result
    assert any(i.op == "endclass" and i.arg1 == "Persona" for i in tac)

# -------------------------
# 4) Print y Block
# -------------------------

def test_print_and_block():
    code = """
    {
      let x: integer = 1;
      print(x);
    }
    """
    tac = _tac(code)
    # al menos una asignación y un print
    assert _any_op(tac, "=")
    assert _any_op(tac, "print")

# -------------------------
# 5) If / Else
# -------------------------

def test_if_else_simple():
    code = """
    let x: integer = 0;
    if (x < 10) { x = 1; } else { x = 2; }
    """
    tac = _tac(code)
    # Debe haber comparación, if-goto y gotos
    assert _any_op(tac, "<")
    assert _any_op(tac, "if-goto")
    assert _any_op(tac, "goto")
    # Y labels (entry/else/end)
    assert len(_labels(tac)) >= 3

# -------------------------
# 6) While
# -------------------------

def test_while_loop():
    code = """
    let i: integer = 0;
    while (i < 3) { i = i + 1; }
    """
    tac = _tac(code)
    # patrón típico: label cond → if-goto → goto → label body → ... → goto cond → label end
    assert _has_subsequence(tac, ["label", "if-goto", "goto", "label", "goto", "label"])

# -------------------------
# 7) Do-While
# -------------------------

def test_do_while_loop():
    code = """
    let i: integer = 0;
    do { i = i + 1; } while (i < 3);
    """
    tac = _tac(code)
    # patrón típico: label body → label cond → if-goto → goto → label end
    assert _has_subsequence(tac, ["label", "label", "if-goto", "goto", "label"])

# -------------------------
# 8) For
# -------------------------

def test_for_loop():
    code = """
    for (let i: integer = 0; i < 2; i = i + 1) {
        if (i == 1) { /* continue; (ignorado por semántica actual) */ }
    }
    """
    tac = _tac(code)
    # Debe existir: init (=), label cond, if-goto, label body, label step, gotos de lazo
    assert _any_op(tac, "=")
    assert _any_op(tac, "if-goto")
    labels = _labels(tac)
    assert len(labels) >= 4
    assert _any_op(tac, "goto")

# -------------------------
# 9) Switch
# -------------------------

def test_switch_basic():
    code = """
    let x: integer = 2;
    switch (x) {
      case 1: x = 10;
      case 2: x = 20;
      default: x = 30;
    }
    """
    tac = _tac(code)
    # Debe hacer comparaciones con '==' y tener labels/gotos
    assert _any_op(tac, "==")
    assert _any_op(tac, "label")
    assert _any_op(tac, "goto")

# -------------------------
# 10) Foreach
# -------------------------

# def test_foreach_loop():
#     code = """
#     let arr: list<integer> = [1,2,3];
#     foreach (item in arr) {
#       print(item);
#     }
#     """
#     tac = _tac(code)
#     assert _any_op(tac, "=")
#     assert any(i.op == "len" for i in tac) 
#     assert any(i.op == "getidx" for i in tac)
#     assert _any_op(tac, "print")

# -------------------------
# 11) Break / Continue
# -------------------------

# def test_break_continue_in_loops():
#     code = """
#     let s: integer = 0;
#     let i: integer = 0;
#     while (i < 5) {
#       i = i + 1;
#       if (i == 2) { continue; }
#       if (i == 4) { break; }
#       s = s + i;
#     }
#     """
#     tac = _tac(code)
#     # No nos importa la forma exacta, pero deben existir varios gotos/if-goto y labels
#     assert _any_op(tac, "label")
#     assert _any_op(tac, "if-goto")
#     assert _any_op(tac, "goto")

# -------------------------
# 12) Return
# -------------------------

# def test_return_no_value_and_with_value():
#     code = """
#     function g() { return; }
#     function f(a: integer){ return a; }
#     """
#     tac = _tac(code)
#     # Debe haber dos 'return' (uno sin arg y otro con arg)
#     rets = _ops(tac, "return")
#     assert len(rets) >= 2
#     assert any(r.arg1 is None for r in rets)     # return;
#     assert any(isinstance(r.arg1, str) for r in rets)  # return a/tx