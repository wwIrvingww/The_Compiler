# tests/test_type_system.py

import pytest
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic

# Utilidad compartida (idéntica a la que usas)
def run_semantic(code: str):
    input_stream = InputStream(code)
    lexer = CompiscriptLexer(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)
    tree = parser.program()
    walker = ParseTreeWalker()
    sem = AstAndSemantic()
    walker.walk(sem, tree)
    return sem.errors, sem.program


# =============================================================================
# Inciso 1 — Aritmética (+, -, *, /): operandos integer
# =============================================================================

def test_01_aritmetica_ok_enteros():
    code = """
    let a: integer = 6;
    let b: integer = 3;
    let s: integer = a + b;
    let r: integer = a - b;
    let m: integer = a * b;
    let d: integer = a / b;
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_01_aritmetica_error_tipos_malos():
    # Usa los chequeos de Additive/Multiplicative que emiten:
    # "No se puede aplicar {op} a tipos '...' y '...'"
    code = """
    let a: integer = 1;
    let s: string  = "x";
    let k: integer = a + s;   // suma int + string
    """
    errors, _ = run_semantic(code)
    assert any("No se puede aplicar +" in e for e in errors), errors

def test_01_aritmetica_ok_concat_strings():
    # Tu unify_bin permite string + string => string
    code = """
    let a: string = "a";
    let b: string = "b";
    let c: string = a + b;
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors


# =============================================================================
# Inciso 2 — Lógicas (&&, ||, !): operandos boolean.
# al inicializar una variable booleana con el resultado de ! sobre entero (ERROR).
# =============================================================================

def test_02_logicas_ok_booleanos():
    code = """
    let p: boolean = true;
    let q: boolean = false;
    let r: boolean = p && !q || q;
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_02_logicas_error_and_or_sobre_no_booleanos():
    code = """
    let a: integer = 1;
    let b: integer = 2;
    // Debe disparar: "No se puede aplicar && ..." y/o "No se puede aplicar || ..."
    let x = (a && b) || a;
    """
    errors, _ = run_semantic(code)
    assert any("No se puede aplicar &&" in e or "No se puede aplicar ||" in e for e in errors), errors

def test_02_logicas_error_not_sobre_no_boolean_asignacion():
    # "!1" produce tipo ERROR, y luego:
    # "Tipo incompatible en inicializacion de 'ok': esperado boolean, obtenido error"
    code = """
    let uno: integer = 1;
    let ok: boolean = !uno;
    """
    errors, _ = run_semantic(code)
    assert any(
        "Tipo incompatible en inicializacion de 'ok'" in e and "boolean" in e and "error" in e
        for e in errors
    ), errors


# =============================================================================
# Inciso 3 — Comparaciones (==, !=, <, <=, >, >=): operandos del mismo tipo compatible.
# =============================================================================

def test_03_comparaciones_ok_mismo_tipo():
    code = """
    let a: integer = 3;
    let b: integer = 5;
    let c: boolean = a < b && (a == 3) && (b != 4);

    let s1: string = "aa";
    let s2: string = "bb";
    let t: boolean = (s1 == s2) || (s1 != s2);
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_03_comparaciones_error_tipos_distintos():
    # a == "3" => unify a ERROR; capturamos incompatibilidad asignándolo a boolean
    code = """
    let a: integer = 3;
    let bad: boolean = (a == "3");
    """
    errors, _ = run_semantic(code)
    assert any(
        "Tipo incompatible en inicializacion de 'bad'" in e and "boolean" in e and "error" in e
        for e in errors
    ), errors


# =============================================================================
# Inciso 4 — Asignaciones: el tipo del valor debe coincidir con el declarado.
# =============================================================================

def test_04_asignacion_ok_inicializacion_compatible():
    code = """
    let x: integer = 10;
    let y: string  = "hola";
    let z: boolean = true;
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_04_asignacion_error_inicializacion_incompatible():
    code = """
    let x: integer = true;
    """
    errors, _ = run_semantic(code)
    assert any(
        "Tipo incompatible en inicializacion de 'x'" in e and "integer" in e
        for e in errors
    ), errors


# =============================================================================
# Inciso 5 — Constantes: inicialización obligatoria en su declaración.
# =============================================================================

def test_05_const_ok_con_inicializador():
    code = """
    const PI: integer = 3;
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_05_const_error_sin_inicializador():
    code = """
    const A: integer;
    """
    errors, _ = run_semantic(code)
    assert any("Constante 'A' debe tener inicializador" in e for e in errors), errors


# =============================================================================
# Inciso 6 — Listas y estructuras: verificación de tipo de elementos e índices.
# listener:
#  - En ArrayLiteral exige homogeneidad: "No se puede agrupar tipo 'X' con tipo 'Y'..."
#  - Para indexación valida índice integer: "Indexacion debe ser tipo 'integer' no ..."
#  - Para asignar a un elemento: "Tipo de asignacion incompatible: esperado T, obtenido U"
# =============================================================================

def test_06_lista_ok_homogenea_y_indexacion_y_asignacion():
    code = """
    let a: integer = 1;
    let b: integer = 2;
    let L: integer[] = [a, b, 3];

    // indexación con entero
    let i: integer = 0;
    let v: integer = L[i];

    // asignación de elemento con tipo correcto
    L[1] = 99;
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_06_lista_error_heterogenea():
    code = """
    let L = [1, "x", 3];
    """
    errors, _ = run_semantic(code)
    assert any("No se puede agrupar tipo" in e for e in errors), errors

def test_06_lista_error_index_no_entero():
    code = """
    let L: integer[] = [1, 2, 3];
    let b: boolean = true;
    let x = L[b];  // índice no entero
    """
    errors, _ = run_semantic(code)
    assert any("Indexacion debe ser tipo 'integer'" in e for e in errors), errors

def test_06_lista_error_asignacion_elemento_tipo_incompatible():
    code = """
    let L: integer[] = [1, 2, 3];
    L[0] = "hola";  // esperado integer, obtenido string
    """
    errors, _ = run_semantic(code)
    assert any("Tipo de asignacion incompatible" in e for e in errors), errors


# =============================================================================
# Casos adicionales 
# =============================================================================

def test_ax_lista_vacia_ok_tipada_como_list_null():
    code = """
    let E = [];
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_ax_asignar_a_const_error():
    code = """
    const C: integer = 5;
    C = 7;
    """
    errors, _ = run_semantic(code)
    assert any("No se puede asignar a const 'C'" in e for e in errors), errors
