from dataclasses import dataclass, field, fields, is_dataclass
from typing import List, Optional, Union, Any, Iterable

Type = str
INT: Type = "integer"
BOOL: Type = "boolean"
STR: Type = "string"
NULL: Type = "null"
ERROR: Type = "error"

def type_list(inner_type: str) -> str:
    """
    Return the string representation of an array type.
    Can be nested.
    """
    return f"{inner_type}[]"

def is_list(type: str) -> bool:
    """
    Return if actual value type is a list
    """
    return type[len(type)-1] == ']' and type[len(type)-2] == '['
@dataclass
class ASTNode:
    ty: Type = ERROR

@dataclass
class Program(ASTNode):
    body: List['ASTNode'] = field(default_factory=list)

@dataclass
class Block(ASTNode):
    statements: List['ASTNode'] = field(default_factory=list)

@dataclass
class VarDecl(ASTNode):
    name: str = ""
    is_const: bool = False
    declared_type: Optional[Type] = None
    init: Optional['ASTNode'] = None

@dataclass
class Assign(ASTNode):
    name: str = ""
    value: 'ASTNode' = None  # type: ignore

@dataclass
class Identifier(ASTNode):
    name: str = ""

@dataclass
class Literal(ASTNode):
    value: Union[int, bool, str, None] = None
    
@dataclass
class ArrayLiteral(ASTNode):
    ty: Type = ERROR
    elements: List['ASTNode'] = field(default_factory=list)

@dataclass
class UnaryOp(ASTNode):
    op: str = ""
    expr: 'ASTNode' = None  # type: ignore

@dataclass
class BinaryOp(ASTNode):
    op: str = ""
    left: 'ASTNode' = None  # type: ignore
    right: 'ASTNode' = None  # type: ignore

@dataclass
class PrintStmt(ASTNode):
    expr: 'ASTNode' = None  # type: ignore

@dataclass
class IfStmt(ASTNode):
    cond: 'ASTNode' = None  # type: ignore
    then_block: Block = None  # type: ignore
    else_block: Optional[Block] = None

@dataclass
class WhileStmt(ASTNode):
    cond: 'ASTNode' = None  # type: ignore
    body: Block = None  # type: ignore

@dataclass
class ReturnStmt(ASTNode):
    expr: Optional['ASTNode'] = None

def _iter_children(n: Any) -> Iterable[ASTNode]:
    if not is_dataclass(n): return
    for f in fields(n):
        v = getattr(n, f.name)
        if isinstance(v, ASTNode):
            yield f.name, v
        elif isinstance(v, list):
            for i, c in enumerate(v):
                if isinstance(c, ASTNode):
                    yield f"{f.name}[{i}]", c

def _label(n: ASTNode) -> str:
    # Etiquetas girlie pop por tipo
    if isinstance(n, Program):     return "Program"
    if isinstance(n, Block):       return "Block"
    if isinstance(n, VarDecl):     return f"VarDecl name={n.name} const={n.is_const} declared={n.declared_type} ty={n.ty}"
    if isinstance(n, Assign):      return f"Assign {n.name} ty={n.ty}"
    if isinstance(n, BinaryOp):    return f"BinaryOp '{n.op}' ty={n.ty}"
    if isinstance(n, UnaryOp):     return f"UnaryOp '{n.op}' ty={n.ty}"
    if isinstance(n, Identifier):  return f"Identifier {n.name} ty={n.ty}"
    if isinstance(n, Literal):     return f"Literal {repr(n.value)} ty={n.ty}"
    if isinstance(n, ArrayLiteral):     
        return f"ArrayLiteral elements={
            [el.ty for el in n.elements]
        }"
    if isinstance(n, PrintStmt):   return "PrintStmt"
    if isinstance(n, IfStmt):      return "IfStmt"
    if isinstance(n, WhileStmt):   return "WhileStmt"
    if isinstance(n, ReturnStmt):  return "ReturnStmt"
    return type(n).__name__

def render_ascii(root: ASTNode) -> str:
    lines = []
    def dfs(node: ASTNode, prefix: str="", is_last: bool=True):
        connector = "└─ " if is_last else "├─ "
        lines.append(prefix + connector + _label(node))
        children = list(_iter_children(node))
        for idx, (_, ch) in enumerate(children):
            last = (idx == len(children) - 1)
            dfs(ch, prefix + ("   " if is_last else "│  "), last)
    dfs(root)
    return "\n".join(lines)