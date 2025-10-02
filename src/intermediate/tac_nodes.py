"""Intermediate representation"""

from dataclasses import dataclass, field, fields, is_dataclass
from typing import List, Optional, Union, Any, Iterable, Literal

@dataclass
class TACOP:
    op : Literal[
        # Assignment
        "=",  
        
        # Relational
        "==", "!=", "<", ">", "<=", ">=",
        
        # Unary
        "uminus", "not",
        
        # Logic Gates
        "||", "&&",
        
        # Mult
        "*", "/", "%", 
        
        # add
        "+", "-",
        
        # Flow
        "goto", "if-goto", "label", # Flow
        
        # Functions
        "call", "return" ,
        
        # Memory
        "load", "store", "move",
        
        ## Special tags ##
        "LOAD_IDX",
        "STORE_IDX",

        "LOAD_PROP",
        "STORE_PROP"
        
        # DEFAULT
        "nop"
    ] = "nop"
    arg1 : Optional[str] = None
    arg2 : Optional[str] = None
    result :Optional[str] = None 


    ## Esta funcion es solo para imprimir el tac bonito. 
    ## No cambia como esta guardado ni nada, solo es para poder escribirlo/leerlo de manera bonita
    def __str__(self):
        parts = []
        op = self.op
        
        if op=="=":
            parts.append(str(self.result))
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