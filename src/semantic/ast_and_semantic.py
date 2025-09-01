from antlr4 import ParseTreeWalker
from parser.CompiscriptParser import CompiscriptParser
from parser.CompiscriptListener import CompiscriptListener
from typing import Optional, List, Dict, Any
from symbol_table.symbol_table import Symbol, SymbolTable
from ast_nodes import *

def unify_bin(op: str, lt: Type, rt: Type) -> Type:
    if op in {"+", "-", "*", "/", "%"}:
        if lt == INT and rt == INT:
            return INT
        if op == "+" and lt == STR and rt == STR:
            return STR
        return ERROR
    if op in {"==", "!=", "<", "<=", ">", ">="}:
        if lt == rt and lt in {INT, STR, BOOL}:
            return BOOL
        return ERROR
    if op in {"&&"}:
        return BOOL if lt == BOOL and rt == BOOL else ERROR
    if op in {"||"}:
        return BOOL if lt == BOOL and rt == BOOL else ERROR
    return ERROR

def compatible(expected: Optional['Type'], actual: Type) -> bool:
    if expected is None:
        return True
    if is_list(expected) and actual == type_list(NULL):
        return True
    return expected == actual


def returnLiteral(lex):
    node = Literal(value=None, ty=ERROR)
    if len(lex) >= 2 and lex[0] == '"' and lex[-1] == '"':
        node = Literal(value=lex[1:-1], ty=STR)
    elif lex.isdigit():
        node = Literal(value=int(lex), ty=INT)
    return node
def _parse_type_text(text: Optional[str]) -> Optional[Type]:
    if not text:
        return None
    t = text.replace(":", "").strip()
    dims = 0
    while t.endswith("[]"):
        t = t[:-2]; dims += 1
    base = Type(name=t)
    while dims > 0:
        base = type_list(base); dims -= 1
    return base

def _get_type_text_from_ctx(ctx) -> Optional[str]:
    if hasattr(ctx, "typeAnnotation"):
        ta = ctx.typeAnnotation()
        if ta:
            return ta.getText()
    if hasattr(ctx, "type_"):  # por si la gramática renombró 'type' a 'type_'
        t = ctx.type_()
        if t:
            return t.getText()
    return None
    
