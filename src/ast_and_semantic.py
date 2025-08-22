from antlr4 import ParseTreeWalker
from CompiscriptListener import CompiscriptListener
from CompiscriptParser import CompiscriptParser
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

def compatible(expected: Optional[Type], actual: Type) -> bool:
    if expected is None:
        return True
    return expected == actual

class AstAndSemantic(CompiscriptListener):
    def __init__(self):
        self.ast: Dict[Any, ASTNode] = {}
        self.types: Dict[Any, Type] = {}
        self.errors: List[str] = []
        self.table = SymbolTable()
        self.program = Program()
        self.const_scopes: List[set] = [set()]

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
        name = ctx.Identifier().getText()
        declared = None
        if ctx.typeAnnotation():
            declared = ctx.typeAnnotation().getText().replace(":", "").strip()
        init_node = None
        init_ty = NULL
        if ctx.initializer():
            init_node = self.ast.get(ctx.initializer())
            init_ty = self.types.get(ctx.initializer(), ERROR)
        try:
            self._define_symbol(name, declared or (init_ty if init_ty != NULL else None))
        except Exception as e:
            self.errors.append(str(e))

        if ctx.initializer() and not compatible(declared, init_ty):
            self.errors.append(f"Tipo incompatible en inicialización de '{name}': esperado {declared}, obtenido {init_ty}")

        node = VarDecl(name=name, is_const=False, declared_type=declared, init=init_node, ty=declared or init_ty or NULL)
        self.ast[ctx] = node

    def exitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()
        declared = None
        if ctx.typeAnnotation():
            declared = ctx.typeAnnotation().getText().replace(":", "").strip()
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
            self.errors.append("Asignación a propiedad no soportada en esta fase (se implementará con objetos/clases).")
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
            self.errors.append(f"Asignación incompatible a '{name}': {var_ty} = {val_ty}")

        self.ast[ctx] = Assign(name=name, value=val_node, ty=(var_ty if var_ty == val_ty or var_ty in (None, NULL) else ERROR))

    def exitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        expr_node = self.ast.get(ctx.expression())
        self.ast[ctx] = PrintStmt(expr=expr_node, ty=NULL)

    def exitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        cond_ty = self.types.get(ctx.expression(), ERROR)
        if cond_ty != BOOL:
            self.errors.append("La condición del if debe ser boolean")
        then_block = self.ast.get(ctx.block(0))
        else_block = self.ast.get(ctx.block(1)) if len(ctx.block()) > 1 else None
        self.ast[ctx] = IfStmt(cond=self.ast.get(ctx.expression()), then_block=then_block, else_block=else_block, ty=NULL)

    def exitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        cond_ty = self.types.get(ctx.expression(), ERROR)
        if cond_ty != BOOL:
            self.errors.append("La condición del while debe ser boolean")
        self.ast[ctx] = WhileStmt(cond=self.ast.get(ctx.expression()), body=self.ast.get(ctx.block()), ty=NULL)

    def exitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        rn = self.ast.get(ctx.expression()) if ctx.expression() else None
        self.ast[ctx] = ReturnStmt(expr=rn, ty=(self.types.get(ctx.expression()) if ctx.expression() else NULL))

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
            if len(lex) >= 2 and lex[0] == '"' and lex[-1] == '"':
                node = Literal(value=lex[1:-1], ty=STR)
            elif lex.isdigit():
                node = Literal(value=int(lex), ty=INT)
            else:
                # Por si en el futuro agregas literales extra
                node = Literal(value=None, ty=ERROR)

        # Caso 3: arrayLiteral (si decides tiparlo más adelante)
        elif ctx.arrayLiteral():
            # De momento no tipamos arrays aquí; propaga el sub-árbol si luego lo construyes
            node = Literal(value=None, ty=ERROR)

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

    def exitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        if len(ctx.unaryExpr()) == 1:
            sub = ctx.unaryExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.unaryExpr(0), ctx.unaryExpr(1), op)
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        if len(ctx.multiplicativeExpr()) == 1:
            sub = ctx.multiplicativeExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        op = ctx.getChild(1).getText()
        node, ty = self._bin2(ctx.multiplicativeExpr(0), ctx.multiplicativeExpr(1), op)
        self.ast[ctx] = node; self.types[ctx] = ty

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

    def exitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        if len(ctx.equalityExpr()) == 1:
            sub = ctx.equalityExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        node, ty = self._bin2(ctx.equalityExpr(0), ctx.equalityExpr(1), "&&")
        self.ast[ctx] = node; self.types[ctx] = ty

    def exitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        if len(ctx.logicalAndExpr()) == 1:
            sub = ctx.logicalAndExpr(0)
            self.ast[ctx] = self.ast.get(sub); self.types[ctx] = self.types.get(sub, ERROR)
            return
        node, ty = self._bin2(ctx.logicalAndExpr(0), ctx.logicalAndExpr(1), "||")
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
        if len(ctx.suffixOp()) > 0:
            self.errors.append("Accesos/calls/indexación no soportados aún en esta fase.")
            self.ast[ctx] = base_node
            self.types[ctx] = ERROR
        else:
            self.ast[ctx] = base_node
            self.types[ctx] = base_ty

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
                self.errors.append("La condición del operador ternario debe ser boolean")
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

    def _define_symbol(self, name, ty, metadata=None):
        """
        Intenta usar define(Symbol(...)). Si tu tabla fuera antigua (define(name, ty)),
        hace fallback automático.
        """
        try:
            self.table.define(Symbol(name, ty, metadata or {}))
        except TypeError:
            # firma antigua: define(name, ty)
            self.table.define(name, ty)