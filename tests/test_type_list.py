# /tests/test_type_list.py
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

def test_empty_lists():
    input = """
    let empty = [];
    let empty_int : integer[] = [];
    let empty_str : string[] = [];
    """
    errors, program = run_semantic(input)
    assert program.body[0].ty == "null[]"
    assert program.body[1].ty == "integer[]"
    assert program.body[2].ty == "string[]"
    
    assert errors == [], f"Esperaba sin errores, obtuve: {errors}"

def test_implicit_list_type():
    input = """
    let implicit_int = [1,2,3,4];
    let implicit_str = ["a", "b", "c"];
    """
    errors, program = run_semantic(input)
    assert program.body[0].ty == "integer[]"
    assert program.body[1].ty == "string[]"
    assert errors == [], f"Esperaba sin errores, obtuve: {errors}"

def test_incongruent_list_type():
    input = """
    let error_int : integer[] = [1,2, "a"]
    let error_int2 : integer[] = ["a", "b"]
    let error_str : string[] = ["a", "b", 2]
    let error_str2 : string[] = [1, 2]
    """
    errors, program = run_semantic(input)
    assert len(errors) == 4
    