class AstAndSemantic(CompiscriptListener):
    def __init__(self):
        self.ast: Dict[Any, ASTNode] = {}
        self.types: Dict[Any, Type] = {}
        self.errors: List[str] = []
        self.table = SymbolTable()
        self.program = Program()
        self.const_scopes: List[set] = [set()]
        self.current_class: Optional[str] = None
        self.current_method: Optional[str] = None
        self._class_frames: list = []
        self.func_ret_stack: List[Type] = [] #Agregar un stack para validar los returns
        self.inter_counter : int = 0
        self.init_foreach_identifyer_flag : bool  = False
        self.foreach_item_stack : List[str] = []

    def _error(self, ctx, msg):
        line = getattr(ctx.start, "line", 1)
        self.errors.append(
            f"[line {line}] {msg}"
        )
    def _enter_scope(self):
        self.table.enter_scope()
        self.const_scopes.append(set())

    def _exit_scope(self):
        self.table.exit_scope()
        self.const_scopes.pop()

    def enterProgram(self, ctx: CompiscriptParser.ProgramContext):
        self.program = Program()

    def exitProgram(self, ctx: CompiscriptParser.ProgramContext):
        body = [self.ast.get(s) for s in ctx.statement()]
        self.program.body = [s for s in body if s is not None]
        self.program.ty = NULL

    def enterBlock(self, ctx: CompiscriptParser.BlockContext):
        self._enter_scope()

    def exitBlock(self, ctx: CompiscriptParser.BlockContext):
        stmts = [self.ast.get(s) for s in ctx.statement()]
        node = Block(statements=[s for s in stmts if s is not None], ty=NULL)
        self.ast[ctx] = node
        self._exit_scope()

    def exitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        # Get name        
        name = ctx.Identifier().getText()
        # Save the declaration type (it can be NONE)
        declared = None
        ttxt = _get_type_text_from_ctx(ctx)
        if ttxt:
            declared = _parse_type_text(ttxt)
        init_node = None
        init_ty = NULL
        
        if ctx.initializer():
            init_node = self.ast.get(ctx.initializer())
            init_ty = self.types.get(ctx.initializer(), ERROR)
        try:
            self._define_symbol(name, declared or (init_ty if (init_ty != NULL) else None), err_ctx=ctx)
        except Exception as e:
            self.errors.append(str(e))

        if ctx.initializer() and not compatible(declared, init_ty):
            self._error(
                msg=f"Tipo incompatible en inicializacion de '{name}': esperado {declared}, obtenido {init_ty}",
                ctx=ctx
            )

        node = VarDecl(name=name, is_const=False, declared_type=declared, init=init_node, ty=declared or init_ty or NULL)
        self.ast[ctx] = node

        # Si estamos en una clase y NO en un método, registrar como atributo
        if self.current_class and not self.current_method and self._class_frames:
            frame = self._class_frames[-1]
            frame["attributes"][name] = Symbol(name, node.ty.name)
            frame["symbol"].metadata["attributes"] = frame["attributes"]
    def exitConstantDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        # Get name        
        name = ctx.Identifier().getText()
        # Save the declaration type (it can be NONE)
        declared = None
        ttxt = _get_type_text_from_ctx(ctx)
        if ttxt:
            declared = _parse_type_text(ttxt)
        init_node = None
        init_ty = NULL
        
        if ctx.expression():
            init_node = self.ast.get(ctx.expression())
            init_ty = self.types.get(ctx.expression(), ERROR)
        try:
            
            self._define_symbol(name, declared or (init_ty if (init_ty != NULL) else None), err_ctx=ctx, metadata={"const": True})
        except Exception as e:
            self.errors.append(str(e))

        if ctx.expression() and not compatible(declared, init_ty):
            self.errors.append(f"Tipo incompatible en inicializacion de '{name}': esperado {declared}, obtenido {init_ty}")

        node = VarDecl(name=name, is_const=True, declared_type=declared, init=init_node, ty=declared or init_ty or NULL)
        self.ast[ctx] = node

    def exitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        # RHS
        
        exprs = ctx.expression()
        expr_list = exprs if isinstance(exprs, list) else [exprs]
        rhs_ctx = expr_list[-1]
        val_node = self.ast.get(rhs_ctx)
        val_ty = self.types.get(rhs_ctx, ERROR)
        # Intentar obtener Identifier directamente (si la gramática lo provee)
        ids = None
        try:
            ids_candidate = ctx.Identifier()
            if ids_candidate:
                ids = ids_candidate
        except Exception:
            ids = None

        # Fallback: buscar en leftHandSide -> primaryAtom -> Identifier
        if not ids:
            try:
                if hasattr(ctx, "leftHandSide"):
                    lh = ctx.leftHandSide()
                    # leftHandSide() puede devolver lista o un solo nodo
                    lhs = lh if not isinstance(lh, list) else (lh[0] if lh else None)
                    if lhs and hasattr(lhs, "primaryAtom") and lhs.primaryAtom():
                        pa = lhs.primaryAtom()
                        if hasattr(pa, "Identifier") and pa.Identifier():
                            ids2 = pa.Identifier()
                            if ids2:
                                ids = ids2
            except Exception:
                # no bloquear validación si algo falla aquí
                ids = ids

        # Si aún no encontramos un identifier, salimos (no es asignación simple a variable)
        if not ids:
            return
        # Resolver nombre (ids puede ser token o lista)
        try:
            if isinstance(ids, list):
               
                name = ids[-1].getText() if ids else None
            else:
                name = ids.getText()
        except Exception:
            name = None

        if not name:
            return

        # Buscar en la tabla de símbolos
        sym = self.table.lookup(name)
        try: 
            if sym.metadata.get("const"):
                self._error(
                    msg=f"No se puede asignar a const \'{sym.name}\'",
                    ctx=ctx
                )
                return
        except:
            pass
        
        if sym is None:
            # intentar sacar línea del token/ctx
            self._error(
                msg=f"variable '{name}' no declarada",
                ctx=ctx
            )
            return
            # line = 1
            # try:
            #     # tokens ANTLR: ids.getSymbol().line
            #     token = None
            #     try:
            #         token = ids.getSymbol()
            #     except Exception:
                    
            #         # a veces ids es un Token (no un ctx) con .line
            #         token = getattr(ids, 'symbol', None) or getattr(ids, 'getSymbol', None)
            #     if hasattr(token, 'line'):
            #         line = token.line
            #     else:
            #         line = getattr(ctx.start, "line", 1)
            # except Exception:
        else:
            identifier_node = Identifier(
                ty = sym.type,
                name = sym.name
            )
            ass_node = Assign(
                dest = identifier_node,
                value= val_node,
                ty = sym.type  
            )
            self.ast[ctx] = ass_node
            return
        # (Opcional) construir nodo AST/typing similar a antes
        # self.ast[ctx] = Assign(name=name, value=val_node, ty=(sym.type if sym else ERROR))


    def exitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()

        declared = None
        ttxt = _get_type_text_from_ctx(ctx)
        if ttxt:
            declared = _parse_type_text(ttxt)

        init_node = None
        init_ty = NULL
        if ctx.expression():
            init_node = self.ast.get(ctx.expression())
            init_ty = self.types.get(ctx.expression(), ERROR)

        if not ctx.expression():
            self._error(
                msg=f"Constante \'{name}\' debe tener inicializador",
                ctx=ctx
            )

        try:
            sym = Symbol(name, declared or init_ty or NULL, metadata={"const": True})
            self.table.define(sym)
            # Registrar también en const_scopes
            self.const_scopes[-1].add(name)
        except Exception as e:
            self.errors.append(str(e))

        if ctx.expression() and declared and not compatible(declared, init_ty):
            self.errors.append(
                f"Tipo incompatible en inicializacion de const '{name}': esperado {declared}, obtenido {init_ty}"
            )

        node = VarDecl(
            name=name,
            is_const=True,
            declared_type=declared,
            init=init_node,
            ty=declared or init_ty or NULL
        )
        self.ast[ctx] = node

    def exitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        expr_node = self.ast.get(ctx.expression())
        self.ast[ctx] = PrintStmt(expr=expr_node, ty=NULL)

    def exitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        # localizar la condición
        cond_ctx = None
        try:
            exprs = ctx.expression()
            cond_ctx = exprs if not isinstance(exprs, list) else (exprs[0] if exprs else None)
        except Exception:
            cond_ctx = None

        if cond_ctx is None:
            return

        cond_text = cond_ctx.getText()
        cond_ty = self.types.get(cond_ctx, None)
        
        try:
            is_bool = (cond_ty == BOOL)
        except NameError:
            is_bool = False

        if not is_bool and cond_text not in ("true", "false"):
            self._error(ctx, msg=f"condicion de 'if' debe ser boolean, no \'{cond_ty}\': '{cond_text}'")
            return
        
        if_blocks = [b for b in ctx.block()]
        
        then_block = None
        else_block = None
        if (len(if_blocks) == 1):
            stmts = [self.ast.get(s) for s in if_blocks[0].statement()]
            then_block = Block(statements=[s for s in stmts if s is not None], ty=NULL)
            # just then block
            pass
        elif (len(if_blocks) == 2):
            stmts1 = [self.ast.get(s) for s in if_blocks[0].statement()]
            then_block = Block(statements=[s for s in stmts1 if s is not None], ty=NULL)
            stmts2 = [self.ast.get(s) for s in if_blocks[1].statement()]
            else_block = Block(statements=[s for s in stmts2 if s is not None], ty=NULL)
            # then and else blocks
            pass
        else:
            self._error(ctx, msg=f"condicion \'if\' no puede tener {len(if_blocks)} bloques")
            return
        node = IfStmt(
            ty=NULL,
            cond = self.ast.get(cond_ctx),
            then_block= then_block,
            else_block= else_block if else_block else None
        )
        self.ast[ctx] = node
        
        
        
    # ---------------------------------- #
    #       Iterative Statements         #
    # -----------------------------------#
    
    def enterDoWhileStatement(self, ctx):
        self.inter_counter+=1;
    def exitDoWhileStatement(self, ctx: CompiscriptParser.DoWhileStatementContext):
        """
        Exige que la condición del while sea booleana.
        Intenta primero con inferencia de tipos; si no hay tipo, cae a literal 'true'/'false'.
        """
        cond_ctx = None
        try:
            # muchas gramáticas exponen la condición como expression()
            exprs = ctx.expression()
            cond_ctx = exprs if not isinstance(exprs, list) else (exprs[0] if exprs else None)
        except Exception:
            cond_ctx = None

        if cond_ctx is None:
            return  # si la gramática no ofrece la condición aquí, no generamos error

        cond_text = cond_ctx.getText()
        cond_ty = self.types.get(cond_ctx, None)

        # Si tenemos sistema de tipos y BOOL está definido:
        try:
            is_bool = (cond_ty == BOOL)
        except NameError:
            is_bool = False

        # Fallback literal
        if not is_bool:
            if cond_text not in ("true", "false"):
                line = getattr(cond_ctx.start, "line", getattr(ctx.start, "line", 1))
                self.errors.append(f"[linea {line}] condicion de 'while' debe ser boolean: '{cond_text}'")
            
        stmts = [self.ast.get(s) for s in ctx.block().statement()]
        block_node = Block(statements=[s for s in stmts if s is not None], ty=NULL)
        while_node = WhileStmt(
            ty=NULL,
            is_do_while=True,
            cond = self.ast.get(cond_ctx),
            body=block_node
        )
        self.ast[ctx] = while_node
        self.inter_counter-=1
        
    def enterWhileStatement(self, ctx):
        self.inter_counter+=1;
    def exitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        """
        Exige que la condición del while sea booleana.
        Intenta primero con inferencia de tipos; si no hay tipo, cae a literal 'true'/'false'.
        """
        cond_ctx = None
        try:
            # muchas gramáticas exponen la condición como expression()
            exprs = ctx.expression()
            cond_ctx = exprs if not isinstance(exprs, list) else (exprs[0] if exprs else None)
        except Exception:
            cond_ctx = None

        if cond_ctx is None:
            return  # si la gramática no ofrece la condición aquí, no generamos error

        cond_text = cond_ctx.getText()
        cond_ty = self.types.get(cond_ctx, None)

        # Si tenemos sistema de tipos y BOOL está definido:
        try:
            is_bool = (cond_ty == BOOL)
        except NameError:
            is_bool = False

        # Fallback literal
        if not is_bool:
            if cond_text not in ("true", "false"):
                line = getattr(cond_ctx.start, "line", getattr(ctx.start, "line", 1))
                self.errors.append(f"[linea {line}] condicion de 'while' debe ser boolean: '{cond_text}'")
                
        stmts = [self.ast.get(s) for s in ctx.block().statement()]
        block_node = Block(statements=[s for s in stmts if s is not None], ty=NULL)
        while_node = WhileStmt(
            ty=NULL,
            is_do_while=False,
            cond = self.ast.get(cond_ctx),
            body=block_node
        )
        self.ast[ctx] = while_node
        self.inter_counter-=1

    def enterForStatement(self, ctx):
        self.inter_counter+=1;
    def exitForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        """
        Exige que la condición del for sea booleana.
        Soporta for estilo C (init; cond; update) y variantes con una sola expresión entre paréntesis.
        """
        cond_ctx = None
        update_ctx = None
        try:
            exprs = ctx.expression()
            if isinstance(exprs, list):
                # Heurística:
                # - Si hay 3 expresiones: (init; cond; update) -> cond es la segunda
                if len(exprs) >= 3:
                    cond_ctx = exprs[1]
                    update_ctx = exprs[2]
                # - Si hay 2 o 1 expresiones, tomamos la primera como condición (caso simple)
                elif len(exprs) >= 1:
                    cond_ctx = exprs[0]
                    update_ctx = exprs[1]
            else:
                cond_ctx = exprs
        except Exception:
            cond_ctx = None

        if cond_ctx is None:
            return

        cond_text = cond_ctx.getText()
        cond_ty = self.types.get(cond_ctx, None)

        try:
            is_bool = (cond_ty  == BOOL)
        except NameError:
            is_bool = False

        if not is_bool:
            if cond_text not in ("true", "false"):
                line = getattr(cond_ctx.start, "line", getattr(ctx.start, "line", 1))
                self.errors.append(f"[linea {line}] condicion de 'for' no es boolean: '{cond_text}'")
        
        stmts = [self.ast.get(s) for s in ctx.block().statement()]
        block_node = Block(statements=[s for s in stmts if s is not None], ty=NULL)
        forNode = ForStmt(
            ty=NULL,
            cond=self.ast.get(cond_ctx),
            update=self.ast.get(update_ctx),
            body=block_node
        )
        self.ast[ctx] = forNode
        self.inter_counter-=1
    
    def enterForeachStatement(self, ctx):
        self.init_foreach_identifyer_flag = True
        
        ## Array preparation
        arr_ctx = ctx.expression()
        arr_sym = self.table.lookup(arr_ctx.getText())
        
        if (not arr_sym):
            self._error(ctx, f"no se pudo determinar la lista {ctx.expression().getText()}")
            return
    
        arr_type = arr_sym.type
        
        if not is_list(arr_type):
            self._error(ctx, f"condicion \'foreach\' espera tipo lista, se obtuvo {array_node.ty}")
            return
    
        # Item preparation
        item_name = ctx.Identifier().getText()
        item_ty = index(arr_type)
        self._define_symbol(
            name_or_symbol=str(item_name),
            ty = item_ty,
            err_ctx=ctx.Identifier()
        )
        self.inter_counter+=1;
        
    def exitForeachStatement(self, ctx: CompiscriptParser.ForeachStatementContext):
        """
        Exige que la condición del for sea booleana.
        Soporta for estilo Python (<item> in <array>)
        """
        # Array iterator:
        array_ctx = ctx.expression()
        array_node = self.ast.get(array_ctx)
        # item iterator 
               
        item_name = ctx.Identifier().getText()
        item_ty = index(array_node.ty)

        item_node = VarDecl(
            ty=item_ty,
            declared_type=item_ty,
            name=item_name
        )

        stmts = [self.ast.get(s) for s in ctx.block().statement()]
        block_node = Block(statements=[s for s in stmts if s is not None], ty=NULL)
        fore_node = ForEachStmt(
            ty=NULL,
            array=array_node,
            item = item_node,
            body=block_node
        )

        self.ast[ctx] = fore_node
        self.inter_counter-=1
        return
    # ---------------------------------- #
    #          Other Statements          #
    # -----------------------------------#
    
    def exitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        actual_ty = NULL
        rn = None
        if ctx.expression():
            rn = self.ast.get(ctx.expression())
            actual_ty = self.types.get(ctx.expression(), ERROR)

        if not self.func_ret_stack:
            line = ctx.start.line
            self.errors.append(f"[linea {line}] 'return' fuera de funcion")
            expected = NULL
        else:
            expected = self.func_ret_stack[-1]
            if not compatible(expected, actual_ty):
                self.errors.append(f"Tipo de retorno incompatible: esperado {expected}, obtenido {actual_ty}")

        self.ast[ctx] = ReturnStmt(expr=rn, ty=actual_ty)

    def exitArrayLiteral(self, ctx):
        elements = []
        types = []
        try: 
            for expr_cntx in ctx.expression():
                if(expr_cntx.Literal()): 
                    sub_lex = expr_cntx.getText()
                    sub_node = returnLiteral(sub_lex)
                    types.append(sub_node.ty)
                    elements.append(sub_node)
        except:
            for expr_cntx in ctx.expression():
                sub_node = self.ast.get(expr_cntx)
                types.append(sub_node.ty)
                elements.append(sub_node)
            
                
        if (len(elements) == 0): # Empty list init
            node = ArrayLiteral(elements=[], ty=type_list(NULL))

        else: # Lista inicial si tiene elementos
            flag = 0
            last = None
            current = None
            for t in types:
                if(last):
                    current = t
                    if(str(last) !=str(t)):
                        flag = 1
                        break
                else:
                    last = t
            if(flag == 1):
                self.errors.append(f"No se puede agrupar tipo \'{last}\' con tipo \'{current}\' en una misma lista")
            node = ArrayLiteral(elements=elements, ty=type_list(last))    
        self.ast[ctx] = node
        self.types[ctx] = node.ty
    
    def exitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        # Caso 1: 'true' | 'false' | 'null'
        text = ctx.getText()
        if text == "true":
            node = Literal(value=True, ty=BOOL)
        elif text == "false":
            node = Literal(value=False, ty=BOOL)
        elif text == "null":
            node = Literal(value=None, ty=NULL)
        # Caso 2: Literal (IntegerLiteral | StringLiteral)
        elif ctx.Literal():
            lex = ctx.Literal().getText()
            node = returnLiteral(lex)
        # Caso 3: arrayLiteral (si decides tiparlo más adelante)
        elif ctx.arrayLiteral():
            arlit = self.ast.get(ctx.arrayLiteral())
            node = arlit

        else:
            node = Literal(value=None, ty=ERROR)
        self.ast[ctx] = node
        self.types[ctx] = node.ty

    def exitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.Identifier().getText()
        sym = self.table.lookup(name)
        if sym is None:
            if self.init_foreach_identifyer_flag:
                self.foreach_item_stack.append(name)
                return
            self.errors.append(f"Identificador no declarado: '{name}'")
            node = Identifier(name=name, ty=ERROR)
            ty = ERROR
        else:
            ty = sym.type or NULL
            node = Identifier(name=name, ty=ty)

        # Mapea en la alternativa...
        self.ast[ctx] = node
        self.types[ctx] = ty
        if ctx.parentCtx is not None:
            self.ast[ctx.parentCtx] = node
            self.types[ctx.parentCtx] = ty

    def exitUnaryExpr(self, ctx: CompiscriptParser.UnaryExprContext):
        if ctx.primaryExpr():
            self.ast[ctx] = self.ast.get(ctx.primaryExpr())
            self.types[ctx] = self.types.get(ctx.primaryExpr(), ERROR)
            return
        op = ctx.getChild(0).getText()
        e_node = self.ast.get(ctx.unaryExpr())
        e_ty = self.types.get(ctx.unaryExpr(), ERROR)
        if op == "!":
            ty = BOOL if e_ty == BOOL else ERROR
        elif op == "-":
            ty = INT if e_ty == INT else ERROR
        else:
            ty = ERROR
        self.ast[ctx] = UnaryOp(op=op, expr=e_node, ty=ty)
        self.types[ctx] = ty

    def _bin2(self, ctx_left, ctx_right, op_text):
        l = self.ast.get(ctx_left); lt = self.types.get(ctx_left, ERROR)
        r = self.ast.get(ctx_right); rt = self.types.get(ctx_right, ERROR)
        ty = unify_bin(op_text, lt, rt)
        return BinaryOp(op=op_text, left=l, right=r, ty=ty), ty

