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
    
def test_switch_positive():
    code = """
    let tem : integer = 10;
    let tem_str : string = "hola";
    switch(tem){
        case 1: 
            print("es 1");
        default:
            switch(tem_str){
                case "hola":
                    print("Es saludo");
                case "adios":
                    print("es despedida");
                default:
                    print("No es saludo ni despdedida");
            }
    }
    """
    errors, program = run_semantic(code)
    assert len(errors) == 0
    
def test_switch_negative():
    # Sin casos
    code1 = """
    let tem = 1;
    switch(tem){}
    """
    errors1, _ = run_semantic(code1)
    assert any("debe tener al menos un caso" in e for e in errors1), errors1
    
    # Casos repetidos
    code2 = """
    let tem = 1;
    switch(tem){
        case 1:
            print("es 1");
        case 1:
            print("repetido");
    }
    """
    errors2, _ = run_semantic(code2)
    assert any("caso repetido en sentencia \'switch\'" in e for e in errors2), errors2
    
    # Tipos no concuerdan
    code3 = """
    let tem : string = "hola";
    switch(tem){
        case 1:
            print("es 1");
        default:
            print("default");
    }
    """
    errors3, _ = run_semantic(code3)
    assert any("\'case\' debe tener el mismo tipo que la expresion" in e for e in errors3), errors3
    
    
    
    
    