# src/DriverGen.py

import os
print(os.getcwd())

import sys
from antlr4 import *
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic
from ast_nodes import create_tree_image, render_ascii

# Tac generator (visitor)
from intermediate.tac_generator import TacGenerator

# Runtime validator (la que creamos antes)
from symbol_table.runtime_validator import validate_runtime_consistency, dump_runtime_info_json

def main(argv):
    if len(argv) < 2:
        print("Uso: python src/DriverGen.py <archivo.cps>")
        return 1

    
    input_path = argv[1]
    pretty_path = f"{input_path}.pretty_tac"
    raw_path = f"{input_path}.raw_tac"
    # print(f"[INFO] Analizando archivo: {input_path}\n")

    input_stream = FileStream(input_path, encoding='utf-8')
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()

    # 1) Análisis semántico (listeners)
    walker = ParseTreeWalker()
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)

    # try:
    #     path = create_tree_image(sem_listener.program, out_basename="ast", fmt="png")
    #     print(f"\n[OK] AST exportado a: {path}")
    # except Exception as e:
    #     print(f"\n[WARN] No se pudo exportar imagen: {e}")

    if sem_listener.errors:
        print("== ERRORES SEMÁNTICOS ==")
        for e in sem_listener.errors:
            print("•", e)
        return 1

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
    try:
        tac_gen = TacGenerator(sem_listener.table)
        # Recorrido del AST (visitor); genera tac y, si corresponde, frames via FrameManager
        tac_gen.visit(tree)
    except Exception as e:
        print(f"[ERROR] Fallo en la generación de TAC: {e}")
        raise

    # -------------------------
    # 3) VALIDACIÓN RUNTIME (integración)
    # Aquí integramos el validador que verifica consistencia SymbolTable <-> FrameManager.
    # Se ejecuta justo después de generar el TAC y antes de terminar el driver.
    # -------------------------
    try:
        errors = validate_runtime_consistency(sem_listener.table, tac_gen.frame_manager)
        if errors:
            print("\n== RUNTIME VALIDATION ERRORS ==")
            for er in errors:
                print("•", er)
        else:
            pass
            # print("\n[OK] Runtime layout: validación pasada (no se detectaron inconsistencias).")
        # Además volcamos JSON con la estructura de frames (útil para el IDE)
        frames_json = dump_runtime_info_json(tac_gen.frame_manager)
        out_json = f"{input_path}.frames.json"
        with open(out_json, "w", encoding="utf-8") as f:
            f.write(frames_json)
        print(f"[INFO] Frames JSON escrito: {out_json}")
    except Exception as e:
        print(f"[WARN] No se pudo validar layout runtime: {e}")

    # 4) Emitir TAC en consola (opcional: tac_gen ya pudo haber impreso o escrito archivos)
    pretty_tac = "\n".join(str(taco) for taco in tac_gen.code)
    print(pretty_tac)
    
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
