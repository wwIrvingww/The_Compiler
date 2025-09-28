# tests/test_temps.py
import pytest
from src.intermediate.temps import TempAllocator

def test_allocate_free_reuse_lifo():
    ta = TempAllocator(prefix="t", start=0)
    ta.reset()
    t0 = ta.new_temp()   # t0
    t1 = ta.new_temp()   # t1
    # free t1, should be reused next (LIFO behaviour)
    ta.free_temp(t1)
    t2 = ta.new_temp()
    assert t2 == t1

def test_typed_temp_and_mapping():
    ta = TempAllocator()
    ta.reset()
    tt = ta.new_typed_temp("f32")
    mapping = ta.temp_type_map()
    assert tt in mapping
    assert mapping[tt] == "f32"

def test_temporary_context_manager_auto_free():
    ta = TempAllocator()
    ta.reset()
    with ta.temporary() as tmp:
        assert tmp in ta.allocated()
    # after context exit tmp should not be allocated
    assert tmp not in ta.allocated()

def test_reserve_and_duplicate_reserve_raises():
    ta = TempAllocator()
    ta.reset()
    ta.reserve("t42", type_name="i32")
    assert "t42" in ta.temp_type_map()
    with pytest.raises(KeyError):
        ta.reserve("t42")  # reservar dos veces falla

def test_free_unallocated_ignored_by_default():
    ta = TempAllocator(raise_on_invalid_free=False)
    ta.reset()
    # should not raise
    ta.free_temp("t999999")
    # but if configured to raise, it should error
    tb = TempAllocator(raise_on_invalid_free=True)
    tb.reset()
    with pytest.raises(ValueError):
        tb.free_temp("t999999")
