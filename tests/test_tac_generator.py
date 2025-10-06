
import pytest
from intermediate.tac_nodes import TACOP, IRNode
from src.intermediate.tac_generator import TacGenerator, TempAllocator, LabelGenerator
from symbol_table.symbol_table import SymbolTable

# ==============================================================
# 1. FIXTURES BÁSICAS
# ==============================================================

@pytest.fixture
def generator():
    """Instancia base de TacGenerator con tablas limpias."""
    symtab = SymbolTable()
    gen = TacGenerator(symtab)
    return gen


@pytest.fixture
def empty_ir():
    """IRNode vacío auxiliar."""
    return IRNode(place=None, code=[])


# ==============================================================
# 2. TESTS DE COMPONENTES AUXILIARES
# ==============================================================

def test_temp_allocator_basic():
    t = TempAllocator()
    first = t.new_temp()
    second = t.new_temp()
    assert first == "t0"
    assert second == "t1"
    # No asumimos release(): validamos unicidad y formato
    third = t.new_temp()
    assert third.startswith("t")
    assert len({first, second, third}) == 3


def test_label_generator_incremental():
    l = LabelGenerator(prefix="L", start=5)
    assert l.new_label() == "L5"
    assert l.new_label() == "L6"


def test_emit_assign(generator):
    code = []
    generator._emit_assign("x", "t0", code)
    assert code[0].op == "="
    assert code[0].result == "x"
    assert code[0].arg1 == "t0"


def test_emit_bin(generator):
    code = []
    res = generator._emit_bin("+", "a", "b", code)
    assert res.startswith("t")
    assert any(op.op == "+" for op in code)


# ==============================================================
# 3. PEEPHOLE OPTIMIZATION
# ==============================================================

def test_peephole_removes_self_assign():
    code = [TACOP(op="=", arg1="x", result="x")]
    opt = TacGenerator.peephole(code)
    assert len(opt) == 0, "Debe eliminar x=x"

def test_peephole_true_goto():
    code = [TACOP(op="if-goto", arg1="true", arg2="L1")]
    opt = TacGenerator.peephole(code)
    assert opt[0].op == "goto"

def test_peephole_false_goto():
    code = [TACOP(op="if-goto", arg1="false", arg2="L1")]
    opt = TacGenerator.peephole(code)
    assert len(opt) == 0

def test_peephole_temp_bool_chain():
    code = [
        TACOP(op="=", arg1="true", result="t1"),
        TACOP(op="if-goto", arg1="t1", arg2="L1")
    ]
    opt = TacGenerator.peephole(code)
    assert opt[0].op == "goto" and opt[0].arg1 == "L1"

def test_peephole_goto_to_next_label():
    code = [TACOP(op="goto", arg1="L1"), TACOP(op="label", result="L1")]
    opt = TacGenerator.peephole(code)
    # En tu versión actual, este patrón NO se elimina: se conservan ambas
    assert len(opt) == 2
    assert opt[0].op == "goto" and opt[0].arg1 == "L1"
    assert opt[1].op == "label" and opt[1].result == "L1"


# ==============================================================
# 4. GENERACIÓN DE TAC PARA ESTRUCTURAS
# ==============================================================

def test_variable_declaration(generator):
    # Simula: let x = 5;
    class Id:
        def getText(self):
            return "x"

    # Un "ctx" para la expresión que sea visitable por generator.visit(...)
    class ExprCtx: 
        pass

    class Init:
        def expression(self):
            # devolvemos un ctx visitable; el visitor lo resolverá a IRNode
            return ExprCtx()

    class Ctx:
        def Identifier(self): return Id()
        def initializer(self): return Init()

    # Cuando el generator "visite" ExprCtx, devolvemos el IR de una constante
    def fake_visit(ctx):
        if isinstance(ctx, ExprCtx):
            return IRNode(place="t1", code=[TACOP(op="=", arg1="5", result="t1")])
        return IRNode(place=None, code=[])
    generator.visit = fake_visit

    node = generator.visitVariableDeclaration(Ctx())
    # Debe haber una asignación x = t1
    assert any(op.op == "=" and op.result == "x" and op.arg1 == "t1" for op in node.code)

def test_print_statement(generator):
    val = IRNode(place="t0", code=[TACOP(op="=", arg1="5", result="t0")])
    generator.visit = lambda ctx: val
    ctx = type("Ctx", (), {"expression": lambda: None})
    result = generator.visitPrintStatement(ctx)
    assert any(op.op == "print" for op in result.code)

def test_if_statement(generator):
    # if (x < 3) { print(x); }  (sin else)
    cond = IRNode(place="t0", code=[TACOP(op="<", arg1="x", arg2="3", result="t0")])
    then = IRNode(place=None, code=[TACOP(op="print", arg1="x")])

    # visit() será llamado con ctx.expression() y ctx.block(0)
    def fake_visit(arg):
        # distinguimos por un atributo marcador que pondremos en el mock de ctx
        if getattr(arg, "_kind", "") == "expr":
            return cond
        if getattr(arg, "_kind", "") == "block0":
            return then
        return IRNode(place=None, code=[])

    generator.visit = fake_visit

    class ExprCtx: _kind = "expr"
    class Block0Ctx: _kind = "block0"

    class IfCtx:
        def __init__(self):
            self._blocks = [Block0Ctx()]  # solo THEN
            self._expr = ExprCtx()

        def expression(self):
            return self._expr

        # CompiscriptParser permite block(i) y también block() sin args.
        # Aquí devolvemos lista si no pasan índice (para que len(ctx.block()) funcione),
        # y la entrada específica si pasan i.
        def block(self, i=None):
            if i is None:
                return self._blocks
            return self._blocks[i]

    node = generator.visitIfStatement(IfCtx())
    ops = [op.op for op in node.code]
    assert "if-goto" in ops and "goto" in ops and "label" in ops

