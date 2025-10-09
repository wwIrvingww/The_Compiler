# src/CompilerServer.py
from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Literal
import re

from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic
from intermediate.tac_generator import TacGenerator


app = FastAPI()

class InputCode(BaseModel):
    source: str
class OutputCode(BaseModel):
    result: str
    errors: List[str] = []

class Errors(BaseModel):
    line: int
    message: str
    severity: Literal["error", "warning"]
class Diagnostics(BaseModel):
    diagnostics: List[Errors]

class ErrorCollector(ErrorListener):
    def __init__(self):
        super(ErrorCollector, self).__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"[Line {line}] {msg}")


def compile_driver(
    code:str,
    mode:str
    ) -> OutputCode:
    
    # Lexic/Syntax
    input_stream = InputStream(code)
    lexer = CompiscriptLexer(input_stream)
    lexer_error_listener = ErrorCollector()
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_error_listener)
    
    ## 2. Semantic Analysis
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    parser_error_listener = ErrorCollector()
    parser.removeErrorListeners()
    parser.addErrorListener(parser_error_listener)

    tree = parser.program()

    # 1) Análisis semántico (listeners)
    walker = ParseTreeWalker()
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)

    all_errors = lexer_error_listener.errors + parser_error_listener.errors + sem_listener.errors
    if all_errors:
        
        return OutputCode(result="== ERRORS ==", errors=all_errors)
    
    tac_gen = TacGenerator(sem_listener.table)
    tac_gen.visit(tree)
    
    if mode=="pretty":
        pretty_tac = "\n".join(str(taco) for taco in tac_gen.code)
        return OutputCode(result=str(pretty_tac), errors=[])
    else: 
        raw_tac = "\n".join(f"{taco.result},{taco.op},{taco.arg1},{taco.arg2}" for taco in tac_gen.code)
        return OutputCode(result=str(raw_tac), errors=[])

def diagnostics_driver(
        code: str
    )->Diagnostics:
    # Lexic/Syntax
    # Lexic/Syntax
    input_stream = InputStream(code)
    lexer = CompiscriptLexer(input_stream)
    lexer_error_listener = ErrorCollector()
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_error_listener)
    
    ## 2. Semantic Analysis
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    parser_error_listener = ErrorCollector()
    parser.removeErrorListeners()
    parser.addErrorListener(parser_error_listener)

    tree = parser.program()

    # 1) Análisis semántico (listeners)
    walker = ParseTreeWalker()
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)

    all_errors = lexer_error_listener.errors + parser_error_listener.errors + sem_listener.errors

    diags = []
    if all_errors:
        for e in all_errors:
            end_idx = e.index("]")
            line_str = e[6:end_idx]
            line = int(line_str.strip())
            msg = e[end_idx+2:]
            diags.append(Errors(line=line, message=msg, severity="error"))
    
    return Diagnostics(diagnostics=diags)
    
    

@app.get("/")
def root():
    return {"message", "Hello from Compiscript Compiler service!"}


## Diagnostic endpoints
@app.post("/diagnostics", response_model=Diagnostics)
def test(payload: InputCode):
    code = payload.source
    return diagnostics_driver(code)


## Compile endpoints
@app.post("/tac/pretty", response_model=OutputCode)
def generate_tac_pretty(payload: InputCode):
    try: 
        return compile_driver(payload.source, mode="pretty")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/tac/quadruplet", response_model=OutputCode)
def generate_tac_pretty(payload: InputCode):
    try: 
        return compile_driver(payload.source, mode="raw")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))