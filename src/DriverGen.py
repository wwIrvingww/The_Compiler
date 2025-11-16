# src/DriverGen.py
import sys
from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic
from ast_nodes import create_tree_image, render_ascii
from intermediate.tac_generator import TacGenerator
from code_generator.pre_analysis import MIPSPreAnalysis
from code_generator.mips_generator import MIPSCodeGenerator
from symbol_table.runtime_validator import validate_runtime_consistency, dump_runtime_info_json
from intermediate.cfg import *

class ErrorCollector(ErrorListener):
    def __init__(self):
        super(ErrorCollector, self).__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"[Line {line}] {msg}")

def main(argv):
    # Param Check
    if len(argv) < 2:
        print("Uso: python src/DriverGen.py <archivo.cps>")
        return 1
    
    # Path define
    
    input_path = argv[1]
    pretty_path = f"{input_path}.pretty_tac"
    raw_path = f"{input_path}.raw_tac"
    
    
    ## 1. Lexic analysis
    input_stream = FileStream(input_path, encoding='utf-8')
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
        print("== ERRORES  ==")
        for e in all_errors:
            print("•", e)
        return 1

    
    # try:
    #     path = create_tree_image(sem_listener.program, out_basename="ast", fmt="png")
    #     print(f"\n[OK] AST exportado a: {path}")
    # except Exception as e:
    #     print(f"\n[WARN] No se pudo exportar imagen: {e}")


    # print("\n== AST ==")
    # try:
    #     print(render_ascii(sem_listener.program))
        
    # except Exception:
    #     print("[WARN] No se puede imprimir AST (render_ascii falló).")

    # Genera imagen (ast.png por defecto) o DOT de fallback
    # try:
    #     path = create_tree_image(sem_listener.program, out_basename="ast", fmt="png")
    #     print(f"\n[OK] AST exportado a: {path}")
    # except Exception as e:
    #     print(f"\n[WARN] No se pudo exportar imagen: {e}\nSe generó ast.dot (puedes correr `dot -Tpng ast.dot -o ast.png`).")

    # 2) Generación de TAC (visitor)
    # print("\n== GENERANDO TAC ==")
    # print(tree.toStringTree(recog=parser))
    
    try:
        # print("Symbol table:")
        # sem_listener.table.print_table()
        # print(sem_listener.resolved_symbols)
        tac_gen = TacGenerator(sem_listener.table, sem_listener.resolved_symbols)
        # Recorrido del AST (visitor); genera tac y, si corresponde, frames via FrameManager
        tac_gen.visit(tree)
        print("\n== MIPS GENERATION ==")
        
        mips_gen = MIPSCodeGenerator(tac_gen.code, tac_gen.frame_manager)
        asm_str = mips_gen.generate()
        # print(asm_str)
        with open(f"{input_path}.asm", "w") as pp:
            pp.write(asm_str)
        # Ejecutar pre-análisis
        # pre_analysis = MIPSPreAnalysis(tac_gen.code, tac_gen.frame_manager)
        # pre_analysis.analyze()
        # pre_analysis.print_summary()
    except Exception as e:
        print(f"[ERROR] Fallo en la generación de TAC: {e}")
        raise

    cfg_ = build_cfg(tac_gen.code)
    print("=== Control Flow Graph ===")
    cfg_ = build_cfg(tac_gen.code)
    vis_cfg(cfg_, "./cfg_vis")
    # -------------------------
    # 3) VALIDACIÓN RUNTIME (integración)
    # Aquí integramos el validador que verifica consistencia SymbolTable <-> FrameManager.
    # Se ejecuta justo después de generar el TAC y antes de terminar el driver.
    # -------------------------
    # try:
    #     errors = validate_runtime_consistency(sem_listener.table, tac_gen.frame_manager)
    #     if errors:
    #         print("\n== RUNTIME VALIDATION ERRORS ==")
    #         for er in errors:
    #             print("•", er)
    #     else:
    #         pass
    #         # print("\n[OK] Runtime layout: validación pasada (no se detectaron inconsistencias).")
    #     # Además volcamos JSON con la estructura de frames (útil para el IDE)
    #     frames_json = dump_runtime_info_json(tac_gen.frame_manager)
    #     out_json = f"{input_path}.frames.json"
    #     with open(out_json, "w", encoding="utf-8") as f:
    #         f.write(frames_json)
    #     print(f"[INFO] Frames JSON escrito: {out_json}")
    # except Exception as e:
    #     print(f"[WARN] No se pudo validar layout runtime: {e}")

    # 4) Emitir TAC en consola (opcional: tac_gen ya pudo haber impreso o escrito archivos)
    
    # pretty_tac = "\n".join(str(taco) for taco in tac_gen.code)
    pretty_tac = ""
    for taco in tac_gen.code:
        if (str(taco).startswith("FN")):
            pretty_tac+=f"\n{str(taco)[3:]}:"
        elif (str(taco).startswith("label")):
            pretty_tac+=f"\n\t{str(taco)}"
        else:
            pretty_tac+=f"\n\t\t{str(taco)}"
    # print(pretty_tac)
    
    
    
    try:
        # tac_gen.code (lista de ops) o tac_gen.emit_pretty() según implementacion
        pretty_tac = "\n".join(str(taco) for taco in tac_gen.code)
        with open(pretty_path, "w") as pp:
            pp.write(pretty_tac)
        
        raw_tac = "\n".join(f"{taco.result},{taco.op},{taco.arg1},{taco.arg2}" for taco in tac_gen.code)
        with open(raw_path, "w") as rp:
            rp.write(raw_tac)
        
        
        # if hasattr(tac_gen, "emit_pretty"):
        #     # print("\n== TAC (pretty) ==")
        #     pretty_tac = "\n".join(str(taco) for taco in tac_gen.code)
        #     for line in getattr(tac_gen, "code", []):
        #         print(line)
            
        #     with open(pretty_tac)
        #     print(tac_gen.emit_pretty())
        # elif hasattr(tac_gen, "code"):
        #     raw_tac = "\n".join(f"{taco.result},{taco.op},{taco.arg1},{taco.arg2}" for taco in tac_gen.code)

    except Exception:
        pass

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
