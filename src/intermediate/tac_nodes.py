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
        "CREATE_ARRAY,"
        "PUSH_ARRAY",
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
                
        elif op in ["not", "uminus"]: # mejor usar 'not' (no '!')
            parts.append(f"{self.result} =")
            parts.append(op)
            parts.append(str(self.arg1))
        elif op in ["STORE_IDX"]:
            parts.append(f"{self.result}")
            parts.append("STORE_IDX")
            parts.append(str(self.arg1)+",")
            parts.append(str(self.arg2))
        elif op in ["LOAD_IDX"]:
            parts.append(f"{self.result}")
            parts.append("LOAD_IDX")
            parts.append(str(self.arg1)+",")
            parts.append(str(self.arg2))    
        
        elif op == "label":
            # imprime "label Lk"
            parts.append("label")
            parts.append(str(self.result or self.arg1))
        elif op == "goto":
            # imprime "goto Lk"
            parts.append("goto")
            parts.append(str(self.arg1 or self.result))
        elif op == "if-goto":
            # imprime "if tX goto Lk"
            parts.append(f"if {self.arg1} goto {self.arg2}")
        elif op == "return":
            parts.append("return" + (f" {self.arg1}" if self.arg1 is not None else ""))
        else:
            # binarios: "tZ = a OP b"
            parts.append(f"{self.result} =")
            if self.arg1 is not None:
                parts.append(str(self.arg1))
            parts.append(op)
            if self.arg2 is not None:
                parts.append(""+str(self.arg2))
        return " ".join(parts)
    
    def __post_init__(self):
        def norm(x):
            if isinstance(x, tuple) and x:
                x = x[0]
            if x is None:
                return None
            return str(x)
        self.arg1   = norm(self.arg1)
        self.arg2   = norm(self.arg2)
        self.result = norm(self.result)
        
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
    
    
@dataclass
class IRArray(IRNode):
    base: Any = None
    index : Any = None