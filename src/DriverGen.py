import sys
from antlr4 import *
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic
from ast_nodes import create_tree_image, render_ascii
from intermediate.tac_generator import TacGenerator
def main(argv):
    input_stream = FileStream(argv[1], encoding='utf-8')
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()
    
    walker = ParseTreeWalker()
    
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)

    try:
        path = create_tree_image(sem_listener.program, out_basename="ast", fmt="png")
        print(f"\n[OK] AST exportado a: {path}")
    except Exception as e:
        print(f"\n[WARN] No se pudo exportar imagen: {e}")

    if sem_listener.errors:
        print("== ERRORES SEMÁNTICOS ==")
        for e in sem_listener.errors: print("•", e)
    else:
        tac_gen = TacGenerator(sem_listener.table)
        tac_gen.visit(tree)
        pretty_tac = "\n".join(str(op) for op in tac_gen.code)
        print(pretty_tac)
        with open(f"{argv[1]}.pretty_tac", "w") as f:
            f.write(pretty_tac)
            
        raw_tac = "\n".join(f"{op.op},{op.arg1},{op.arg2},{op.result}" for op in tac_gen.code)
        with open(f"{argv[1]}.raw_tac", "w") as f:
            f.write(raw_tac)
    

if __name__ == '__main__':
    main(sys.argv)