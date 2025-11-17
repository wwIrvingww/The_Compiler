# # tests/test_tac_functions.py
# from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
# from src.parser.CompiscriptLexer import CompiscriptLexer
# from src.parser.CompiscriptParser import CompiscriptParser
# from src.semantic.ast_and_semantic import AstAndSemantic
# from src.intermediate.tac_generator import TacGenerator

# def _tac(code: str):
#     input_stream = InputStream(code)
#     lx = CompiscriptLexer(input_stream)
#     ts = CommonTokenStream(lx)
#     ps = CompiscriptParser(ts)
#     tree = ps.program()

#     sem = AstAndSemantic()
#     ParseTreeWalker().walk(sem, tree)
#     assert sem.errors == [], f"Semánticos: {sem.errors}"

#     gen = TacGenerator(sem.table)
#     gen.visit(tree)
#     get_code = getattr(gen, "get_code", None)
#     return get_code() if callable(get_code) else gen.code

# def test_tac_function_decl_labels_and_return():
#     code = """
#     function f(a: integer, b: integer): integer {
#         return a + b;
#     }
#     """
#     tac = _tac(code)

#     # 1) Labels de función (entry/exit)
#     has_entry = any(i.op == "label" and i.result == "func_f_entry" for i in tac)
#     has_exit  = any(i.op == "label" and i.result == "func_f_exit"  for i in tac)
#     assert has_entry, "Falta label 'func_f_entry'"
#     assert has_exit,  "Falta label 'func_f_exit'"

#     # 2) Alguna operación binaria en el cuerpo (suma)
#     has_sum = any(i.op == "+" for i in tac)
#     assert has_sum, "Se esperaba una operación de suma (+) en el cuerpo"

#     # 3) Instrucción de retorno
#     has_return = any(i.op == "return" for i in tac)
#     assert has_return, "Se esperaba instrucción 'return' en el cuerpo"
