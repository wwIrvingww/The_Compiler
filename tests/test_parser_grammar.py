import pytest
from antlr4 import InputStream, CommonTokenStream
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser


def parse_code(src: str):
    """
    Helper que recibe código fuente como string,
    lo parsea con ANTLR y devuelve el parser.
    """
    lexer = CompiscriptLexer(InputStream(src))
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    parser.removeErrorListeners()
    parser.program()
    return parser


# ---------------- PRUEBAS POSITIVAS ---------------- #

@pytest.mark.parametrize("code", [
    "let x: integer = 5;",
    "var y = 10;",
    "const z: string = \"hola\";",
    "print(1+2);",
    "if (true) { print(\"ok\"); } else { print(\"no\"); }",
    "while (false) { var i = 0; }",
    "do { var j = 1; } while (true);",
    "for (var i=0; i<10; i=i+1) { print(i); }",
    "function f(a: integer) { return a+1; }",
    "class C { function m() { return 42; } }",
    "let a: integer[] = [1,2,3]; print(a[0]);",
])
def test_valid_programs_parse_ok(code):
    parser = parse_code(code)
    assert parser.getNumberOfSyntaxErrors() == 0


# ---------------- PRUEBAS NEGATIVAS ---------------- #

@pytest.mark.parametrize("code", [
    "let = 5;",                  # falta identificador
    "if (1 { print(1); }",       # paréntesis faltante
    "function f( { }",           # parámetros mal formados
    "class { }",                 # clase sin nombre
    "return",                    # falta punto y coma
    "for i in range(10) { }",    # sintaxis inválida
])
def test_invalid_programs_have_errors(code):
    parser = parse_code(code)
    assert parser.getNumberOfSyntaxErrors() > 0
