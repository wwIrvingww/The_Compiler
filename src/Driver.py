import sys
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic import AstAndSemantic
from ast_nodes import *

def main(argv):
    input_stream = FileStream(argv[1], encoding='utf-8')
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()  # We are using 'prog' since this is the starting rule based on our Compiscript grammar, yay!

    walker = ParseTreeWalker()
    sem = AstAndSemantic()
    walker.walk(sem, tree)

    print("== ERRORES SEMÁNTICOS ==")
    if sem.errors:
        for e in sem.errors: print("•", e)
    else:
        print("Sin errores")

    print("\n== AST ==")
    print(render_ascii(sem.program))

if __name__ == '__main__':
    main(sys.argv)