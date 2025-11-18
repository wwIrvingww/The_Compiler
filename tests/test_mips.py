import sys
import os
import re

sys.path.append(os.path.abspath("src"))

from intermediate.tac_nodes import TACOP
from symbol_table.runtime_layout import FrameManager
from code_generator.mips_generator import MIPSCodeGenerator


def normalize_lines(s: str):
    return [line.rstrip() for line in s.splitlines() if line.strip()]


# ============================
#  Helpers
# ============================

def make_generator(tac):
    fm = FrameManager()
    gen = MIPSCodeGenerator(tac, fm)
    asm = gen.generate()
    return normalize_lines(asm)


# ======================================
#  1) Estructura general del programa
# ======================================

def test_program_has_text_data_and_main_wrapper():
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="=", arg1="3", result="a"),
        TACOP(op="return", arg1="a"),
    ]

    lines = make_generator(tac)

    # Siempre debe existir la sección de texto y el wrapper main
    assert any(".text" in ln for ln in lines)
    assert any(".globl main" in ln for ln in lines)
    assert any(re.match(r"^\s*main:$", ln) for ln in lines)

    # La sección .data NO es obligatoria si no hay strings

# ======================================
#  2) Operaciones aritméticas / lógicas
# ======================================

def test_simple_add_function_generates_mips():
    # fn main(): return 3 + 4;
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="=", arg1="3", result="a"),
        TACOP(op="=", arg1="4", result="b"),
        TACOP(op="+", arg1="a", arg2="b", result="t0"),
        TACOP(op="return", arg1="t0"),
    ]

    lines = make_generator(tac)

    # Debe tener secciones básicas
    assert any(".text" in ln for ln in lines)
    assert any(re.match(r"\s*func_main:", ln) for ln in lines)

    # Constantes cargadas
    assert any("li" in ln and "3" in ln for ln in lines)
    assert any("li" in ln and "4" in ln for ln in lines)

    # Operación de suma
    assert any("add" in ln for ln in lines)

    # Retorno de la función
    assert any("move $v0" in ln for ln in lines)
    assert any("jr $ra" in ln for ln in lines)


def test_relop_less_than_uses_slt():
    # fn main(): return a < b;
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="=", arg1="3", result="a"),
        TACOP(op="=", arg1="5", result="b"),
        TACOP(op="<", arg1="a", arg2="b", result="t0"),
        TACOP(op="return", arg1="t0"),
    ]

    lines = make_generator(tac)

    # Debe usar slt para comparación
    assert any("slt" in ln for ln in lines)


def test_unary_not_generates_todo_comment_but_does_not_crash():
    # fn main(): return !a;
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="=", arg1="1", result="a"),
        TACOP(op="not", arg1="a", result="t0"),
        TACOP(op="return", arg1="t0"),
    ]

    lines = make_generator(tac)

    # Se genera código para la función principal
    assert any("func_main" in ln for ln in lines)

    # De momento, 'not' se marca como no soportado
    assert any("unsupported TAC op not" in ln for ln in lines)

# ======================================
#  3) Control de flujo (if-goto / goto / label)
# ======================================

def test_if_goto_generates_branch_and_label():
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="=", arg1="1", result="a"),
        TACOP(op="if-goto", arg1="a", arg2="L1"),
        TACOP(op="=", arg1="2", result="b"),
        TACOP(op="label", result="L1"),
        TACOP(op="return", arg1="a"),
    ]

    lines = make_generator(tac)

    # Debe haber etiqueta L1 y un salto condicional hacia L1
    assert any(re.match(r"\s*L1:", ln) for ln in lines)
    assert any("bne" in ln and "L1" in ln for ln in lines)


def test_goto_generates_unconditional_jump():
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="=", arg1="1", result="a"),
        TACOP(op="goto", arg1="LEND"),
        TACOP(op="=", arg1="2", result="b"),  # código que debería saltarse
        TACOP(op="label", result="LEND"),
        TACOP(op="return", arg1="a"),
    ]

    lines = make_generator(tac)

    assert any(re.match(r"\s*LEND:", ln) for ln in lines)
    assert any(re.match(r"\s*j\s+LEND", ln) for ln in lines)


# ======================================
#  4) Prints (enteros y cadenas)
# ======================================

def test_print_int_generates_syscall_1():
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="=", arg1="42", result="a"),
        TACOP(op="print", arg1="a"),
        TACOP(op="return", arg1="a"),
    ]

    lines = make_generator(tac)

    # syscall de print int
    assert any("li $v0, 1" in ln for ln in lines)
    assert any("syscall" in ln for ln in lines)


