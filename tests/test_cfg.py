# from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
# from src.parser.CompiscriptLexer import CompiscriptLexer
# from src.parser.CompiscriptParser import CompiscriptParser
# from src.semantic.ast_and_semantic import AstAndSemantic
# from src.intermediate.tac_generator import TacGenerator
# from src.intermediate.cfg import build_cfg

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
#     return gen.get_code()

# def _label2idx(tac):
#     return {ins.result: i for i, ins in enumerate(tac) if ins.op == "label" and ins.result}

# def _has_back_edge(cfg):
#     return any(any(s < b.id for s in b.succ) for b in cfg.blocks)

# def _has_back_edge_by_label(tac, cfg):
#     # Busca un if-goto con destino a un bloque con id <= al bloque actual.
#     labels = {i.result: k for k, i in enumerate(tac) if i.op == "label" and i.result}
#     ifg_idxs = [k for k, i in enumerate(tac) if i.op == "if-goto" and i.arg2 in labels]
#     if not ifg_idxs:
#         return False

#     def _block_of_insn(idx):
#         for b in cfg.blocks:
#             if b.start <= idx <= b.end:
#                 return b.id
#         return None

#     for idx in ifg_idxs:
#         curr_bid = _block_of_insn(idx)
#         tgt_label = tac[idx].arg2
#         tgt_bid = cfg.label2block.get(tgt_label)
#         if curr_bid is not None and tgt_bid is not None and tgt_bid <= curr_bid:
#             return True
#     return False

# def test_cfg_if_simple():
#     code = """
#     let x: integer = 0;
#     if (x < 10) { x = x + 1; }
#     """
#     tac = _tac(code)
#     cfg = build_cfg(tac)
#     # Debe haber al menos 2 bloques (condición y then)
#     assert len(cfg.blocks) >= 2
#     # Debe existir algún if-goto / goto en el último TAC del bloque condicional
#     cond_block = cfg.blocks[0]
#     last = tac[cond_block.end]
#     assert last.op in {"if-goto", "goto"} or any(b.labels for b in cfg.blocks)

# def test_cfg_if_else():
#     code = """
#     let x: integer = 0;
#     if (x < 10) { x = 1; } else { x = 2; }
#     """
#     tac = _tac(code)
#     cfg = build_cfg(tac)
#     # Al menos 3 bloques: cond, then, else (y usualmente un cuarto de salida)
#     assert len(cfg.blocks) >= 3

#     # El bloque de condición debe terminar en salto condicional
#     cond = cfg.blocks[0]
#     last = tac[cond.end]
#     assert last.op in {"if-goto", "goto"}
#     # Debe tener exactamente 2 sucesores (rama y caída)
#     assert len(cond.succ) == 2

# def test_cfg_if_else_nested():
#     code = """
#     let x: integer = 0;
#     if (x < 10) {
#         if (x == 0) { x = 1; } else { x = 2; }
#     } else {
#         x = 3;
#     }
#     """
#     tac = _tac(code)
#     cfg = build_cfg(tac)
#     assert len(cfg.blocks) >= 4  # cond outer + (then-cond + then-branches) + else + end

#     cond0 = cfg.blocks[0]
#     last0 = tac[cond0.end]
#     assert last0.op in {"if-goto", "goto"}
#     # el primer bloque (cond externo) debe tener 2 sucesores
#     assert len(cond0.succ) == 2

# def test_cfg_while_back_edge():
#     code = """
#     let i: integer = 0;
#     while (i < 3) {
#       i = i + 1;
#     }
#     """
#     tac = _tac(code)
#     cfg = build_cfg(tac)

#     assert _has_back_edge(cfg)

#     cond_blocks = [b for b in cfg.blocks if tac[b.end].op == "if-goto"]
#     assert cond_blocks, "No se encontró bloque condicional (if-goto)"
#     cond_blk = cond_blocks[0]
#     last = tac[cond_blk.end]
#     assert last.op in {"if-goto", "goto"}

# def test_cfg_do_while_back_edge():
#     code = """
#     let i: integer = 0;
#     do {
#       i = i + 1;
#     } while (i < 3);
#     """
#     tac = _tac(code)
#     cfg = build_cfg(tac)
#     assert _has_back_edge(cfg) or _has_back_edge_by_label(tac, cfg)
#     assert any(i.op == "if-goto" for i in tac)

# def test_cfg_function_labels_present():
#     code = """
#     function f(a: integer, b: integer): integer {
#         if (a < b) { return a; }
#         return b;
#     }
#     """
#     tac = _tac(code)
#     cfg = build_cfg(tac)
#     labels = _label2idx(tac)
#     # Por convención del generador: "func_f_entry" / "func_f_exit"
#     assert any("func_f_entry" in L for L in labels)
#     assert any("func_f_exit"  in L for L in labels)

#     # Y el grafo debe tener al menos un bloque con 'return'
#     ends = [tac[b.end].op for b in cfg.blocks if b.start <= b.end]
#     assert "return" in ends