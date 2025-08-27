import pytest
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic

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

def test_ok_function_call_and_return_type():
    code = """
    function sum(a: integer, b: integer): integer {
        return a + b;
    }
    let r: integer = sum(1, 2);
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_arity_mismatch():
    code = """
    function f(a: integer): integer { return a; }
    let x: integer = f(1, 2);
    """
    errors, _ = run_semantic(code)
    assert any("Numero de argumentos invalido" in e for e in errors), errors

def test_arg_type_mismatch():
    code = """
    function f(a: integer, b: integer): integer { return a + b; }
    let x: integer = f(1, true);
    """
    errors, _ = run_semantic(code)
    assert any("Argumento 2 invalido" in e for e in errors), errors

def test_recursion_allowed():
    code = """
    function fact(n: integer): integer {
        if (n == 0) { return 1; }
        return n * fact(n - 1);
    }
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_procedure_cannot_return_value():
    code = """
    function p() { return 1; } // sin tipo de retorno => null
    """
    errors, _ = run_semantic(code)
    assert any("Tipo de retorno incompatible" in e for e in errors), errors

def test_missing_return_is_ok_for_null():
    code = """
    function p() { } // ok: retorna null implicito
    """
    errors, _ = run_semantic(code)
    assert errors == [], errors

def test_return_type_mismatch():
    code = """
    function bad(a: integer): integer {
        return "hola";
    }
    """
    errors, _ = run_semantic(code)
    assert any("Tipo de retorno incompatible" in e for e in errors), errors

def test_procedure_return_value_not_allowed():
    # Sin anotación de retorno => se interpreta como null
    code = """
    function p(a: integer) { 
        return 1;   // devolver un valor en "procedimiento" debe marcar error
    }
    """
    errors, _ = run_semantic(code)
    assert any("Tipo de retorno incompatible" in e and "esperado null" in e for e in errors), errors

def test_use_procedure_as_expression_fails_assignment():
    code = """
    function logit() { print(1); }   // retorna null
    let x: integer = logit();        // asignar null a integer debe fallar
    """
    errors, _ = run_semantic(code)
    # Es una incompatibilidad en la inicialización de la variable 'x'
    assert any(
        ("Tipo incompatible" in e or "incompatible" in e) and
        "'x'" in e and
        "obtenido null" in e
        for e in errors
    ), errors

def test_call_undefined_function():
    code = "let x = foo(1);"
    errors, _ = run_semantic(code)
    assert any("Funcion no declarada: 'foo'" in e for e in errors), errors

def test_nested_function_sees_outer_var():
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

def test_function_redeclaration_in_same_scope():
    code = """
    function f(a: integer): integer { return a; }
    function f(b: integer): integer { return b; } // redeclaracion
    """
    errors, _ = run_semantic(code)
    assert any(("definido" in e or "ambito actual" in e) and "'f'" in e for e in errors), errors
