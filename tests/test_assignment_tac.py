from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from src.parser.CompiscriptLexer import CompiscriptLexer
from src.parser.CompiscriptParser import CompiscriptParser
from src.semantic.ast_and_semantic import AstAndSemantic
from src.intermediate.tac_generator import TacGenerator

def _tac(code: str):
    input_stream = InputStream(code)
    lx = CompiscriptLexer(input_stream)
    ts = CommonTokenStream(lx)
    ps = CompiscriptParser(ts)
    tree = ps.program()

    sem = AstAndSemantic()
    ParseTreeWalker().walk(sem, tree)
    assert sem.errors == [], f"Semánticos: {sem.errors}"

    gen = TacGenerator(sem.table)
    gen.visit(tree)
    get_code = getattr(gen, "get_code", None)
    return get_code() if callable(get_code) else gen.code

# ---------- Asignación a variables ----------

def test_assign_variable_simple():
    code = """
    let a: integer;
    a = 5;
    """
    tac = _tac(code)
    # Debe existir una instrucción de asignación con destino 'a'
    has_assign_a = any(i.op == "=" and i.result == "a" for i in tac)
    assert has_assign_a, "Se esperaba '=' con result='a' para la asignación simple"

def test_assign_variable_with_expr():
    code = """
    let a: integer;
    a = 1 + 2;
    """
    tac = _tac(code)
    # Debe existir un '+' en el TAC (RHS) y luego '=' hacia 'a'
    has_plus = any(i.op == "+" for i in tac)
    has_assign_a = any(i.op == "=" and i.result == "a" for i in tac)
    assert has_plus, "Se esperaba una suma (+) en el RHS"
    assert has_assign_a, "Se esperaba '=' con result='a' para la asignación"

def test_assign_variable_from_variable():
    code = """
    let a: integer = 3;
    let b: integer;
    b = a;
    """
    tac = _tac(code)
    # La asignación final debe mover algo a 'b'
    has_assign_b = any(i.op == "=" and i.result == "b" for i in tac)
    assert has_assign_b, "Se esperaba '=' con result='b' para b = a"

# ---------- Asignación a propiedades ----------

def test_assign_property_simple():
    code = """
    class Persona {
        var nombre: string;
        function setNombre(n: string) { this.nombre = n; }
    }
    """
    tac = _tac(code)
    # Debe existir un STORE_PROP sobre 'nombre'
    has_store_nombre = any(i.op == "STORE_PROP" and i.arg2 == "nombre" for i in tac)
    assert has_store_nombre, "Se esperaba STORE_PROP(_, 'nombre', _) en el cuerpo de setNombre"

# def test_assign_property_from_expr():
#     code = """
#     class C {
#         var x: integer;
#         function inc(a: integer) {
#             this.x = a + 1;
#         }
#     }
#     """
#     tac = _tac(code)
#     # Debe existir '+' y luego STORE_PROP sobre 'x'
#     has_plus = any(i.op == "+" for i in tac)
#     has_store_x = any(i.op == "STORE_PROP" and i.arg2 == "x" for i in tac)
#     assert has_plus, "Se esperaba suma (+) en RHS de la asignación a propiedad"
#     assert has_store_x, "Se esperaba STORE_PROP(_, 'x', _) en la asignación a propiedad"

def test_assign_property_chained_object_expr():
    # Por si tu grammar permite algo tipo: let p = new C(); p.x = 7;
    code = """
    class C { var x: integer; function setX() { } }
    let p: C;
    p.x = 7;
    """
    tac = _tac(code)
    # No sabemos cómo representas p (registro/temp), pero sí que debe existir STORE_PROP sobre 'x'
    has_store_x = any(i.op == "STORE_PROP" and i.arg2 == "x" for i in tac)
    assert has_store_x, "Se esperaba STORE_PROP(_, 'x', 7/tx) para p.x = 7"