########
    def exitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        if len(ctx.unaryExpr()) == 1:            
            sub = ctx.unaryExpr(0)
            self.ast[ctx] = self.ast.get(sub)
            self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.unaryExpr(0), ctx.unaryExpr(1), op)
        compat = (node.right.ty == node.left.ty) and (node.right.ty == INT)
        if (not compat):
            self.errors.append(f"No se puede aplicar {op} a tipos \'{node.left.ty}\' y \'{node.right.ty}\'")
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        if len(ctx.multiplicativeExpr()) == 1:
            sub = ctx.multiplicativeExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.multiplicativeExpr(0), ctx.multiplicativeExpr(1), op)
        compat = (node.right.ty == node.left.ty) and ((node.right.ty == STR) or (node.right.ty == INT))
        if (not compat):
            self.errors.append(f"No se puede aplicar {op} a tipos \'{node.left.ty}\' y \'{node.right.ty}\'")
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        if len(ctx.equalityExpr()) == 1:
            sub = ctx.equalityExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.equalityExpr(0), ctx.equalityExpr(1), op)
        compat = (node.right.ty == node.left.ty) and (node.right.ty == BOOL)
        if (not compat):
            self.errors.append(f"No se puede aplicar {op} a tipos \'{node.left.ty}\' y \'{node.right.ty}\'")
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        if len(ctx.logicalAndExpr()) == 1:
            sub = ctx.logicalAndExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.logicalAndExpr(0), ctx.logicalAndExpr(1), "||")
        compat = (node.right.ty == node.left.ty) and (node.right.ty == BOOL)
        if (not compat):
            self.errors.append(f"No se puede aplicar {op} a tipos \'{node.left.ty}\' y \'{node.right.ty}\'")
        self.ast[ctx] = node; self.types[ctx] = ty
