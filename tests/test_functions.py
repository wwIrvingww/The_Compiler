# tests/test_functions.py
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
# Inciso 1: Validación del número y tipo de argumentos en llamadas a funciones
# (coincidencia posicional)
# =============================================================================

def test_01_args_ok_posicional_positiva():
    """
    Positivo: se pasa el número correcto de argumentos y con tipos compatibles.
    """
    code = """
    function sum(a: integer, b: integer): integer { return a + b; }
    let r: integer = sum(2, 3);
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_01_args_mismatch_negativa_arity():
    """
    Negativo: número de argumentos inválido.
    Debe reportar: "Numero de argumentos invalido"
    """
    code = """
    function f(a: integer): integer { return a; }
    let x: integer = f(1, 2);
    """
    errors, _ = run_semantic(code)
    assert any("Numero de argumentos invalido" in e for e in errors), errors

def test_01_args_type_mismatch_negativa_tipo():
    """
    Negativo: tipo de argumento inválido en posición 2.
    Debe reportar: "Argumento 2 invalido"
    """
    code = """
    function f(a: integer, b: integer): integer { return a + b; }
    let x: integer = f(1, true);
    """
    errors, _ = run_semantic(code)
    assert any("Argumento 2 invalido" in e for e in errors), errors


# =============================================================================
# Inciso 2: Validación del tipo de retorno de la función
# (el valor devuelto debe coincidir con el tipo declarado)
# =============================================================================

def test_02_return_type_ok_positiva():
    """
    Positivo: la función devuelve el tipo declarado (integer).
    """
    code = """
    function id(a: integer): integer { return a; }
    let x: integer = id(7);
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_02_return_type_mismatch_negativa():
    """
    Negativo: la función declara integer, retorna string.
    Debe reportar: "Tipo de retorno incompatible"
    """
    code = """
    function bad(a: integer): integer {
        return "hola";
    }
    """
    errors, _ = run_semantic(code)
    assert any("Tipo de retorno incompatible" in e for e in errors), errors

def test_02_procedure_no_retorna_valor_negativa():
    """
    Negativo: procedimiento (retorno implícito null) intenta retornar un valor.
    Debe reportar: "Tipo de retorno incompatible ... esperado null"
    """
    code = """
    function p(a: integer) { 
        return 1;   // no debería permitir devolver valor en procedimiento
    }
    """
    errors, _ = run_semantic(code)
    assert any("Tipo de retorno incompatible" in e and "esperado null" in e for e in errors), errors

def test_02_missing_return_is_ok_for_null_positiva():
    """
    Positivo: sin anotación de retorno => null implícito; sin 'return' explícito es válido.
    """
    code = """
    function p() { }
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors


# =============================================================================
# Inciso 3: Soporte para funciones recursivas
# (verificación de que pueden llamarse a sí mismas)
# =============================================================================

def test_03_recursion_ok_positiva():
    """
    Positivo: la función recursiva se resuelve y el tipo de retorno coincide.
    """
    code = """
    function fact(n: integer): integer {
        if (n == 0) { return 1; }
        return n * fact(n - 1);
    }
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_03_recursion_tipo_incompatible_negativa():
    """
    Negativo: recursión devuelve tipo incompatible en alguna rama.
    Debe reportar: "Tipo de retorno incompatible"
    """
    code = """
    function weird(n: integer): integer {
        if (n == 0) { return "cero"; }  // rama incorrecta
        return weird(n - 1);
    }
    """
    errors, _ = run_semantic(code)
    assert any("Tipo de retorno incompatible" in e for e in errors), errors


# =============================================================================
# Inciso 4: Soporte para funciones anidadas y closures
# (debe capturar variables del entorno donde se definen)
# =============================================================================

def test_04_nested_function_closure_ok_positiva():
    """
    Positivo: la función interna accede a variable del entorno externo (closure).
    """
    code = """
    let k: integer = 10;
    function outer(): integer {
        function inner(): integer { return k; }
        return inner();
    }
    let x: integer = outer();
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_04_nested_function_usa_identificador_inesistente_negativa():
    """
    Negativo: la función interna intenta usar un identificador no declarado.
    Debe reportar: "Identificador no declarado: 'y'"
    """
    code = """
    function outer(): integer {
        function inner(): integer { return y; } // 'y' no existe en ningún entorno
        return inner();
    }
    """
    errors, _ = run_semantic(code)
    assert any("Identificador no declarado: 'y'" in e for e in errors), errors

def test_04_closure_sombrea_tipo_incompatible_negativa():
    """
    Negativo: shadowing con tipo incompatible en uso interno (si corresponde).
    Aquí simulamos error pasando outer() a una asignación incompatible.
    """
    code = """
    let base: integer = 5;
    function outer(): integer {
        function inner(): integer { return base; }
        return inner();
    }
    let s: string = outer();  // incompatible: integer -> string
    """
    errors, _ = run_semantic(code)
    # El listener suele reportar incompatibilidad en la inicialización de variable 's'
    assert any(("Tipo incompatible" in e or "incompatible" in e) and "'s'" in e for e in errors), errors


# =============================================================================
# Inciso 5: Detección de múltiples declaraciones de funciones con el mismo nombre
# =============================================================================

def test_05_redeclaracion_funcion_negativa():
    """
    Negativo: misma función redeclarada en el mismo ámbito.
    Debe reportar que ya está definido en el ámbito actual.
    """
    code = """
    function f(a: integer): integer { return a; }
    function f(b: integer): integer { return b; } // redeclaración
    """
    errors, _ = run_semantic(code)
    assert any(("definido" in e or "ambito actual" in e) and "'f'" in e for e in errors), errors

def test_05_funcion_declarada_una_vez_positiva():
    """
    Positivo: una sola declaración de función y uso correcto.
    """
    code = """
    function g(a: integer, b: integer): integer { return a + b; }
    let r: integer = g(3, 4);
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors


# =============================================================================
# Incisos complementarios de Funciones/Procedimientos (coherencia de uso)
# =============================================================================

def test_cx_usar_procedimiento_en_expresion_falla_asignacion_negativa():
    """
    Negativo: un procedimiento (retorno null) usado como expresión para inicializar integer.
    Debe producir incompatibilidad de tipos en la variable.
    """
    code = """
    function logit() { print(1); }   // retorna null
    let x: integer = logit();        // asignar null a integer debe fallar
    """
    errors, _ = run_semantic(code)
    assert any(
        ("Tipo incompatible" in e or "incompatible" in e) and
        "'x'" in e and
        "null" in e
        for e in errors
    ), errors

def test_cx_llamar_funcion_no_declarada_negativa():
    """
    Negativo: llamada a una función inexistente.
    Debe reportar: "Funcion no declarada: 'foo'"
    """
    code = "let x = foo(1);"
    errors, _ = run_semantic(code)
    assert any("Funcion no declarada: 'foo'" in e for e in errors), errors
