"""Intermediate representation"""

from dataclasses import dataclass, field, fields, is_dataclass
from typing import List, Optional, Union, Any, Iterable, Literal

@dataclass
class TACOP:
    op : Literal[
        "=",  # Assignment
        "==", "!=", "<", ">", "<=", ">=", # Relational
        "uminus", "not", # Unary
        "||", "&&", # Logic
        "*", "/", "%", # Mult
        "+", "-",
        "goto", "if-goto", "label", # Flow
        "call", "return" ,# Functions
        "load", "store", "move", # Memory
        "nop" # DEFAULT
    ] = "nop"
    arg1 : Optional[str] = None
    arg2 : Optional[str] = None
    result :Optional[str] = None 

    def __str__(self):
        parts = []
        op = self.op
        if op=="=":
            if self.result is not None:
                parts.append(f"{self.result}")
            parts.append(op)
            if self.arg1 is not None:
                parts.append(str(self.arg1))
            if self.arg2 is not None:
                parts.append(", "+str(self.arg2))
        elif op in ["!", "uminus"]:
            parts.append(f"{self.result} =")
            parts.append(op)
            parts.append(str(self.arg1))
        elif op in ["label", "goto"]:
            parts.append(op)
            parts.append(str(self.result))
        else:
            if self.result is not None:
                parts.append(f"{self.result} =")
            if self.arg1 is not None:
                parts.append(str(self.arg1))
            parts.append(op)
            if self.arg2 is not None:
                parts.append(""+str(self.arg2))
        return " ".join(parts)
        
@dataclass
class IRNode:
    place: Any = None
    value: Union[int, bool, str, None] = None
    code : List['TACOP'] = None
    
    
@dataclass
class IRAssign(IRNode):
    name: str = None
    
@dataclass
class IRBlock(IRNode):
    start_label : Any = None
    end_label : Any = None