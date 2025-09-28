# tests/test_labels.py
import re
import pytest
from src.intermediate.labels import LabelGenerator, get_default_label_generator

def test_new_label_sequence_and_uniqueness():
    lg = LabelGenerator(prefix="L", start=0)
    a = lg.new_label()
    b = lg.new_label()
    assert a == "L0"
    assert b == "L1"
    assert a != b
    assert re.match(r"^L\d+$", a)
    assert re.match(r"^L\d+$", b)

def test_reserve_advances_next_id():
    lg = LabelGenerator()
    lg.reset()
    lg.reserve("L42")
    allocated = lg.allocated()
    assert "L42" in allocated
    assert lg.next_id_hint() >= 43

def test_reserve_duplicate_raises():
    lg = LabelGenerator()
    lg.reset()
    lg.reserve("L0")
    with pytest.raises(KeyError):
        lg.reserve("L0")

def test_reset_clears_state():
    lg = LabelGenerator()
    lg.new_label()
    lg.new_label()
    lg.reset()
    assert lg.next_id_hint() == 0
    assert lg.allocated() == []
