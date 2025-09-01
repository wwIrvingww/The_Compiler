# /tests/test_loops_and_cond.py
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

def test_for():
    code = """
    for(let i = 0; i<10; i = i+1){
        print("hello world");
        continue:
    }
    """
    errors, _ = run_semantic(code)
    assert len(errors) == 0
    
def test_while():
    code = """
    let i = 10;
    while(i>0){
        print("Hello World!");
        i = i - 1;
    }
    """
    errors, program = run_semantic(code)
    assert len(errors) == 0

def test_do_while():
    code = """
    let i = 10;
    do {
        print("Hello World!");
        i = i - 1;
    } while(i>0);
    """
    errors, program = run_semantic(code)
    assert len(errors) == 0 
    
def test_foreach():
    code = """
    let array : integer[] = [1,2,3,4];
    foreach(i in array){
        print("hello world!");
        continue;
    }
    """
    errors, program = run_semantic(code)
    assert len(errors) ==0
    

def test_if():
    code = """
    let num = 10;
    if(num % 2 == 0){
        print("Hello World!");
    }
    """
    errors, program = run_semantic(code)
    assert len(errors) == 0
    
def test_if_else():
    code = """
    let num = 10;
    if(num % 2 == 0){
        print("Hello World!");
    } else{
        print("Goodbye World :(");
    }
    """
    errors, program = run_semantic(code)
    assert len(errors) == 0
    
def test_switch():
    code = """
    """
    errors, program = run_semantic(code)
    ## TBD
    assert True