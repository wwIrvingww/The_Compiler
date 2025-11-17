from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener
from src.code_generator.mips_generator import MIPSCodeGenerator

import importlib


def code_to_tac(source: str):
    """
    Compila código Compiscript a TAC usando el MISMO pipeline que DriverGen.py:

      1) Lexer + Parser (CompiscriptLexer / CompiscriptParser)
      2) AstAndSemantic (AST + semántica, tabla de símbolos, resolved_symbols)
      3) TacGenerator.visit(tree)  -> tac_gen.code

    Devuelve: lista de TACOP (pero NO filtramos por isinstance para evitar
    el problema de módulos duplicados).
    """

    # -------- 1) Resolver módulos en el mismo "mundo" --------
    # Intentamos primero sin prefijo ("parser", "semantic", "intermediate"),
    # si falla, probamos con "src." ("src.parser", etc).
    prefixes = ["", "src."]

    last_err = None
    CompiscriptLexer = CompiscriptParser = AstAndSemantic = TacGenerator = None

    for base in prefixes:
        try:
            lex_mod = importlib.import_module(base + "parser.CompiscriptLexer")
            par_mod = importlib.import_module(base + "parser.CompiscriptParser")
            sem_mod = importlib.import_module(base + "semantic.ast_and_semantic")
            tac_mod = importlib.import_module(base + "intermediate.tac_generator")

            CompiscriptLexer = lex_mod.CompiscriptLexer
            CompiscriptParser = par_mod.CompiscriptParser
            AstAndSemantic = sem_mod.AstAndSemantic
            TacGenerator = tac_mod.TacGenerator
            break
        except ModuleNotFoundError as e:
            last_err = e
            continue

    if CompiscriptLexer is None:
        raise last_err or ImportError(
            "No se pudieron importar parser/semantic/intermediate "
            "ni con '' ni con 'src.'"
        )

    # -------- 2) ErrorCollector igual que en DriverGen --------
    class ErrorCollector(ErrorListener):
        def __init__(self):
            super().__init__()
            self.errors = []

        def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
            self.errors.append(f"[Line {line}] {msg}")

    # -------- 3) Lexer + Parser sobre el código fuente --------
    input_stream = InputStream(source)

    lexer = CompiscriptLexer(input_stream)
    lexer_err = ErrorCollector()
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_err)

    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)
    parser_err = ErrorCollector()
    parser.removeErrorListeners()
    parser.addErrorListener(parser_err)

    tree = parser.program()

    # -------- 4) AST + semántica (AstAndSemantic) --------
    walker = ParseTreeWalker()
    sem_listener = AstAndSemantic()
    walker.walk(sem_listener, tree)

    all_errors = []
    all_errors.extend(getattr(lexer_err, "errors", []))
    all_errors.extend(getattr(parser_err, "errors", []))
    all_errors.extend(getattr(sem_listener, "errors", []))

    if all_errors:
        print("[code_to_tac] Advertencia: errores detectados:")
        for e in all_errors:
            print("   -", e)
        # AUN ASÍ intentamos generar TAC como hace DriverGen, para que el test
        # de MIPS pueda seguir.

    # -------- 5) Generar TAC con TacGenerator --------
    tac_gen = TacGenerator(sem_listener.table, sem_listener.resolved_symbols)
    # OJO: DriverGen hace tac_gen.visit(tree), no visitProgram(tree)
    tac_gen.visit(tree)

    # El TAC ya está en tac_gen.code
    tac_code = getattr(tac_gen, "code", [])

    # ¡NO filtramos por isinstance(TACOP)! Para evitar el bug de doble módulo.
    return list(tac_code)

# def test_simple_while_to_mips(tmp_path):
#     """
#     Prueba que genera MIPS desde código fuente con un while
#     """
#     source = """
#     let a = 0;
#     while(a < 10){
#         a = a + 1;
#         print(a);
#     }
#     """

#     # 1) Código fuente -> TAC
#     tac = code_to_tac(source)

#     print("\n===== TAC generado =====")
#     for op in tac:
#         print(op)
#     print("===== FIN TAC =====\n")

#     # Sanity mínimo: que no esté vacío y contenga '<' y 'print'
#     assert tac, "El TAC está vacío (no se generó nada)."
#     ops = [getattr(op, "op", None) for op in tac]
#     assert "<" in ops, "El TAC no contiene la comparación '<'"
#     assert "print" in ops, "El TAC no contiene ninguna instrucción 'print'"

#     # 2) TAC -> MIPS
#     gen = MIPSCodeGenerator(tac)
#     asm = gen.generate()

#     # Guardar MIPS en un archivo temporal dentro del contenedor
#     out_file = tmp_path / "generated_mips_while_from_code.asm"
#     out_file.write_text(asm, encoding="utf-8")

#     # 3) Imprimir el MIPS completo en la terminal
#     print("\n===== MIPS generado (while desde código) =====\n")
#     print(asm)
#     print("===== FIN MIPS =====\n")

#     # Sanity: que no esté vacío
#     assert asm.strip() != ""

def test_complex_while_to_mips(tmp_path):
    """
    Código de prueba:

        let a = 0;
        let b = 10;
        let sum = 0;

        while (a < b && sum < 50) {
            a = a + 1;
            sum = sum + a;

            if (sum > 30) {
                let c = 0;
                while (c < a) {
                    c = c + 2;
                }
            } else {
                sum = sum + 1;
            }
        }

    Se convierte a TAC con code_to_tac() y luego a MIPS con MIPSCodeGenerator.
    El MIPS se imprime en la terminal para poder probarlo en QtSpim.
    """
    source = """
    let a = 0;
    let b = 10;
    let sum = 0;

    while (a < b && sum < 50) {
        print("a=");
        print(a);
        print(" sum=");
        print(sum);
        print(" | ");

        a = a + 1;
        sum = sum + a;

        if (sum > 30) {
            let c = 0;
            while (c < a) {
                print("c=");
                print(c);
                print(" ");
                c = c + 2;
            }
            print(" [end inner] ");
        } else {
            sum = sum + 1;
            print("sum_else=");
            print(sum);
            print(" ");
        }
    }
    print("FIN WHILE");
    """

    # 1) Código fuente -> TAC
    tac = code_to_tac(source)

    # print("\n===== TAC generado (while complejo) =====")
    # for op in tac:
    #     print(op)
    # print("===== FIN TAC (while complejo) =====\n")

    # Sanity mínimo: que no esté vacío y tenga control de flujo
    assert tac, "El TAC del while complejo está vacío (no se generó nada)."
    ops = [getattr(op, "op", None) for op in tac]
    assert "if-goto" in ops or "if" in ops, "El TAC no contiene saltos condicionales."
    assert "label" in ops, "El TAC no contiene etiquetas de control de flujo."

    # 2) TAC -> MIPS
    gen = MIPSCodeGenerator(tac)
    asm = gen.generate()

    # Guardar MIPS en un archivo temporal dentro del contenedor
    out_file = tmp_path / "generated_mips_complex_while.asm"
    out_file.write_text(asm, encoding="utf-8")

    # 3) Imprimir el MIPS completo en la terminal
    print("\n===== MIPS generado (while complejo) =====\n")
    print(asm)
    print("===== FIN MIPS (while complejo) =====\n")

    # Sanity: que no esté vacío
    assert asm.strip() != ""
