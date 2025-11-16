import sys, os
sys.path.append(os.path.abspath("src"))

from code_generator.register_allocator import RegisterAllocator


def test_basic_allocation():
    alloc = RegisterAllocator()

    live = set()

    # Solicito registro para variable a
    reg_a, code_a = alloc.get_register_for("a", live, for_read=False, for_write=True)
    assert reg_a.startswith("$")
    assert "a" in alloc.address
    alloc.mark_written(reg_a)

    # Ahora solicito b
    reg_b, code_b = alloc.get_register_for("b", live, for_read=False, for_write=True)
    assert reg_b != reg_a
    assert "b" in alloc.address
    alloc.mark_written(reg_b)

    # Ahora solicito a de nuevo, debe reutilizar reg_a
    reg_a2, code_a2 = alloc.get_register_for("a", live, for_read=True, for_write=False)
    assert reg_a2 == reg_a  # mismo registro
    assert code_a2 == []    # no necesita cargar ni spill

def test_spill_when_full():
    # Limito a solo dos registros para forzar spill
    alloc = RegisterAllocator(available_registers=["$t0", "$t1"])
    alloc.bind_variable_to_memory("a", -4)
    alloc.bind_variable_to_memory("b", -8)
    alloc.bind_variable_to_memory("c", -12)

    live = {"a", "b"}  # c NO está viva

    # Asigna a y b → usa ambos registros
    reg_a, _ = alloc.get_register_for("a", live, for_read=False, for_write=True)
    alloc.mark_written(reg_a)
    reg_b, _ = alloc.get_register_for("b", live, for_read=False, for_write=True)
    alloc.mark_written(reg_b)

    # Registrar c → debe hacer spill de un registro que NO esté vivo (candidato ideal)
    reg_c, code_c = alloc.get_register_for("c", live, for_read=False, for_write=True)

    # Debe existir alguna instrucción "sw" en code_c indicando SPILL
    spilled = any("sw" in line for line in code_c)
    assert spilled

    alloc.mark_written(reg_c)