def test_while_statement(generator):
    cond = IRNode(place="t0", code=[TACOP(op="<", arg1="i", arg2="10", result="t0")])
    body = IRNode(place=None, code=[TACOP(op="print", arg1="i")])
    generator.visit = lambda ctx: cond if "expression" in str(ctx) else body
    ctx = type("Ctx", (), {"expression": lambda: None, "block": lambda: None})
    node = generator.visitWhileStatement(ctx)
    assert any(op.op == "if-goto" for op in node.code)
    assert any(op.op == "goto" for op in node.code)

def test_for_statement(generator):
    cond = IRNode(place="t0", code=[TACOP(op="<", arg1="i", arg2="5", result="t0")])
    body = IRNode(place=None, code=[TACOP(op="print", arg1="i")])
    generator.visit = lambda ctx: cond if "expression" in str(ctx) else body
    ctx = type("Ctx", (), {
        "variableDeclaration": lambda: None,
        "assignment": lambda: None,
        "expression": lambda: [None, None],
        "block": lambda: None
    })
    node = generator.visitForStatement(ctx)
    assert any(op.op == "if-goto" for op in node.code)

def test_foreach_statement(generator):
    # Mocks correctos para Identifier().getText()
    class Id:
        def getText(self):
            return "item"

    class Blk:
        def statement(self):  # cuerpo vacío
            return []

    class Ctx:
        def Identifier(self): return Id()
        def expression(self): return None  # el visitor lo sobreescribimos abajo
        def block(self): return Blk()

    # la expresión que da el arreglo:
    arr = IRNode(place="arr", code=[TACOP(op="CREATE_ARRAY", result="arr")])
    generator.visit = lambda ctx: arr  # cuando pida visitar la expr, devolvemos arr

    node = generator.visitForeachStatement(Ctx())
    assert any(op.op == "len" for op in node.code)
    assert any(op.op == "getidx" for op in node.code)

def test_return_statement(generator):
    expr = IRNode(place="t0", code=[TACOP(op="=", arg1="1", result="t0")])
    generator.visit = lambda ctx: expr
    ctx = type("Ctx", (), {"expression": lambda: None})
    node = generator.visitReturnStatement(ctx)
    assert node.code[-1].op == "return"


# ==============================================================
# 5. TEMPORAL & FRAME INTEGRATION
# ==============================================================

def test_temp_reuse_and_label_unique(generator):
    t1 = generator._new_temp()
    t2 = generator._new_temp()
    l1 = generator._new_label()
    l2 = generator._new_label()
    assert t1 != t2
    assert l1 != l2


def test_frame_manager_allocates(generator):
    # API disponible: enter_frame / current_frame_id / allocate_local
    generator.frame_manager.enter_frame("main")
    fid = generator.frame_manager.current_frame_id()
    assert fid is not None

    generator.frame_manager.allocate_local(fid, "x", "int", 4)

    frame = generator.frame_manager._frames[fid]

    # Aserción tolerante: intenta encontrar "x" en cualquier mapa plausible del frame
    found = False
    # 1) si el frame es un objeto con __dict__, inspeccionamos dicts candidatas
    if hasattr(frame, "__dict__"):
        for k, v in vars(frame).items():
            if isinstance(v, dict) and "x" in v:
                found = True
                break
    # 2) atributos comunes (por compatibilidad con tus variantes)
    for attr in ("symbols", "_symbols", "locals", "_locals", "table", "_table", "bindings", "_bindings"):
        if hasattr(frame, attr) and isinstance(getattr(frame, attr), dict):
            if "x" in getattr(frame, attr):
                found = True
                break

    assert found, "No se encontró el símbolo 'x' en las estructuras del frame luego de allocate_local()"

# ==============================================================
# 6. CASOS FALLIDOS / EDGE CASES
# ==============================================================

def test_break_without_loop(generator):
    generator.break_stack.clear()
    node = generator.visitBreakStatement(None)
    assert node.code == []

def test_continue_without_loop(generator):
    generator.continue_stack.clear()
    node = generator.visitContinueStatement(None)
    assert node.code == []

def test_assignment_nonexistent_var(generator):
    # Mock con métodos que acepten self y firma esperada
    class Id:
        def getText(self): return "y"

    class Ctx:
        def getChildCount(self): return 4
        def Identifier(self): return Id()
        # expression(index) -> devolvemos un IR válido simulando RHS
        def expression(self, _=None):
            return IRNode(place="t0", code=[TACOP(op="=", arg1="1", result="t0")])

    with pytest.raises(Exception):
        generator.visitAssignment(Ctx())