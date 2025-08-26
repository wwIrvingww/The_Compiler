# /tests/test_semantic.py
import pytest
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic


def run_semantic(code: str):
    """
    Ejecuta el lexer+parser+listener semántico sobre 'code' y
    regresa (errors, program_ast).
    """
    input_stream = InputStream(code)
    lexer = CompiscriptLexer(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)
    tree = parser.program()

    walker = ParseTreeWalker()
    sem = AstAndSemantic()
    walker.walk(sem, tree)
    return sem.errors, sem.program


def has_error(errors, text):
    joined = "\n".join(errors)
    return text in joined


# ---------------------------
# Casos OK (no deben fallar)
# ---------------------------

def test_ok_basic_no_errors():
    code = """
    let a: integer = 1;
    let b = 2;
    a = a + b * 3;
    print(a);

    let flag: boolean = true;
    if (flag) { print(a); }
    while (flag) { flag = false; }
    """
    errors, program = run_semantic(code)
    assert errors == [], f"Esperaba sin errores, obtuve: {errors}"
    # sanity check simple sobre el AST
    assert len(program.body) >= 4


def test_shadowing_allowed_in_inner_block():
    code = """
    let a: integer = 1;
    {
        let a: integer = 2;  // redeclaración en bloque anidado: permitido
        print(a);
    }
    print(a);
    """
    errors, _ = run_semantic(code)
    assert errors == [], f"Sombras en bloque anidado deberían ser válidas: {errors}"


# -----------------------------------
# Casos con errores (deben disparar)
# -----------------------------------

def test_type_mismatch_in_initializer():
    code = 'let s: string = 42;'
    errors, _ = run_semantic(code)
    assert any("Tipo incompatible" in e and "'s'" in e for e in errors), errors


def test_type_mismatch_in_initializer_from_expr():
    code = 'let i: integer = "hola" + 3;'
    errors, _ = run_semantic(code)
    assert any("Tipo incompatible" in e and "'i'" in e for e in errors), errors


def test_undeclared_identifier_on_assignment():
    code = 'y = 5;'
    errors, _ = run_semantic(code)
    assert any("Identificador no declarado" in e and "'y'" in e for e in errors), errors


def test_const_reassignment_forbidden():
    code = """
    const c: integer = 1;
    c = 2;
    """
    errors, _ = run_semantic(code)
    assert any("No se puede asignar a const" in e and "'c'" in e for e in errors), errors


def test_redeclaration_in_same_scope():
    code = """
    let a: integer = 1;
    let a = 2;  // misma capa: debe marcar redeclaración
    """
    errors, _ = run_semantic(code)
    assert any("ya está definido en el ámbito actual" in e or "ya esta definido en el ambito actual" in e for e in errors), errors


def test_if_and_while_require_boolean_condition():
    code = """
    if (1) { }
    while (2) { }
    """
    errors, _ = run_semantic(code)
    assert any("La condición del if debe ser boolean" in e for e in errors), errors
    assert any("La condición del while debe ser boolean" in e for e in errors), errors


def test_property_assignment_not_supported_yet():
    code = """
    let obj: integer = 0;
    obj.prop = 3;     // aún no soportado
    """
    errors, _ = run_semantic(code)
    assert any("Identificador no declarado" in e for e in errors), errors


def test_access_call_index_not_supported_yet():
    code = """
    let a: integer = 10;
    print(a[0]);      // indexación aún no soportada
    """
    errors, _ = run_semantic(code)
    # El mensaje exacto lo pusiste como "Accesos/calls/indexación no soportados aún en esta fase."
    assert any("no soportados" in e and "indexación" in e for e in errors), errors


def test_ternary_condition_must_be_boolean():
    code = 'let t = 1 ? 2 : 3;'
    errors, _ = run_semantic(code)
    # Si ya renombraste a exitTernaryExpr(...) esto debería aparecer
    assert any("La condición del operador ternario debe ser boolean" in e for e in errors), errors
