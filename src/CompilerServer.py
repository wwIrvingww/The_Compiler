# src/CompilerServer.py
from antlr4 import *
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Literal
import re

from src.parser.CompiscriptLexer import CompiscriptLexer
from src.parser.CompiscriptParser import CompiscriptParser
from src.semantic.ast_and_semantic import AstAndSemantic
from src.intermediate.tac_generator import TacGenerator


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

def compile_driver(
    code:str,
    mode:str
    ) -> OutputCode:
    
    # Lexic/Syntax
    input_stream = InputStream(code)
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()
    # Semantic
    walker = ParseTreeWalker()
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)
    
    if sem_listener.errors:
        return OutputCode(result="", errors=sem_listener.errors)
    
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
    input_stream = InputStream(code)
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()
    # Semantic
    walker = ParseTreeWalker()
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)
    diags = []
    if sem_listener.errors:
        for e in sem_listener.errors:
            match = re.search(r'\[line (\d+)\] (.*)', e)
            line = match.group(1)
            msg = match.group(2)
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