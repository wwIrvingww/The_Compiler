import sys
from antlr4 import *
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic
from ast_nodes import render_ascii

def main(argv):
    input_stream = FileStream(argv[1], encoding='utf-8')
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()
    
    walker = ParseTreeWalker()
    
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)

    if sem_listener.errors:
        print("== ERRORES SEMÁNTICOS ==")
        for e in sem_listener.errors: print("•", e)
    else:
        print("Sin errores")

    print("\n== AST ==")
    print(render_ascii(sem_listener.program))

if __name__ == '__main__':
    main(sys.argv)