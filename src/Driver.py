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

    if sem_listener.errors:
        print("== ERRORES SEMÁNTICOS ==")
        for e in sem_listener.errors: print("•", e)
    else:
        print("TAC GEN")
        tac_gen = TacGenerator(sem_listener.table)
        tac_gen.visit(tree)
        

    print("\n== AST ==")
    print(render_ascii(sem_listener.program))
    # Genera imagen (ast.png por defecto) o DOT de fallback
    try:
        path = create_tree_image(sem_listener.program, out_basename="ast", fmt="png")
        print(f"\n[OK] AST exportado a: {path}")
    except Exception as e:
        print(f"\n[WARN] No se pudo exportar imagen: {e}\nSe generó ast.dot (puedes correr `dot -Tpng ast.dot -o ast.png`).")


if __name__ == '__main__':
    main(sys.argv)