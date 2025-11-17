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

def test_simple_while_to_mips(tmp_path):
    """
    Caso sencillo de while
    """
    source = """
    let a = 0;
    while(a < 10){
        a = a + 1;
        print(a);
    }
    """

    # 1) Código fuente -> TAC
    tac = code_to_tac(source)

    # print("\n===== TAC generado (while simple) =====")
    # for op in tac:
    #     print(op)
    # print("===== FIN TAC (while simple) =====\n")

    # Sanity mínimo: que no esté vacío y contenga '<' y 'print'
    assert tac, "El TAC está vacío (no se generó nada)."
    ops = [getattr(op, "op", None) for op in tac]
    assert "<" in ops, "El TAC no contiene la comparación '<'"
    assert "print" in ops, "El TAC no contiene ninguna instrucción 'print'"

    # 2) TAC -> MIPS
    gen = MIPSCodeGenerator(tac)
    asm = gen.generate()

    # Guardar MIPS en un archivo temporal dentro del contenedor
    out_file = tmp_path / "generated_mips_while_from_code.asm"
    out_file.write_text(asm, encoding="utf-8")

    # 3) Imprimir el MIPS completo en la terminal
    # print("\n===== MIPS generado (while simple) =====\n")
    # print(asm)
    # print("===== FIN MIPS (while simple) =====\n")

    # Sanity: que no esté vacío
    assert asm.strip() != ""

def test_complex_while_to_mips(tmp_path):
    """
    Código de prueba con while complejo:
      - condición compuesta (&&)
      - if dentro del while
      - while dentro del if
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
    # print("\n===== MIPS generado (while complejo) =====\n")
    # print(asm)
    # print("===== FIN MIPS (while complejo) =====\n")

    # Sanity: que no esté vacío
    assert asm.strip() != ""

def test_for_simple_to_mips(tmp_path):
    """
    Caso sencillo de for
    """
    source = """
    let i = 0;
    let sum = 0;

    for (i = 0; i < 4; i = i + 1) {
        sum = sum + i;
        print(i);
        print(sum);
    }
    """

    # 1) Código fuente -> TAC
    tac = code_to_tac(source)

    # print("\n===== TAC generado (for simple) =====")
    # for op in tac:
    #     print(op)
    # print("===== FIN TAC (for simple) =====\n")

    # Sanity mínimo
    assert tac, "El TAC del for simple está vacío."
    ops = [getattr(op, "op", None) for op in tac]
    assert "if-goto" in ops or "goto" in ops, "El TAC no parece tener control de flujo."
    assert "print" in ops, "El TAC no contiene ningún print."

    # 2) TAC -> MIPS
    gen = MIPSCodeGenerator(tac)
    asm = gen.generate()

    # Guardar el MIPS en archivo temporal
    out_file = tmp_path / "generated_mips_for_simple.asm"
    out_file.write_text(asm, encoding="utf-8")

    # 3) Imprimir MIPS para copiar a QtSpim
    # print("\n===== MIPS generado (for simple) =====\n")
    # print(asm)
    # print("===== FIN MIPS (for simple) =====\n")

    assert asm.strip() != ""

def test_for_complex_to_mips(tmp_path):
    """
    Caso complejo de for con:
      - dos fors anidados
      - if dentro del for interno
      - varias impresiones para seguir el flujo
    """
    source = """
    let total = 0;

    for (let i = 0; i < 3; i = i + 1) {
        for (let j = 0; j < 3; j = j + 1) {
            let s = i + j;
            print("i=");
            print(i);
            print(" j=");
            print(j);
            if (s > 2) {
                print(" s=");
                print(s);
                print(" total before=");
                print(total);
                total = total + s;
                print(" total=");
                print(total);
            } else {
                print(" s=");
                print(s);
            }
            print(" | ");
        }
        print(" [end outer iteration] ");
    }
    print("FINAL TOTAL=");
    print(total);
    """

    # 1) Código fuente -> TAC
    tac = code_to_tac(source)

    # print("\n===== TAC generado (for complejo) =====")
    # for op in tac:
    #     print(op)
    # print("===== FIN TAC (for complejo) =====\n")

    # Sanity mínimo
    assert tac, "El TAC del for complejo está vacío."
    ops = [getattr(op, "op", None) for op in tac]
    assert "if-goto" in ops, "El TAC no contiene saltos condicionales (if-goto)."
    assert "label" in ops, "El TAC no contiene etiquetas de control de flujo."
    assert "print" in ops, "El TAC no contiene ningún print."

    # 2) TAC -> MIPS
    gen = MIPSCodeGenerator(tac)
    asm = gen.generate()

    # Guardar el MIPS en archivo temporal
    out_file = tmp_path / "generated_mips_for_complex.asm"
    out_file.write_text(asm, encoding="utf-8")

    # 3) Imprimir MIPS para copiar a QtSpim
    print("\n===== MIPS generado (for complejo) =====\n")
    print(asm)
    print("===== FIN MIPS (for complejo) =====\n")

    assert asm.strip() != ""
