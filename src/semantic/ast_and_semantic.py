from antlr4 import ParseTreeWalker
from parser.CompiscriptParser import CompiscriptParser
from parser.CompiscriptListener import CompiscriptListener
from typing import Optional, List, Dict, Any
from symbol_table.symbol_table import Symbol, SymbolTable
from ast_nodes import *

def unify_bin(op: str, lt: Type, rt: Type) -> Type:
    if op in {"+", "-", "*", "/", "%"}:
        return INT if lt == INT and rt == INT else ERROR
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
    return str(expected)==str(actual)


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
        self.func_ret_stack: List[Type] = [] #Agregar un stack para validar los returns

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
            self._define_symbol(name, declared or (init_ty if (init_ty != NULL) else None))
        except Exception as e:
            self.errors.append(str(e))

        if ctx.initializer() and not compatible(declared, init_ty):
            self.errors.append(f"Tipo incompatible en inicializacion de '{name}': esperado {declared}, obtenido {init_ty}")

        node = VarDecl(name=name, is_const=False, declared_type=declared, init=init_node, ty=declared or init_ty or NULL)
        self.ast[ctx] = node
        
        
    def exitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()
        declared = None
        ttxt = _get_type_text_from_ctx(ctx)
        if ttxt:
            declared = _parse_type_text(ttxt)

        expr_node = self.ast.get(ctx.expression())
        expr_ty = self.types.get(ctx.expression(), ERROR)

        try:
            self._define_symbol(name, declared or expr_ty)
        except Exception as e:
            self.errors.append(str(e))

        if declared and not compatible(declared, expr_ty):
            self.errors.append(f"Tipo incompatible en const '{name}': esperado {declared}, obtenido {expr_ty}")

        self.const_scopes[-1].add(name)

        node = VarDecl(name=name, is_const=True, declared_type=declared, init=expr_node, ty=declared or expr_ty)
        self.ast[ctx] = node

    def exitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        # Normaliza expressions a lista y toma RHS (último) como valor a asignar
        exprs = ctx.expression()
        expr_list = exprs if isinstance(exprs, list) else [exprs]
        rhs_ctx = expr_list[-1]
        val_node = self.ast.get(rhs_ctx)
        val_ty = self.types.get(rhs_ctx, ERROR)

        ids = ctx.Identifier()

        # ¿Es asignación a propiedad? (expression '.' Identifier '=' expression)
        if isinstance(ids, list):
            # ids[-1] sería el nombre de la propiedad; el objeto base está en expr_list[0]
            # Para esta fase básica, deja un error (o WARNING) y sal:
            self.errors.append("Asignacion a propiedad no soportada en esta fase (se implementara con objetos/clases).")
            # Aun así, registra un nodo Assign placeholder con tipo ERROR:
            self.ast[ctx] = Assign(name="__property__", value=val_node, ty=ERROR)
            return

        # Alternativa simple: Identifier '=' expression ';'
        name = ids.getText()
        sym = self.table.lookup(name)
        var_ty = ERROR if sym is None else (sym.type or NULL)

        # ¿es const?
        for scope_consts in reversed(self.const_scopes):
            if name in scope_consts:
                self.errors.append(f"No se puede asignar a const '{name}'")
                break

        if sym is None:
            self.errors.append(f"Identificador no declarado: '{name}'")
        elif var_ty not in (None, NULL, ERROR) and val_ty != ERROR and var_ty != val_ty:
            self.errors.append(f"Asignacion incompatible a '{name}': {var_ty} = {val_ty}")

        self.ast[ctx] = Assign(name=name, value=val_node, ty=(var_ty if var_ty == val_ty or var_ty in (None, NULL) else ERROR))

    def exitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        expr_node = self.ast.get(ctx.expression())
        self.ast[ctx] = PrintStmt(expr=expr_node, ty=NULL)

    def exitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        cond_ty = self.types.get(ctx.expression(), ERROR)
        if cond_ty != BOOL:
            self.errors.append("La condicion del if debe ser boolean")
        then_block = self.ast.get(ctx.block(0))
        else_block = self.ast.get(ctx.block(1)) if len(ctx.block()) > 1 else None
        self.ast[ctx] = IfStmt(cond=self.ast.get(ctx.expression()), then_block=then_block, else_block=else_block, ty=NULL)

    def exitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        cond_ty = self.types.get(ctx.expression(), ERROR)
        if cond_ty != BOOL:
            self.errors.append("La condicion del while debe ser boolean")
        self.ast[ctx] = WhileStmt(cond=self.ast.get(ctx.expression()), body=self.ast.get(ctx.block()), ty=NULL)

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
        if (ty == ERROR):
            self.errors.append(f"No se puede aplicar {op} a tipos \'{node.left.ty}\' y \'{node.right.ty}\'")
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        if len(ctx.multiplicativeExpr()) == 1:
            sub = ctx.multiplicativeExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.multiplicativeExpr(0), ctx.multiplicativeExpr(1), op)
        if (ty == ERROR):
            self.errors.append(f"No se puede aplicar {op} a tipos \'{node.left.ty}\' y \'{node.right.ty}\'")
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        if len(ctx.equalityExpr()) == 1:
            sub = ctx.equalityExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.equalityExpr(0), ctx.equalityExpr(1), op)
        if (ty == ERROR):
            self.errors.append(f"No se puede aplicar {op} a tipos \'{node.left.ty}\' y \'{node.right.ty}\'")
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        if len(ctx.logicalAndExpr()) == 1:
            sub = ctx.logicalAndExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.logicalAndExpr(0), ctx.logicalAndExpr(1), "||")
        if (ty == ERROR):
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
        if sub in self.ast:
            self.ast[ctx] = self.ast[sub]
            self.types[ctx] = self.types.get(sub, ERROR)
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
        # leftHandSide: primaryAtom (suffixOp)*
        base_node = self.ast.get(ctx.primaryAtom()); base_ty = self.types.get(ctx.primaryAtom(), ERROR)
        # Para esta fase básica, si hay suffixOp (llamada, indexación, propiedad) marcamos como no soportado
        suffixes = list(ctx.suffixOp())
        if not suffixes:
            self.ast[ctx] = base_node
            self.types[ctx] = base_ty
            return
        # Si hay propiedad o indexación en cualquiera de los sufijos -> aún no soportado
        txt_all = "".join(s.getText() for s in suffixes)
        if ("[" in txt_all) or ("." in txt_all):
            self.errors.append("Accesos/calls/indexacion no soportados aun en esta fase.")
            self.ast[ctx] = base_node
            self.types[ctx] = ERROR
            return 
        # Sólo sufijos de llamada '()': deja el resultado que ya construyó exitCallExpr
        node = self.ast.get(ctx)
        ty   = self.types.get(ctx, ERROR)
        if node is None:
            # Fallback: si por cualquier razón exitCallExpr no corrió, deja el base
            node, ty = base_node, base_ty
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

    def _define_symbol(self, name_or_symbol, ty=None, metadata=None):
        """
        Wrapper que intenta definir un símbolo en la tabla:
        - acepta ambas firmas: Symbol(...) o (name, type)
        - captura KeyError o retorno False y añade al self.errors un mensaje en español
        con la frase que los tests de semántica esperan:
        "'<name>' ya está definido en el ambito actual" (incluye nombre).
        """
        try:
            # si le pasaron name + type, usamos la firma flexible
            if isinstance(name_or_symbol, str):
                # name_or_symbol == name, ty == type
                ok = self.table.define(name_or_symbol, ty, metadata or {})
            else:
                # asumimos que es un Symbol object
                ok = self.table.define(name_or_symbol)

            # en caso de que la implementación devuelva False (alguna versión antigua)
            if ok is False:
                nm = name_or_symbol if isinstance(name_or_symbol, str) else getattr(name_or_symbol, "name", "??")
                self.errors.append(f"'{nm}' ya está definido en el ambito actual")

        except KeyError as ke:
            # la SymbolTable ya registró (en inglés) el error; aquí añadimos la versión en español
            # para que los tests de semántica lo vean
            msg = ke.args[0] if ke.args else str(ke)
            nm = None
            if isinstance(msg, str):
                import re
                m = re.search(r"'([^']+)'", msg)
                if m:
                    nm = m.group(1)
            if nm is None:
                nm = name_or_symbol if isinstance(name_or_symbol, str) else getattr(name_or_symbol, "name", "??")
            self.errors.append(f"'{nm}' ya está definido en el ambito actual")

        except TypeError:
            # compatibilidad con firma antigua: reintentar con define(name, type)
            if not isinstance(name_or_symbol, str):
                nm = getattr(name_or_symbol, "name", None)
                self.table.define(nm, ty)
            else:
                raise




    def enterFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()

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
            self._define_symbol(name, ret, metadata=meta)
        except Exception as e:
            # deja registro pero NO abortes el walk
            self.errors.append(str(e))

        # Scope de función + parámetros
        self._enter_scope()
        self.func_ret_stack.append(ret)
        for pname, pty in params:
            self._define_symbol(pname, pty)

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

        self.func_ret_stack.pop()
        self._exit_scope()
    
    def exitCallExpr(self, ctx: CompiscriptParser.CallExprContext):
        """
        En esta gramática, CallExpr es sólo el sufijo '(args)'.
        El callee está en el primaryAtom del LeftHandSide padre.
        Aquí armamos la Call y la escribimos directamente sobre el LeftHandSide padre.
        """
        # 1) Ubicar el LeftHandSide contenedor
        p = ctx.parentCtx
        lhs_ctx = None
        while p is not None:
            if isinstance(p, CompiscriptParser.LeftHandSideContext):
                lhs_ctx = p
                break
            p = getattr(p, "parentCtx", None)

        # Si por alguna razón no hallamos el LHS, salimos silenciosamente
        if lhs_ctx is None:
            return

        # 2) Tomar el callee desde el primaryAtom del LHS (ya resuelto en exitIdentifierExpr)
        callee_node = self.ast.get(lhs_ctx.primaryAtom())
        callee_ty   = self.types.get(lhs_ctx.primaryAtom(), ERROR)

        # Sólo soportamos callee como identificador simple por ahora
        if not isinstance(callee_node, Identifier):
            # Si hubiese sido algo como obj.m(...), tu política actual es marcar no soportado
            self.errors.append("Accesos/calls/indexacion no soportados aun en esta fase.")
            self.ast[lhs_ctx] = callee_node
            self.types[lhs_ctx] = ERROR
            return

        fname = callee_node.name
        sym = self.table.lookup(fname)
        if sym is None or not getattr(sym, "metadata", None) or sym.metadata.get("kind") != "func":
            self.errors.append(f"Funcion no declarada: '{fname}'")
            call_node = Call(callee=callee_node, args=[], ty=ERROR)
            self.ast[lhs_ctx] = call_node
            self.types[lhs_ctx] = ERROR
            return

        # 3) Recolectar argumentos ya tipados
        arg_nodes, arg_types = [], []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                arg_nodes.append(self.ast.get(e))
                arg_types.append(self.types.get(e, ERROR))

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

        # 4) Registrar la llamada como valor del LHS (para que primaryExpr la recoja)
        call_node = Call(callee=callee_node, args=arg_nodes, ty=ret)
        self.ast[lhs_ctx] = call_node
        self.types[lhs_ctx] = ret
