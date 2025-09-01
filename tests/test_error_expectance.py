# /tests/test_error_expectance.py
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

def test_incompatible_init():
    code = """
    let a : string = 2;
    """
    errors, program = run_semantic(code)
    assert errors[0] == "[line 2] Tipo incompatible en inicializacion de 'a': esperado string, obtenido integer"
    
def test_const_redeclare():
    code = """
    const const_int : integer = 2;
    const_int = 10;
    """
    errors, program = run_semantic(code)
    assert errors[0] == "[line 3] No se puede asignar a const \'const_int\'"
    
def test_not_declared():
    code ="""let x = 1;
    x = 2;
    y = 3;
    """
    errors, program = run_semantic(code)
    assert errors[0] == "[line 3] variable 'y' no declarada"
    