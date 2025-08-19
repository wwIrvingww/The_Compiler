import pytest
from antlr4 import InputStream, CommonTokenStream
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.flow_validator import FlowValidator

def parse(src: str):
    input_stream = InputStream(src)
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    return parser.program()

def test_return_fuera_de_funcion():
    tree = parse("return 5;")
    errors = FlowValidator.validate(tree)
    assert any("fuera de función" in e for e in errors)

def test_return_dentro_de_funcion_ok():
    code = """
    function foo() {
        return true;
    }
    """
    errors = FlowValidator.validate(parse(code))
    assert errors == []

def test_if_condicion_no_booleana():
    tree = parse("if (123) { }")
    errors = FlowValidator.validate(tree)
    assert any("condición de 'if' no es boolean" in e for e in errors)

def test_while_condicion_no_booleana():
    tree = parse("while (x) { }")
    errors = FlowValidator.validate(tree)
    assert any("condición de 'while' no es boolean" in e for e in errors)

def test_for_condicion_no_booleana():
    code = "for (; \"hola\"; ) { }"
    errors = FlowValidator.validate(parse(code))
    assert any("condición de 'for' no es boolean" in e for e in errors)

def test_flujo_valido_sin_errores():
    code = """
    function bar() {
      if (true) { }
      while (false) { }
      for (; true; ) { }
      return false;
    }
    """
    errors = FlowValidator.validate(parse(code))
    assert errors == []
