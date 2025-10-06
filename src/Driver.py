import sys
from antlr4 import *
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic
from ast_nodes import create_tree_image, render_ascii
from intermediate.tac_generator import TacGenerator
from intermediate.cfg import build_cfg

def main(argv):
    if len(argv) < 2:
        print("Uso: python src/Driver.py <archivo.cps>")
        sys.exit(1)

    input_path = argv[1]
    input_stream = FileStream(input_path, encoding='utf-8')

    print(f"\n[INFO] Analizando archivo: {input_path}")

    # === FASE 1: LÉXICO + SINTÁCTICO ===
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()

    # === FASE 2: SEMÁNTICO + AST ===
    walker = ParseTreeWalker()
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)

    if sem_listener.errors:
        print("\n== ERRORES SEMÁNTICOS ==")
        for e in sem_listener.errors:
            print("•", e)
        print("\n[ABORTADO] No se generará TAC por errores semánticos.\n")
        return

    print("\n== AST ==")
    print(render_ascii(sem_listener.program))

    # Exportar imagen del AST
    try:
        path = create_tree_image(sem_listener.program, out_basename="ast", fmt="png")
        print(f"\n[OK] AST exportado a: {path}")
    except Exception as e:
        print(f"\n[WARN] No se pudo exportar imagen: {e}")

    # === FASE 3: GENERACIÓN DE TAC ===
    print("\n== GENERANDO TAC ==")
    try:
        tac_gen = TacGenerator(sem_listener.table)
        program_tac = tac_gen.generate(sem_listener.program)


        # Guardar TAC legible y raw
        pretty_out = input_path + ".pretty_tac"
        raw_out = input_path + ".raw_tac"

        with open(pretty_out, "w", encoding="utf-8") as f:
            f.write(program_tac.pretty())
        with open(raw_out, "w", encoding="utf-8") as f:
            for instr in program_tac.instructions:
                f.write(str(instr) + "\n")

        print(f"[OK] TAC generado: {pretty_out}")
        print(f"[OK] Cuádruplas exportadas: {raw_out}")

        # Mostrar resumen del TAC
        print("\n--- TAC (versión legible) ---")
        print(program_tac.pretty(limit=20))  # muestra primeras 20 instrucciones
        print("------------------------------")

        # === FASE 4: CONSTRUCCIÓN DE CFG ===
        try:
            cfg = build_cfg(program_tac.instructions)

            print("\n== CFG ==")
            for b in cfg.blocks:
                print(f"BB{b.id}: [{b.start}..{b.end}] labels={b.labels} succ={b.succ} pred={b.pred}")

            # (Opcional) exportar a DOT para graphviz
            dot_path = input_path + ".cfg.dot"
            with open(dot_path, "w", encoding="utf-8") as f:
                f.write("digraph CFG {\n")
                # nodos
                for b in cfg.blocks:
                    label = f"BB{b.id}\\n[{b.start}..{b.end}]"
                    if b.labels:
                        label += "\\n" + ",".join(b.labels)
                    f.write(f'  BB{b.id} [shape=box,label="{label}"];\n')
                # aristas
                for b in cfg.blocks:
                    for s in b.succ:
                        f.write(f"  BB{b.id} -> BB{s};\n")
                f.write("}\n")
            print(f"[OK] CFG exportado a: {dot_path}")

        except Exception as e:
            print(f"[ERROR] Fallo en la construcción del CFG: {e}")

    except Exception as e:
        print(f"[ERROR] Fallo en la generación de TAC: {e}")

if __name__ == '__main__':
    main(sys.argv)
