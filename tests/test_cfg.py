from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from src.parser.CompiscriptLexer import CompiscriptLexer
from src.parser.CompiscriptParser import CompiscriptParser
from src.semantic.ast_and_semantic import AstAndSemantic
from src.intermediate.tac_generator import TacGenerator
from src.intermediate.cfg import build_cfg

def _tac(code: str):
    input_stream = InputStream(code)
    lx = CompiscriptLexer(input_stream)
    ts = CommonTokenStream(lx)
    ps = CompiscriptParser(ts)
    tree = ps.program()
    sem = AstAndSemantic()
    ParseTreeWalker().walk(sem, tree)
    assert sem.errors == [], f"Semánticos: {sem.errors}"
    gen = TacGenerator(sem.table)
    gen.visit(tree)
    return gen.get_code()

def test_cfg_if_simple():
    code = """
    let x: integer = 0;
    if (x < 10) { x = x + 1; }
    """
    tac = _tac(code)
    cfg = build_cfg(tac)
    # Debe haber al menos 2 bloques (condición y then)
    assert len(cfg.blocks) >= 2
    # Debe existir algún if-goto / goto en el último TAC del bloque condicional
    cond_block = cfg.blocks[0]
    last = tac[cond_block.end]
    assert last.op in {"if-goto", "goto"} or any(b.labels for b in cfg.blocks)