def test_print_string_uses_data_label_and_syscall_4():
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        # temp t0 = "hola"
        TACOP(op="=", arg1='"hola"', result="t0"),
        TACOP(op="print_s", arg1="t0"),
        TACOP(op="return", arg1="t0"),
    ]

    lines = make_generator(tac)

    # Debe existir alguna etiqueta strX en .data
    data_labels = [ln for ln in lines if ln.strip().startswith("str")]
    assert data_labels, "No se generaron labels de string en .data"

    # Y debe usarse syscall 4 para imprimir
    assert any("li $v0, 4" in ln for ln in lines)
    assert any("syscall" in ln for ln in lines)


# ======================================
#  5) Funciones, parámetros y retornos
# ======================================

def test_function_call_with_one_param_and_return():
    #   function foo(x: int): int { return x; }
    #   function main(): int { let a = 7; foo(a); }
    tac = [
        TACOP(op="fn_decl", result="func_foo"),
        TACOP(op="load_param", result="x", arg1="0"),
        TACOP(op="return", arg1="x"),

        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="=", arg1="7", result="a"),
        TACOP(op="push_param", result="a"),
        TACOP(op="call", arg1="func_foo", result="ret0"),
        TACOP(op="return", arg1="ret0"),
    ]

    lines = make_generator(tac)

    # Llamada a foo
    assert any("jal func_foo" in ln for ln in lines)

    # Uso de $a0 para pasar el primer parámetro
    assert any("$a0" in ln for ln in lines)

    # Movimiento del retorno desde $v0
    assert any("move" in ln and "$v0" in ln for ln in lines)


def test_prologue_and_epilogue_are_generated_per_function():
    tac = [
        TACOP(op="fn_decl", result="func_get_squared"),
        TACOP(op="load_param", result="n", arg1="0"),
        TACOP(op="*", arg1="n", arg2="n", result="t0"),
        TACOP(op="return", arg1="t0"),

        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="=", arg1="5", result="a"),
        TACOP(op="push_param", result="a"),
        TACOP(op="call", arg1="func_get_squared", result="r0"),
        TACOP(op="return", arg1="r0"),
    ]

    lines = make_generator(tac)

    # Para cada función debe haber prólogo (addiu $sp, -X; sw $ra; sw $fp; move $fp, $sp)
    func_labels = [i for i, ln in enumerate(lines) if ln.strip().startswith("func_")]
    assert func_labels, "No se encontraron funciones en el .asm"

    # Buscamos patrones típicos de prólogo y epílogo en general
    assert any("sw $ra" in ln for ln in lines)
    assert any("sw $fp" in ln for ln in lines)
    assert any("move $fp, $sp" in ln for ln in lines)

    # Epílogo: restaura $fp, $ra, ajusta $sp y hace jr $ra
    assert any("lw $fp" in ln for ln in lines)
    assert any("lw $ra" in ln for ln in lines)
    assert any("jr $ra" in ln for ln in lines)


# ======================================
#  6) Arrays y memoria dinámica
# ======================================

def test_create_array_uses_sbrk_and_returns_pointer():
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        TACOP(op="CREATE_ARRAY", result="arr"),
        TACOP(op="return", arg1="arr"),
    ]

    lines = make_generator(tac)

    # syscall 9 (sbrk) para pedir memoria
    assert any("li $v0, 9" in ln for ln in lines)
    assert any("syscall" in ln for ln in lines)

    # El puntero se mueve desde $v0 a algún registro
    assert any("move" in ln and "$v0" in ln for ln in lines)


def test_array_load_and_store_generate_lw_and_sw():
    tac = [
        TACOP(op="fn_decl", result="func_main"),
        # arr ya es una dirección válida, simulamos load/store directo
        TACOP(op="CREATE_ARRAY", result="arr"),
        TACOP(op="=", arg1="10", result="value"),
        # store value -> [arr]
        TACOP(op="store", result="arr", arg1="value"),
        # load t0 <- [arr]
        TACOP(op="load", arg1="arr", result="t0"),
        TACOP(op="return", arg1="t0"),
    ]

    lines = make_generator(tac)

    assert any("sw " in ln for ln in lines), "No se generó store (sw) para el array"
    assert any("lw " in ln for ln in lines), "No se generó load (lw) para el array"