######

    def exitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        if len(ctx.additiveExpr()) == 1:
            sub = ctx.additiveExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.additiveExpr(0), ctx.additiveExpr(1), op)
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        if len(ctx.relationalExpr()) == 1:
            sub = ctx.relationalExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.relationalExpr(0), ctx.relationalExpr(1), op)
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitExpression(self, ctx: CompiscriptParser.ExpressionContext):
        sub = ctx.assignmentExpr()
        try:
            lhs = sub.leftHandSide()

            if(isinstance(self.ast.get(lhs), Indexed)):
                indexed = self.ast.get(lhs)
                rhs = sub.assignmentExpr()
                
                compat = compatible(indexed.ty, self.types[rhs] )
                
                if compat:
                    node = Assign(
                        ty =indexed.ty,
                        dest = indexed.array,
                        index = indexed.index,
                        value = self.ast[rhs]
                    )
                    self.ast[ctx] = node
                    self.types[ctx] = self.types.get(self.types[rhs], ERROR)
                else:
                    self.errors.append(f"Tipo de asignacion incompatible: esperado {indexed.ty}, obtenido {self.types[rhs]}")
                return
            else:
                rhs = sub.assignmentExpr()
                orig_node =  self.ast.get(lhs)
                dest_node = self.ast.get(rhs)
                op_ty = self.types.get(lhs, ERROR)
                node = Assign(
                    ty =  op_ty,
                    dest =  self.ast.get(lhs),
                    value = self.ast.get(rhs)
                )
                self.ast[ctx] = node
                self.types[ctx] = op_ty
                return
            
        except:
            if sub in self.ast:
                self.ast[ctx] = self.ast[sub]
                self.types[ctx] = self.types.get(sub, ERROR)
            else:
                
                return

    def exitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        # primaryExpr: literalExpr | leftHandSide | '(' expression ')'
        if ctx.literalExpr():
            node = self.ast.get(ctx.literalExpr()); ty = self.types.get(ctx.literalExpr(), ERROR)
        elif ctx.leftHandSide():
            node = self.ast.get(ctx.leftHandSide()); ty = self.types.get(ctx.leftHandSide(), ERROR)
        else:
            # '(' expression ')'
            node = self.ast.get(ctx.expression()); ty = self.types.get(ctx.expression(), ERROR)
        self.ast[ctx] = node
        self.types[ctx] = ty
        

    def exitLeftHandSide(self, ctx: CompiscriptParser.LeftHandSideContext):
        """
        leftHandSide: primaryAtom (suffixOp)*
        Procesa en orden los sufijos: .prop / (args) / [idx] (este último aún no soportado).
        """
        # Estado inicial (objeto base)
        node = self.ast.get(ctx.primaryAtom())
        ty   = self.types.get(ctx.primaryAtom(), ERROR)

        suffixes = list(ctx.suffixOp())
        if not suffixes:
            self.ast[ctx] = node
            self.types[ctx] = ty
            return

        # Usaremos estas variables para validar llamadas a métodos
        last_class_sym = None
        last_prop_name = None

        for sfx in suffixes:
            # --- Acceso por punto: '.' Identifier ---
            if isinstance(sfx, CompiscriptParser.PropertyAccessExprContext):
                prop_name = sfx.Identifier().getText()
                # 'ty' debe ser el nombre de una clase para poder acceder a atributos/métodos
                
                # print("==== DOT DEBUG ====")
                # print("suffix text:", sfx.getText())
                # print("prop_name:", prop_name)
                # print("current ty object:", ty, "| ty.name:", getattr(ty, "name", None))
                # print("lookup result:", self.table.lookup(getattr(ty, "name", None)))
                # if self.table.lookup(getattr(ty, "name", None)):
                #     print("attrs:", list(self.table.lookup(ty.name).metadata.get("attributes", {}).keys()))
                #     print("methods:", list(self.table.lookup(ty.name).metadata.get("methods", {}).keys()))
                # print("===================")

                
                class_sym = self.table.lookup(ty.name)
                if not (class_sym and class_sym.type == "class"):
                    self.errors.append(f"Tipo '{ty}' no tiene atributos")
                    self.ast[ctx] = node
                    self.types[ctx] = ERROR
                    return

                attrs = class_sym.metadata.get("attributes", {})
                methods = class_sym.metadata.get("methods", {})

                if prop_name in attrs:
                    attr_sym = attrs[prop_name]
                    ty = Type(attr_sym.type)           # p.ej. string/integer
                    node = PropertyAccess(obj=node, prop=prop_name, ty=ty)
                    last_class_sym = class_sym
                    last_prop_name = prop_name

                elif prop_name in methods:
                    # Al acceder al método sin llamarlo todavía, tipamos como 'func'
                    ty = Type("func")
                    node = PropertyAccess(obj=node, prop=prop_name, ty=ty)
                    last_class_sym = class_sym
                    last_prop_name = prop_name

                else:
                    self.errors.append(f"Atributo o método '{prop_name}' no existe en clase '{ty}'")
                    self.ast[ctx] = node
                    self.types[ctx] = ERROR
                    return

            # --- Llamada: '(' arguments? ')' ---
            elif isinstance(sfx, CompiscriptParser.CallExprContext):
                # Recolecta argumentos ya tipados
                arg_nodes, arg_types = [], []
                if sfx.arguments():
                    for e in sfx.arguments().expression():
                        arg_nodes.append(self.ast.get(e))
                        arg_types.append(self.types.get(e, ERROR))

                ret = NULL

                # print("==== CALL DEBUG ====")
                # print("node before call:", node)
                # print("last_class_sym:", last_class_sym)
                # print("last_prop_name:", last_prop_name)
                # print("arg_types:", [str(a) for a in arg_types])
                # print("====================")

                # Caso 1: llamada a método, ej. obj.m(...)
                if isinstance(node, PropertyAccess) and last_class_sym and last_prop_name:
                    methods = last_class_sym.metadata.get("methods", {})
                    msym = methods.get(last_prop_name)
                    if not msym:
                        # PropertyAccess no era un método realmente
                        self.errors.append(f"Llamada a no-método '{last_prop_name}'")
                        self.ast[ctx] = node
                        self.types[ctx] = ERROR
                        return
                    meta = msym.metadata or {}
                    expected = meta.get("params", [])
                    ret = meta.get("ret", NULL)
                    if len(arg_types) != len(expected):
                        self.errors.append(
                            f"Numero de argumentos invalido en llamada a '{last_prop_name}': esperado {len(expected)}, obtenido {len(arg_types)}"
                        )
                    else:
                        for i, (a, exp) in enumerate(zip(arg_types, expected), start=1):
                            if not compatible(exp, a):
                                self.errors.append(
                                    f"Argumento {i} invalido en llamada a '{last_prop_name}': esperado {exp}, obtenido {a}"
                                )
                    node = Call(callee=node, args=arg_nodes, ty=ret)
                    ty = ret

                # Caso 2: llamada a función global, ej. f(...)
                elif isinstance(node, Identifier):
                    fname = node.name
                    sym = self.table.lookup(fname)
                    if sym is None or not getattr(sym, "metadata", None) or sym.metadata.get("kind") != "func":
                        self.errors.append(f"Funcion no declarada: '{fname}'")
                        self.ast[ctx] = node
                        self.types[ctx] = ERROR
                        return
                    meta = sym.metadata
                    expected_n     = meta.get("arity", len(meta.get("params", [])))
                    expected_types = meta.get("params", [])
                    ret            = meta.get("ret", NULL)

                    if len(arg_types) != expected_n:
                        self.errors.append(
                            f"Numero de argumentos invalido en llamada a '{fname}': esperado {expected_n}, obtenido {len(arg_types)}"
                        )
                    else:
                        for i, (a, exp) in enumerate(zip(arg_types, expected_types), start=1):
                            if not compatible(exp, a):
                                self.errors.append(
                                    f"Argumento {i} invalido en llamada a '{fname}': esperado {exp}, obtenido {a}"
                                )

                    node = Call(callee=node, args=arg_nodes, ty=ret)
                    ty = ret

                else:
                    # Llamadas sobre algo que no es ni Identifier ni PropertyAccess (p.ej. (expr)())
                    self.errors.append("Llamada sobre objeto no invocable")
                    self.ast[ctx] = node
                    self.types[ctx] = ERROR
                    return

                # tras una llamada, ya no hay 'último método'
                last_prop_name = None
                last_class_sym = None

            # --- Indexación: '[' expression ']' (aún no soportado) ---
            elif isinstance(sfx, CompiscriptParser.IndexExprContext):
                if (is_list(node.ty)):
                    # Chequear que la indexacion sea por un tipo entero
                    suf_exp = self.types[sfx.expression()]
                    if(str(suf_exp) != 'integer'):
                        self.errors.append(f"Indexacion debe ser tipo \'integer\' no {suf_exp}")
                        return
                    # print("\t Suf exp", suf_exp)
                    # print("\t Base node", str(base_node.ty))
                    
                    ty = index(node.ty)
                    tem_node = Indexed(
                        name ="*"+str(node.name),
                        array = node,
                        index = self.ast[sfx.expression()],
                        ty = ty
                    )
                    
                    # print("\n")
                    self.ast[ctx] = tem_node
                    self.types[ctx] = ty
                    node = tem_node
                else:
                    self.errors.append(f"Objeto de tipo \'{node.ty}\' no soporta indexacion")
                    return
            else:
                # Desconocido: fallback
                self.ast[ctx] = node
                self.types[ctx] = ty
                return

        # Resultado final del encadenamiento
        self.ast[ctx] = node
        self.types[ctx] = ty

    def exitTernaryExpr(self, ctx: CompiscriptParser.TernaryExprContext):
        # conditionalExpr: logicalOrExpr ('?' expression ':' expression)?
        if ctx.getChildCount() == 1:
            node = self.ast.get(ctx.logicalOrExpr())
            ty = self.types.get(ctx.logicalOrExpr(), ERROR)
        else:
            cond_ty = self.types.get(ctx.logicalOrExpr(), ERROR)
            then_ty = self.types.get(ctx.expression(0), ERROR)
            else_ty = self.types.get(ctx.expression(1), ERROR)
            if cond_ty != BOOL:
                self.errors.append("La condicion del operador ternario debe ser boolean")
            ty = then_ty if then_ty == else_ty else ERROR
            node = self.ast.get(ctx.logicalOrExpr())  # opcional: crear nodo Ternary

        self.ast[ctx] = node
        self.types[ctx] = ty

    def exitExprNoAssign(self, ctx: CompiscriptParser.ExprNoAssignContext):
        # assignmentExpr: conditionalExpr  (#ExprNoAssign)
        node = self.ast.get(ctx.conditionalExpr()); ty = self.types.get(ctx.conditionalExpr(), ERROR)
        self.ast[ctx] = node
        self.types[ctx] = ty

    def exitInitializer(self, ctx: CompiscriptParser.InitializerContext):
        self.ast[ctx] = self.ast.get(ctx.expression())
        self.types[ctx] = self.types.get(ctx.expression(), ERROR)
        
    def exitStatement(self, ctx: CompiscriptParser.StatementContext):
        # Toma el primer hijo no-nulo y mapea el statement a ese AST
        child = (
            ctx.variableDeclaration() or
            ctx.constantDeclaration() or
            ctx.assignment() or
            ctx.functionDeclaration() or
            ctx.classDeclaration() or
            ctx.expressionStatement() or
            ctx.printStatement() or
            ctx.block() or
            ctx.ifStatement() or
            ctx.whileStatement() or
            ctx.doWhileStatement() or
            ctx.forStatement() or
            ctx.foreachStatement() or
            ctx.tryCatchStatement() or
            ctx.switchStatement() or
            ctx.breakStatement() or
            ctx.continueStatement() or
            ctx.returnStatement()
        )
        if child in self.ast:
            self.ast[ctx] = self.ast[child]

    def exitExpressionStatement(self, ctx: CompiscriptParser.ExpressionStatementContext):
        node = self.ast.get(ctx.expression())
        self.ast[ctx] = node
        self.types[ctx] = self.types.get(ctx.expression(), ERROR)

    def _define_symbol(self, name_or_symbol, ty=None, metadata=None, err_ctx=None):
        """
        Wrapper que intenta definir un símbolo en la tabla y, si falla,
        añade un error **con línea** en el formato: [linea N] '<name>' ya está definido en el ambito actual
        """
        # línea a usar si hay error
        line = 1
        if err_ctx is not None:
            try:
                line = getattr(err_ctx.start, "line", 1)
            except Exception:
                line = 1

        try:
            # firma flexible
            if isinstance(name_or_symbol, str):
                ok = self.table.define(name_or_symbol, ty, metadata or {})
            else:
                ok = self.table.define(name_or_symbol)

            # por compatibilidad si define() devuelve False
            if ok is False:
                nm = name_or_symbol if isinstance(name_or_symbol, str) else getattr(name_or_symbol, "name", "??")
                self.errors.append(f"[linea {line}] '{nm}' ya está definido en el ambito actual")

        except KeyError as ke:
            # extrae el nombre del mensaje en inglés si viene así
            msg = ke.args[0] if ke.args else str(ke)
            nm = None
            if isinstance(msg, str):
                import re
                m = re.search(r"'([^']+)'", msg)
                if m:
                    nm = m.group(1)
            if nm is None:
                nm = name_or_symbol if isinstance(name_or_symbol, str) else getattr(name_or_symbol, "name", "??")
            self.errors.append(f"[linea {line}] '{nm}' ya está definido en el ambito actual")

        except TypeError:
            # firma antigua: define(name, type)
            if not isinstance(name_or_symbol, str):
                nm = getattr(name_or_symbol, "name", None)
                self.table.define(nm, ty)
            else:
                raise


    def enterFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        self.current_method = name

        # Firma: params
        params = []
        if ctx.parameters():
            for pctx in ctx.parameters().parameter():
                pname = pctx.Identifier().getText()
                ptxt = _get_type_text_from_ctx(pctx)
                pty  = _parse_type_text(ptxt) or NULL
                params.append((pname, pty))

        # Tipo de retorno (opcional)
        rtxt = _get_type_text_from_ctx(ctx)
        ret  = _parse_type_text(rtxt) or NULL

        # Define símbolo de función ANTES de su cuerpo (recursión permitida)
        meta = {
            "kind": "func",
            "params": [t for _, t in params],
            "param_names": [n for n, _ in params],
            "arity": len(params),
            "ret": ret,
        }
        # Atrapa duplicados en el mismo ámbito
        try:
            self._define_symbol(name, ret, metadata=meta, err_ctx=ctx)
        except Exception as e:
            # deja registro pero NO abortes el walk
            self.errors.append(str(e))

        # Si estamos dentro de una clase, agregarlo al frame
        if self.current_class and self._class_frames:
            frame = self._class_frames[-1]
            meta = {
                "kind": "method",
                "params": [t for _, t in params],
                "ret": ret,
            }
            frame["methods"][name] = Symbol(name, "func", metadata=meta)
            if name == "constructor":
                frame["methods"]["constructor"] = Symbol("constructor", "func", metadata=meta)
            frame["symbol"].metadata["methods"] = frame["methods"]

        # Scope de función + parámetros
        self._enter_scope()
        self.func_ret_stack.append(ret)
        for pname, pty in params:
            self._define_symbol(pname, pty, err_ctx=ctx)

    def exitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()

        params = []
        if ctx.parameters():
            for pctx in ctx.parameters().parameter():
                pname = pctx.Identifier().getText()
                ptxt = _get_type_text_from_ctx(pctx)
                pty  = _parse_type_text(ptxt) or NULL
                params.append((pname, pty))

        rtxt = _get_type_text_from_ctx(ctx)
        ret  = _parse_type_text(rtxt) or NULL
        body = self.ast.get(ctx.block())

        node = FuncDecl(name=name, params=params, ret=ret, body=body, ty=ret)
        self.ast[ctx] = node

        self.current_method = None

        self.func_ret_stack.pop()
        self._exit_scope()
    
    def enterClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        cls_name = ctx.Identifier(0).getText()
        self.current_class = cls_name

        # Pre-registrar la clase en el scope global con metadata vacía
        sym = self.table.scopes[0].get(cls_name)
        if not sym or sym.type != "class":
            sym = Symbol(cls_name, "class", metadata={"attributes": {}, "methods": {}, "base": None})
            self.table.scopes[0][cls_name] = sym

        # Abrir un frame para acumular miembros durante el recorrido
        self._class_frames.append({
            "name": cls_name,
            "symbol": sym,
            "attributes": {},  # name -> Symbol
            "methods": {},     # name -> Symbol
        })

    def exitClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        # Nombre de la clase base (si existe)
        base_tok  = ctx.Identifier(1)
        base_name = base_tok.getText() if base_tok else None

        # Cerrar el frame actual
        frame = self._class_frames.pop()
        sym = frame["symbol"]

        # Actualizar base en el símbolo
        sym.metadata["base"] = base_name

        # Crear nodo AST de clase (puedes guardar miembros si quieres)
        self.ast[ctx] = ClassDecl(
            name=frame["name"],
            members=[],  # si quieres, aquí podrías pasar frame["attributes"].values() + frame["methods"].values()
            ty=Type(frame["name"])
        )

        # Limpiar contexto actual
        self.current_class = None

        # print("Definiendo clase", frame["name"],
        #     "con atributos", list(frame["attributes"].keys()),
        #     "y métodos", list(frame["methods"].keys()))

    def exitNewExpr(self, ctx: CompiscriptParser.NewExprContext):
        cls = ctx.Identifier().getText()
        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                args.append(self.ast.get(e))

        class_sym = self.table.lookup_class(cls)
        if not class_sym:
            self.errors.append(f"Clase '{cls}' no declarada")
            self.ast[ctx] = NewExpr(class_name=cls, args=args, ty=ERROR)
            self.types[ctx] = ERROR
            return

        ctor = class_sym.metadata.get("methods", {}).get("constructor")
        if ctor:
            expected = ctor.metadata.get("params", [])
            if len(args) != len(expected):
                self.errors.append(f"Constructor de '{cls}' espera {len(expected)} args, obtuvo {len(args)}")

        ty = Type(cls)
        self.ast[ctx] = NewExpr(class_name=cls, args=args, ty=ty)
        self.types[ctx] = ty

    def exitThisExpr(self, ctx: CompiscriptParser.ThisExprContext):
        if not self.current_class:
            self.errors.append("'this' usado fuera de clase")
            self.ast[ctx] = ThisExpr(ty=ERROR)
            self.types[ctx] = ERROR
            return
        ty = Type(self.current_class)
        self.ast[ctx] = ThisExpr(ty=ty)
        self.types[ctx] = ty

    def exitContinueStatement(self, ctx):
        if(self.inter_counter > 0):
            self.ast[ctx] = ContinueStmt()
        else:
            self._error(ctx, msg="llamada a \'continue\' invalida fuera iterador")
        return
    
    def exitBreakStatement(self, ctx):
        if(self.inter_counter > 0):
            self.ast[ctx] = BreakStmt()
        else:
            self._error(ctx, msg="llamada a \'break\' invalida fuera iterador")
        return
    # def exitCallExpr(self, ctx: CompiscriptParser.CallExprContext):
    #     """
    #     En esta gramática, CallExpr es sólo el sufijo '(args)'.
    #     El callee está en el primaryAtom del LeftHandSide padre.
    #     Aquí armamos la Call y la escribimos directamente sobre el LeftHandSide padre.
    #     """
    #     # 1) Ubicar el LeftHandSide contenedor
    #     p = ctx.parentCtx
    #     lhs_ctx = None
    #     while p is not None:
    #         if isinstance(p, CompiscriptParser.LeftHandSideContext):
    #             lhs_ctx = p
    #             break
    #         p = getattr(p, "parentCtx", None)

    #     # Si por alguna razón no hallamos el LHS, salimos silenciosamente
    #     if lhs_ctx is None:
    #         return

    #     # 2) Tomar el callee desde el primaryAtom del LHS (ya resuelto en exitIdentifierExpr)
    #     callee_node = self.ast.get(lhs_ctx.primaryAtom())
    #     callee_ty   = self.types.get(lhs_ctx.primaryAtom(), ERROR)

    #     # Sólo soportamos callee como identificador simple por ahora
    #     if not isinstance(callee_node, Identifier):
    #         # Si hubiese sido algo como obj.m(...), tu política actual es marcar no soportado
    #         self.errors.append("Accesos/calls/indexacion no soportados aun en esta fase.")
    #         self.ast[lhs_ctx] = callee_node
    #         self.types[lhs_ctx] = ERROR
    #         return

    #     fname = callee_node.name
    #     sym = self.table.lookup(fname)
    #     if sym is None or not getattr(sym, "metadata", None) or sym.metadata.get("kind") != "func":
    #         self.errors.append(f"Funcion no declarada: '{fname}'")
    #         call_node = Call(callee=callee_node, args=[], ty=ERROR)
    #         self.ast[lhs_ctx] = call_node
    #         self.types[lhs_ctx] = ERROR
    #         return

    #     # 3) Recolectar argumentos ya tipados
    #     arg_nodes, arg_types = [], []
    #     if ctx.arguments():
    #         for e in ctx.arguments().expression():
    #             arg_nodes.append(self.ast.get(e))
    #             arg_types.append(self.types.get(e, ERROR))

    #     meta = sym.metadata
    #     expected_n     = meta.get("arity", len(meta.get("params", [])))
    #     expected_types = meta.get("params", [])
    #     ret            = meta.get("ret", NULL)

    #     if len(arg_types) != expected_n:
    #         self.errors.append(
    #             f"Numero de argumentos invalido en llamada a '{fname}': esperado {expected_n}, obtenido {len(arg_types)}"
    #         )
    #     else:
    #         for i, (a, exp) in enumerate(zip(arg_types, expected_types), start=1):
    #             if not compatible(exp, a):
    #                 self.errors.append(
    #                     f"Argumento {i} invalido en llamada a '{fname}': esperado {exp}, obtenido {a}"
    #                 )

    #     # 4) Registrar la llamada como valor del LHS (para que primaryExpr la recoja)
    #     call_node = Call(callee=callee_node, args=arg_nodes, ty=ret)
    #     self.ast[lhs_ctx] = call_node
    #     self.types[lhs_ctx] = ret