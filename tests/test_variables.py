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

def test_assign_to_undeclared_variable():
    tree = parse("b = 10;")
    errors = FlowValidator.validate(tree)
    print(errors)
    # esperamos un mensaje indicando que 'b' no fue declarada
    assert any("variable 'b' no declarada" in e for e in errors)

def test_declared_then_assigned_ok():
    code = "let b : integer = 0; b = 10;"
    errors = FlowValidator.validate(parse(code))
    assert errors == []

def test_declared_without_init_then_assigned_ok():
    code = "let b : integer; b = 10;"
    errors = FlowValidator.validate(parse(code))
    assert errors == []

def test_use_variable_in_initializer_ok():
    code = """
    let a : integer = 5;
    let b : integer = a;
    """
    errors = FlowValidator.validate(parse(code))
    assert errors == []
