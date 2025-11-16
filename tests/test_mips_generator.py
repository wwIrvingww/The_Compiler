import sys, os, re
sys.path.append(os.path.abspath("src"))

from intermediate.tac_nodes import TACOP
from symbol_table.runtime_layout import FrameManager
from code_generator.mips_generator import MIPSCodeGenerator



def normalize_lines(s: str):
    return [line.rstrip() for line in s.splitlines() if line.strip()]


def test_simple_add_function_generates_mips():
    # fn main(): return 3 + 4;
    tac = [
        TACOP(op="fn_decl", result="main"),
        TACOP(op="=", arg1="3", result="a"),
        TACOP(op="=", arg1="4", result="b"),
        TACOP(op="+", arg1="a", arg2="b", result="t0"),
        TACOP(op="return", arg1="t0"),
    ]

    fm = FrameManager()
    gen = MIPSCodeGenerator(tac, fm)
    asm = gen.generate()
    lines = normalize_lines(asm)

    # Debe tener secciones básicas
    assert any(".text" in ln for ln in lines)
    assert any(re.match(r"^\s*main:$", ln) for ln in lines)

    # Constantes cargadas
    assert any("li" in ln and "3" in ln for ln in lines)
    assert any("li" in ln and "4" in ln for ln in lines)

    # Operación de suma
    assert any("add" in ln for ln in lines)

    # Retorno de la función
    assert any("move $v0" in ln for ln in lines)
    assert any("jr $ra" in ln for ln in lines)


def test_if_goto_generates_branch_and_label():
    tac = [
        TACOP(op="fn_decl", result="main"),
        TACOP(op="=", arg1="1", result="a"),
        TACOP(op="if-goto", arg1="a", arg2="L1"),
        TACOP(op="=", arg1="2", result="b"),
        TACOP(op="label", result="L1"),
        TACOP(op="return", arg1="a"),
    ]

    fm = FrameManager()
    gen = MIPSCodeGenerator(tac, fm)
    asm = gen.generate()
    lines = normalize_lines(asm)

    # Debe haber etiqueta L1 y un salto condicional hacia L1
    assert any(re.match(r"^L1:$", ln) for ln in lines)
    assert any("bne" in ln and "L1" in ln for ln in lines)
