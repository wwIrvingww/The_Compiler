# tests/test_semantic_generales.py

import pytest
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic

# Utilidad compartida
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
# Inciso 1 — Detección de código muerto (instrucciones después de return/break)
# =============================================================================

def test_01_dead_code_ok_sin_muerto():
    """
    Positivo: no hay instrucciones inalcanzables.
    """
    code = """
    function f(): integer {
        let x: integer = 1;
        if (true) { x = 2; }
        return x;
    }
    """
    errors, _ = run_semantic(code)
    # No esperamos errores por código muerto aquí
    assert not any("codigo muerto" in e.lower() or "inalcanzable" in e.lower() for e in errors), errors

def test_01_dead_code_negativo_despues_de_return():
    """
    Negativo: instrucción después de return debe marcar 'código muerto'.
    """
    code = """
    function g(): integer {
        return 1;
        let y: integer = 3;   // inalcanzable
    }
    """
    errors, _ = run_semantic(code)
    assert any("codigo muerto" in e.lower() or "inalcanzable" in e.lower() for e in errors), errors

def test_01_dead_code_negativo_despues_de_break():
    """
    Negativo: instrucción después de break dentro de bucle debe marcar 'código muerto'.
    """
    code = """
    function h() {
        let i: integer = 0;
        while (i < 3) {
            break;
            i = i + 1;   // inalcanzable
        }
    }
    """
    errors, _ = run_semantic(code)
    assert any("codigo muerto" in e.lower() or "inalcanzable" in e.lower() for e in errors), errors


# =============================================================================
# Inciso 2 — Verificar que las expresiones tengan sentido semántico
# (ejemplo: no multiplicar funciones)
# =============================================================================

def test_02_semantica_ok_operaciones_validas():
    """
    Positivo: operaciones con tipos válidos y llamadas correctas.
    """
    code = """
    function uno(): integer { return 1; }
    let a: integer = uno() * 2;     // multiplicar el resultado (integer) sí tiene sentido
    let b: integer = 3 + 4;
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_02_semantica_negativo_operar_con_null_de_funcion():
    """
    Negativo: intentar operar con el resultado de un 'procedimiento' (retorna null)
    debe terminar en incompatibilidad en multiplicativo (+/-/*/).
    listener emite: "No se puede aplicar * a tipos 'integer' y 'null'".
    """
    code = """
    function log() { print(1); }  // retorna null
    let a: integer = 2 * log();   // operar integer * null -> debe fallar
    """
    errors, _ = run_semantic(code)
    assert any("No se puede aplicar *" in e for e in errors), errors

def test_02_semantica_negativo_no_multiplicar_funcion_identificador():
    """
    Negativo: no debería permitirse tratar el identificador de función como valor aritmético.
    """
    code = """
    function f(): integer { return 2; }
    let k = f * 3;   // usar identificador de función como operando
    """
    errors, _ = run_semantic(code)
    assert any("expresion invalida" in e.lower() or "no se puede" in e.lower() for e in errors), errors


# =============================================================================
# Inciso 3 — Validación de declaraciones duplicadas (variables y parámetros)
# =============================================================================

def test_03_dupes_ok_sin_redeclaracion():
    """
    Positivo: variables con nombres distintos en el mismo ámbito y parámetros únicos.
    """
    code = """
    let a: integer = 1;
    let b: integer = 2;

    function suma(x: integer, y: integer): integer {
        let z: integer = x + y;
        return z;
    }
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_03_dupes_negativo_variable_en_mismo_ambito():
    """
    Negativo: redeclaración de variable en el mismo ámbito.
    """
    code = """
    let a: integer = 1;
    let a: integer = 2;   // redeclaración
    """
    errors, _ = run_semantic(code)
    assert any("ya está definido en el ambito actual" in e and "'a'" in e for e in errors), errors

def test_03_dupes_negativo_parametro_duplicado():
    """
    Negativo: parámetro duplicado en la firma.
    Espera el mismo mensaje de 'ya está definido en el ambito actual' sobre el nombre duplicado.
    """
    code = """
    function f(x: integer, x: integer): integer {  // x duplicado
        return x;
    }
    """
    errors, _ = run_semantic(code)
    assert any("ya está definido en el ambito actual" in e and "'x'" in e for e in errors), errors
