# src/DriverGen.py
import sys
from antlr4 import *
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic
from ast_nodes import create_tree_image, render_ascii
from intermediate.tac_generator import TacGenerator
from symbol_table.runtime_validator import validate_runtime_consistency, dump_runtime_info_json

def main(argv):
    # Argument check
    if len(argv) < 2:
        print("Uso: python src/DriverGen.py <archivo.cps>")
        return 1
    # Path init
    input_path = argv[1]
    pretty_path = f"{input_path}.pretty_tac"
    raw_path = f"{input_path}.raw_tac"
    frame_path = f"{input_path}.frames.json"

    ## 1) Lexic-syntax
    input_stream = FileStream(input_path, encoding='utf-8')
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()

    ## 2) function to return contents
    def export_contents(raw : list, no_errors: bool = True):
        if no_errors:
            pretty_tac = "\n".join(str(taco) for taco in tac_gen.code)
            raw_tac = "\n".join(f"{taco.result},{taco.op},{taco.arg1},{taco.arg2}" for taco in tac_gen.code)
            with open(pretty_path, "w") as pp:
                pp.write(pretty_tac)
            with open(raw_path, "w") as rp:
                rp.write(raw_tac)
        else:
            errors = "\n".join(f"•{e}\n" for e in sem_listener.errors)
            with open(pretty_path, "w") as pp:
                pp.write(errors)
            with open(raw_path, "w") as rp:
                rp.write(errors)
            
    ## 3) Análisis semántico (listeners)
    walker = ParseTreeWalker()
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)
    
    if sem_listener.errors:
        export_contents(sem_listener.errors, no_errors=False)
        return 1

    ## 4) Tac Generation
    try:
        tac_gen = TacGenerator(sem_listener.table)
        tac_gen.visit(tree)
    except Exception as e:
        error = [f"[ERROR] Fallo en la generación de TAC: {e}"]
        export_contents(error, no_errors=False)
        return 1
    
    ## 5) Runtime Validation
    try:
        errors = validate_runtime_consistency(sem_listener.table, tac_gen.frame_manager)
        if errors:
            export_contents(errors, no_errors=False)
            
        ## Export runtime frames=
        frames_json = dump_runtime_info_json(tac_gen.frame_manager)
        with open(frame_path, "w", encoding="utf-8") as f:
            f.write(frames_json)
            
    except Exception as e:
        err = [f"[WARN] No se pudo validar layout runtime: {e}"]
        export_contents(err, no_errors=False)

    # 6) Emitir TAC
    export_contents(tac_gen.code)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
