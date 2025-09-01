import pytest
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic

# /tests/test_list_index.py

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

def test_correct_primary_type():
    input ="""
    let tem : integer[][][];
    tem = [[[1]]];
    tem[1] = [[1]];
    tem[1][1] = [1];
    tem[1][1][1] = 1;
    
    """
    # Indexacion por entero
    errors, program = run_semantic(input)
    assert len(errors) == 0
    
def test_incorrect_primary_type():
    input ="""
    let tem : integer[][][];
    
    // Expected: int[][] received int
    tem[1] = 1; // Expected: int[][] received int
    
    // Expected int[] received int[][]
    tem[1][1] = [[1,2], [3,4]];
    
    // Expected int received int[]
    tem[1][3][4] = [1];
    """
    # Indexacion por entero
    errors, program = run_semantic(input)
    assert errors[0] == "Tipo de asignacion incompatible: esperado integer[][], obtenido integer"
    assert errors[1] == "Tipo de asignacion incompatible: esperado integer[], obtenido integer[][]"
    assert errors[2] == "Tipo de asignacion incompatible: esperado integer, obtenido integer[]"
    
def test_index_by_int():
    input ="""
    let tem1 : integer[];
    tem1["a"] = 1;
    tem1[true] = 1;
    tem1[null] = 1;
    """
    # Indexacion por entero
    errors, program = run_semantic(input)
    print(program)
    # 2 por cada iniciacion, uno por indice no entero, y otro por incializacion
    assert len(errors) == 3
    
def test_index_in_op():
    input ="""
    let tem1 : integer[];
    let b = 5 * tem1[1]/tem1[2] + tem1[3];
    
    let bol_arr : boolean[];
    let value = bol_arr[1] && bol_arr[2] || bol_arr[3];
    """
    # Indexacion por entero
    errors, program = run_semantic(input)
    assert len(errors) == 0