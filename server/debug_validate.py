# server/debug_validate.py
import sys
import pathlib
import logging

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.DEBUG, format="DEBUG:%(name)s:%(message)s")

def main(path_to_file=None):
    from antlr4 import FileStream, InputStream, CommonTokenStream
    from parser.CompiscriptLexer import CompiscriptLexer
    from parser.CompiscriptParser import CompiscriptParser
    from semantic.flow_validator import FlowValidator

    if path_to_file is None:
        path_to_file = str(ROOT / "examples" / "example.cps")

    print("Using file:", path_to_file)
    with open(path_to_file, "r", encoding="utf8") as f:
        code = f.read()

    print("\n-- CODE --\n", code)
    inp = InputStream(code)
    lexer = CompiscriptLexer(inp)
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)

    # print some tokens (first 200)
    tokens.fill()
    print("\n-- TOKENS (first 50) --")
    for i, t in enumerate(tokens.tokens[:50]):
        print(i, repr(str(t.text)), "type=", t.type, "line=", t.line, "col=", t.column)

    # parse tree string
    tree = parser.program()
    try:
        print("\n-- ParseTree (toStringTree) --")
        print(tree.toStringTree(recog=parser))
    except Exception as e:
        print("Could not toStringTree:", e)

    print("\n-- Running FlowValidator.validate(tree) --")
    try:
        errs = FlowValidator.validate(tree)
        print("FlowValidator returned:", type(errs), repr(errs))
        if errs:
            for e in errs:
                print("  >>", e)
        else:
            print("  (no errors)")
    except Exception as e:
        print("FlowValidator.validate raised exception:", e)
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)
