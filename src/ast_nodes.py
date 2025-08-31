from dataclasses import dataclass, field, fields, is_dataclass
from typing import List, Optional, Union, Any, Iterable


@dataclass(frozen=True)
class Type:
    name: Optional[str] = None
    element_type: Optional['Type'] = None
    def __str__(self):
        if self.element_type:
            return str(self.element_type)+"[]"
        return self.name or "undefined"



INT: Type = Type("integer")
BOOL: Type = Type("boolean")
STR: Type = Type("string")
NULL: Type = Type("null")
ERROR: Type = Type("error")

def type_list(inner_type: Type) -> Type:
    """
    Return the string representation of an array type.
    Can be nested.
    """
    arr = Type(element_type=inner_type)
    return arr

def is_list(var: Type) -> bool:
    """
    Return if actual value type is a list
    """
    return var.element_type is not None

@dataclass
class ASTNode:
    ty: Type = field(default_factory=lambda: ERROR)

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

@dataclass
class FuncDecl(ASTNode):
    name: str = ""
    # [(paramName, Type), ...]
    params: List[tuple] = field(default_factory=list)
    ret: Optional[Type] = None
    body: Block = None  # type: ignore

@dataclass
class Call(ASTNode):
    callee: Identifier = None  # type: ignore
    args: List[ASTNode] = field(default_factory=list)

@dataclass
class ClassDecl(ASTNode):
    name: str = ""
    members: List[ASTNode] = field(default_factory=list)  # FuncDecl, VarDecl, etc.

@dataclass
class MethodDecl(ASTNode):
    name: str = ""
    params: List[tuple] = field(default_factory=list)
    ret: Optional[Type] = None
    body: Block = None  # type: ignore

@dataclass
class PropertyAccess(ASTNode):
    obj: ASTNode = None  # type: ignore
    prop: str = ""

@dataclass
class ThisExpr(ASTNode):
    pass

@dataclass
class NewExpr(ASTNode):
    class_name: str = ""
    args: List[ASTNode] = field(default_factory=list)

def _label(n: ASTNode) -> str:
    # Etiquetas girlie pop por tipo
    if isinstance(n, Program):     return "Program"
    if isinstance(n, Block):       return "Block"
    if isinstance(n, VarDecl): declared = f"{n.declared_type}" if n.declared_type else "—"; inferred = f"{n.ty}"; return f"VarDecl name={n.name} const={n.is_const} declared={declared} ty={inferred}" #cuando declared is None mejor rotular inferred=integer en la etiqueta para más slay
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
    if isinstance(n, FuncDecl):
        ps = ", ".join(f"{p}:{t}" for p, t in n.params)
        return f"FuncDecl {n.name}({ps}) : {n.ret}"
    if isinstance(n, Call):        return f"Call {n.callee.name}() ty={n.ty}"
    if isinstance(n, ClassDecl):   return f"ClassDecl {n.name}"
    if isinstance(n, MethodDecl):
        ps = ", ".join(f"{p}:{t}" for p, t in n.params)
        return f"MethodDecl {n.name}({ps}) : {n.ret}"
    if isinstance(n, PropertyAccess): return f"PropertyAccess .{n.prop} ty={n.ty}"
    if isinstance(n, ThisExpr):    return f"ThisExpr ty={n.ty}"
    if isinstance(n, NewExpr):     return f"NewExpr {n.class_name}() ty={n.ty}"
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

def create_tree_image(root: ASTNode, out_basename: str = "ast", fmt: str = "png") -> str:
    """
    Genera ast.png/svg usando graphviz si corrió el docker AS HE|SHE SHOULD, si no y solo nos odia 
    y no le importó nuestro esfuerzo en hacer su vida más fácil, genera un stinky ast.dot.
    Devuelve la ruta del archivo generado (imagen si hubo, .dot en fallback).
    """
    def safe_label(n: ASTNode) -> str:
        # Reutiliza tu _label pero escapando comillas
        return _label(n).replace('"', '\\"')

    try:
        # Camino 1: usar el paquete graphviz + binario 'dot'
        from graphviz import Digraph
        g = Digraph("AST", format=fmt)
        g.attr("graph", rankdir="TB")           # vertical (top->bottom)
        g.attr("node", shape="box", fontname="Consolas")

        counter = 0
        def new_id():
            nonlocal counter
            counter += 1
            return f"n{counter}"

        def walk(n: ASTNode) -> str:
            me = new_id()
            g.node(me, safe_label(n))
            for child_name, ch in _iter_children(n):
                child = walk(ch)
                g.edge(me, child, label=child_name)
            return me

        walk(root)
        # Nota: render lanza si no está el binario 'dot' instalado
        out_path = g.render(filename=out_basename, cleanup=True)  # crea p.ej. ast.png
        return out_path

    except Exception as e:
        # Stinky camino 2 (fallback): escribir DOT puro, usando id(n) como clave (¡no requiere hash!)
        dot_lines = [
            'digraph AST {',
            '  rankdir=TB;',
            '  node [shape=box fontname="Consolas"];'
        ]
        ids = {}
        counter = 0

        def get_id(n: ASTNode) -> str:
            nonlocal counter
            key = id(n)                 # <- clave basada en identidad, siempre hashable
            if key in ids:
                return ids[key]
            counter += 1
            nid = f"n{counter}"
            ids[key] = nid
            return nid

        def walk_text(n: ASTNode):
            me = get_id(n)
            dot_lines.append(f'  {me} [label="{safe_label(n)}"];')
            for _, ch in _iter_children(n):
                ce = get_id(ch)
                dot_lines.append(f"  {me} -> {ce};")
                walk_text(ch)

        walk_text(root)
        dot_lines.append("}")

        dot_path = out_basename + ".dot"
        with open(dot_path, "w", encoding="utf-8") as f:
            f.write("\n".join(dot_lines))
        return dot_path
