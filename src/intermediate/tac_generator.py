from parser.CompiscriptVisitor import CompiscriptVisitor
from intermediate.tac_nodes import *
from typing import Optional, List, Dict, Any
from symbol_table import SymbolTable
from intermediate.labels import LabelGenerator
from intermediate.temps import TempAllocator


class TacGenerator(CompiscriptVisitor):
    def __init__(self, symbol_table):
        self.sem_table = symbol_table
        self.tac_table = SymbolTable()
        self.code : List['TACOP'] = []
        self.label_generator = LabelGenerator(prefix="L", start=0)
        self.temp_allocator = TempAllocator(prefix="t", start=0)
        self.const_scopes : List[set] = [set()]

    # ==============================================================
    # ||  [0] Aux Functions
    # ==============================================================
    
    # hooks de TAC
    def _emit_goto(self, lab: str, code: list):
        code.append(TACOP(op="goto", arg1=lab))

    def _emit_if_goto(self, cond_place: str, lab: str, code: list, negated=False):
        if not negated:
            code.append(TACOP(op="if-goto", arg1=cond_place, arg2=lab))
        else:
            t = self._new_temp()
            code.append(TACOP(op="not", arg1=cond_place, result=t))
            code.append(TACOP(op="if-goto", arg1=t, arg2=lab))

    # hooks de llamadas
    # def _emit_call(self, fname: str, arg_places: list[str], code: list) -> str:
    #     for p in arg_places:
    #         code.append(TACOP(op="param", arg1=p)) 
    #     code.append(TACOP(op="call", arg1=fname, arg2=str(len(arg_places))))
    #     t = self._new_temp()
    #     code.append(TACOP(op="=", arg1="ret", result=t))
    #     return t



    ############################### Useful
    def _emit_assign(self, dst: str, src: str, code: list):
        code.append(TACOP(op="=", arg1=src, result=dst))

    
    def _emit_label(self, label:str, code: list):
        code.append(TACOP(op="label", result=label))
    
    def _emit_un(self, op_tok: str, a: str, code: list) -> str:
        op = "uminus" if op_tok == "-" else ("not" if op_tok == "!" else op_tok)
        t = self._new_temp()
        code.append(TACOP(op=op, arg1=a, result=t))
        return t
    
    def _emit_bin(self, op_tok: str, a: str, b: str, code: list) -> str:
        op = op_tok
        t = self._new_temp()
        code.append(TACOP(op=op, arg1=a, arg2=b, result=t))
        return t
    
    def _new_temp(self):
        return self.temp_allocator.new_temp()
            
    def _new_label(self):
        return self.label_generator.new_label()
               
    def _enter_scope(self):
        self.sem_table.enter_scope()
        self.tac_table.enter_scope()
        self.const_scopes.append(set())

    def _exit_scope(self):
        self.sem_table.exit_scope()
        self.tac_table.exit_scope()
        self.const_scopes.pop()

    
    # ==============================================================
    # ||  [1] Flow control
    # ==============================================================
    def visitProgram(self, ctx):
        stmts = ctx.statement()
        code = []
        for st in stmts:
            tem_node = self.visit(st)
            if tem_node:
                code = code + tem_node.code

        self.code = code
        return IRNode(code=code)
    
    def visitStatement(self, ctx):
        child = (
            ctx.variableDeclaration() or    # ✅
            ctx.constantDeclaration() or    # ⏳
            ctx.assignment() or             # ⏳ 1/2 terminado, falta asignacion de propiedades
            ctx.functionDeclaration() or    # 🚧 Not implemented yet
            ctx.classDeclaration() or       # 🚧 Not implemented yet
            ctx.expressionStatement() or    # ⏳ pending
            ctx.printStatement() or         # 💤 Not important
            ctx.block() or                  # ✅
            ctx.ifStatement() or            # 🚧 Not implemented yet
            ctx.whileStatement() or         # 🚧 Not implemented yet
            ctx.doWhileStatement() or       # 🚧 Not implemented yet
            ctx.forStatement() or           # 🚧 Not implemented yet
            ctx.foreachStatement() or       # 🚧 Not implemented yet
            ctx.tryCatchStatement() or      # 🚧 Not implemented yet
            ctx.switchStatement() or        # 🚧 Not implemented yet
            ctx.breakStatement() or         # 🚧 Not implemented yet
            ctx.continueStatement() or      # 🚧 Not implemented yet
            ctx.returnStatement()           # 🚧 Not implemented yet
        )
        return self.visit(child)

    # IF / ELSE
    def visitIfStatement(self, ctx):
        # if '(' expression ')' block ('else' block)?
        cond_node = self.visit(ctx.expression())
        then_node = self.visit(ctx.block(0))
        else_node = self.visit(ctx.block(1)) if len(ctx.block()) > 1 else None

        Ltrue = self._new_label()
        Lfalse = self._new_label() if else_node else None
        Lend  = self._new_label()

        code = []
        code += cond_node.code
        # si la condición es true → Ltrue, else → Lfalse o Lend
        self._emit_if_goto(cond_node.place, Ltrue, code)
        if else_node:
            self._emit_goto(Lfalse, code)
        else:
            self._emit_goto(Lend, code)

        # bloque THEN
        self._emit_label(Ltrue, code)
        code += then_node.code
        self._emit_goto(Lend, code)

        # bloque ELSE
        if else_node:
            self._emit_label(Lfalse, code)
            code += else_node.code
            self._emit_goto(Lend, code)

        # salida
        self._emit_label(Lend, code)
        return IRNode(code=code)

    # WHILE
    def visitWhileStatement(self, ctx):
        # while '(' expression ')' block
        Lcond = self._new_label()
        Lbody = self._new_label()
        Lend  = self._new_label()

        code = []
        self._emit_label(Lcond, code)

        cond = self.visit(ctx.expression())
        code += cond.code
        self._emit_if_goto(cond.place, Lbody, code)
        self._emit_goto(Lend, code)

        self._emit_label(Lbody, code)
        body = self.visit(ctx.block())
        code += body.code
        self._emit_goto(Lcond, code)

        self._emit_label(Lend, code)
        return IRNode(code=code)

    # DO ... WHILE
    def visitDoWhileStatement(self, ctx):
        # do block while '(' expression ')' ';'
        Lbody = self._new_label()
        Lcond = self._new_label()
        Lend  = self._new_label()

        code = []
        self._emit_label(Lbody, code)
        body = self.visit(ctx.block())
        code += body.code

        self._emit_label(Lcond, code)
        cond = self.visit(ctx.expression())
        code += cond.code
        self._emit_if_goto(cond.place, Lbody, code)  # repetir si true
        self._emit_goto(Lend, code)

        self._emit_label(Lend, code)
        return IRNode(code=code)

    # FOR
    def visitForStatement(self, ctx):
        """
        for '(' (variableDeclaration | assignment | ';') expression? ';' expression? ')' block;
        """
        code = []

        # init
        if ctx.variableDeclaration():
            init_node = self.visit(ctx.variableDeclaration())
            if init_node: code += init_node.code
        elif ctx.assignment():
            init_node = self.visit(ctx.assignment())
            if init_node: code += init_node.code

        # cond y update
        cond_node, upd_node = None, None
        if ctx.expression():
            exprs = ctx.expression()
            if isinstance(exprs, list):
                if len(exprs) >= 1:
                    cond_node = self.visit(exprs[0])
                if len(exprs) >= 2:
                    upd_node  = self.visit(exprs[1])
            else:
                cond_node = self.visit(exprs)

        Lcond = self._new_label()
        Lbody = self._new_label()
        Lstep = self._new_label()
        Lend  = self._new_label()

        # condición
        self._emit_label(Lcond, code)
        if cond_node is not None:
            code += cond_node.code
            self._emit_if_goto(cond_node.place, Lbody, code)
            self._emit_goto(Lend, code)
        else:
            self._emit_goto(Lbody, code)

        # cuerpo
        self._emit_label(Lbody, code)
        body_node = self.visit(ctx.block())
        code += body_node.code
        self._emit_goto(Lstep, code)

        # update
        self._emit_label(Lstep, code)
        if upd_node is not None:
            code += upd_node.code
            # ⚠️ importante: asegurar que el resultado vuelva a la var
            if hasattr(upd_node, "place") and upd_node.place:
                target = ctx.expression()[1].getText().split("=")[0].strip()
                self._emit_assign(dst=target, src=upd_node.place, code=code)
        self._emit_goto(Lcond, code)

        # fin
        self._emit_label(Lend, code)
        return IRNode(code=code)

    # RETURN
    def visitReturnStatement(self, ctx):
        code = []
        if ctx.expression():
            val = self.visit(ctx.expression())
            code += val.code
            code.append(TACOP(op="return", arg1=val.place))
        else:
            code.append(TACOP(op="return"))
        return IRNode(code=code)


    # ==============================================================
    # ||  [2] Ternary Expressions (operaciones en general)
    # ==============================================================
    
    def visitTernaryExpr(self, ctx):
        if ctx.getChildCount() == 1:            
            sub = self.visit(ctx.logicalOrExpr())
            return sub
    
    def visitRelationalExpr(self, ctx):
        if len(ctx.additiveExpr()) == 1:
            # Unary case
            sub = self.visit(ctx.additiveExpr(0))
            return sub
        # Binary case
        left = self.visit(ctx.additiveExpr(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.additiveExpr(1))
        
        code = left.code + right.code
        temp = self._emit_bin(op, left.place, right.place, code)
        
        return IRNode(
            place=temp,
            code=code
        )
    
    def visitEqualityExpr(self, ctx):
        if len(ctx.relationalExpr()) == 1:
            sub = self.visit(ctx.relationalExpr(0))
            return sub
        left = self.visit(ctx.relationalExpr(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.relationalExpr(1))
        
        code = left.code + right.code
        temp = self._emit_bin(op, left.place, right.place, code)
        
        return IRNode(
            place=temp,
            code=code
        )
    
    def visitLogicalAndExpr(self, ctx):
        if len(ctx.equalityExpr()) == 1:
            sub = self.visit(ctx.equalityExpr(0))
            return sub
        left = self.visit(ctx.equalityExpr(0))
        right = self.visit(ctx.equalityExpr(1))
        
        code = left.code + right.code
        temp = self._emit_bin("&&", left.place, right.place, code)
        
        return IRNode(
            place=temp,
            code=code
        )
        
    def visitLogicalOrExpr(self, ctx):
        # logicalAndExpr ( '||' logicalAndExpr )*
        n = len(ctx.logicalAndExpr())
        node0 = self.visit(ctx.logicalAndExpr(0))
        acc_place = node0.place
        code = node0.code[:]
        for i in range(1, n):
            rhs = self.visit(ctx.logicalAndExpr(i))
            code += rhs.code
            acc_place = self._emit_bin("||", acc_place, rhs.place, code)
        return IRNode(place=acc_place, code=code)

    def visitLogicalAndExpr(self, ctx):
        n = len(ctx.equalityExpr())
        node0 = self.visit(ctx.equalityExpr(0))
        acc_place = node0.place
        code = node0.code[:]
        for i in range(1, n):
            rhs = self.visit(ctx.equalityExpr(i))
            code += rhs.code
            acc_place = self._emit_bin("&&", acc_place, rhs.place, code)
        return IRNode(place=acc_place, code=code)

    def visitEqualityExpr(self, ctx):
        n = len(ctx.relationalExpr())
        node0 = self.visit(ctx.relationalExpr(0))
        acc_place = node0.place
        code = node0.code[:]
        idx = 1
        childi = 1
        while childi < ctx.getChildCount():
            op = ctx.getChild(childi).getText()    # '==' | '!='
            rhs = self.visit(ctx.relationalExpr(idx))
            code += rhs.code
            acc_place = self._emit_bin(op, acc_place, rhs.place, code)
            idx += 1; childi += 2
        return IRNode(place=acc_place, code=code)

    def visitRelationalExpr(self, ctx):
        n = len(ctx.additiveExpr())
        node0 = self.visit(ctx.additiveExpr(0))
        acc_place = node0.place
        code = node0.code[:]
        idx = 1
        childi = 1
        while childi < ctx.getChildCount():
            op = ctx.getChild(childi).getText()    # < <= > >=
            rhs = self.visit(ctx.additiveExpr(idx))
            code += rhs.code
            acc_place = self._emit_bin(op, acc_place, rhs.place, code)
            idx += 1; childi += 2
        return IRNode(place=acc_place, code=code)

    def visitAdditiveExpr(self, ctx):
        n = len(ctx.multiplicativeExpr())
        node0 = self.visit(ctx.multiplicativeExpr(0))
        acc_place = node0.place
        code = node0.code[:]
        idx = 1
        childi = 1
        while childi < ctx.getChildCount():
            op = ctx.getChild(childi).getText()    # + | -
            rhs = self.visit(ctx.multiplicativeExpr(idx))
            code += rhs.code
            acc_place = self._emit_bin(op, acc_place, rhs.place, code)
            idx += 1; childi += 2
        return IRNode(place=acc_place, code=code)

    def visitMultiplicativeExpr(self, ctx):
        n = len(ctx.unaryExpr())
        node0 = self.visit(ctx.unaryExpr(0))
        acc_place = node0.place
        code = node0.code[:]
        idx = 1
        childi = 1
        while childi < ctx.getChildCount():
            op = ctx.getChild(childi).getText()    # * / %
            rhs = self.visit(ctx.unaryExpr(idx))
            code += rhs.code
            acc_place = self._emit_bin(op, acc_place, rhs.place, code)
            idx += 1; childi += 2
        return IRNode(place=acc_place, code=code)

    # ==============================================================
    # ||  [3] Primary and Unary
    # ==============================================================
    
    def visitUnaryExpr(self, ctx):
        if ctx.getChildCount() == 1:
            sub1 = self.visit(ctx.primaryExpr())
            return sub1
        
        sub = self.visit(ctx.unaryExpr())
        op = ctx.getChild(0).getText()
        
        code = sub.code
        temp = self._emit_un(op, sub.place, code)
        
        return IRNode(
            place = temp,
            code = code
        )
    
    def visitPrimaryExpr(self, ctx):
        # primaryExpr: literalExpr | leftHandSide | '(' expression ')'
        if ctx.literalExpr():
            place = self._new_temp()
            val = ctx.literalExpr().getText()
            code = []
            self._emit_assign(dst=place, src=val, code=code)
            return IRNode(place=place, value=val, code=code)

        if ctx.leftHandSide():
            sub = self.visit(ctx.leftHandSide())
            if sub is None:
                # fallback ultra-conservador: usar el texto
                src = ctx.leftHandSide().getText()
                place = self._new_temp()
                code = []
                self._emit_assign(dst=place, src=src, code=code)
                return IRNode(place=place, code=code)
            # patrón: t = <place>
            place = self._new_temp()
            code = sub.code[:] if sub.code else []
            self._emit_assign(dst=place, src=sub.place, code=code)
            return IRNode(place=place, code=code)

        # '(' expression ')'
        inner = self.visit(ctx.expression())
        if inner is None:
            # fallback: asignar el texto (no ideal, pero evita crash)
            place = self._new_temp()
            code = []
            self._emit_assign(dst=place, src=ctx.getText(), code=code)
            return IRNode(place=place, code=code)
        # devolvemos la subexpresión directamente
        return inner
    
    # ==============================================================
    # ||  [4] Variable Declaration flow
    # ==============================================================
    
    def visitVariableDeclaration(self, ctx):
        id = ctx.Identifier().getText()
        init = ctx.initializer()
        node = None
        ty = None
        sem_info = self.sem_table.lookup(id)
        if sem_info:
            ty = sem_info.type
        
        if init:
            expr_rslt = self.visit(init.expression())
            code = expr_rslt.code
            
            self._emit_assign(dst=id, src=expr_rslt.place, code=code)
  
            node = IRAssign(
                place=id,
                name=id,
                code = code
            )
        self.tac_table.define(
            symbol_or_name=id,
            sym_type=ty,
            metadata=self.const_scopes[-1]
            
        )
        return node
        
    def visitAssignment(self, ctx):
        case = "assignment" if ctx.getChildCount() == 4 else "prop_assign"
        node = None
        if case == "assignment":
            id = ctx.Identifier().getText()
            if id:
                tac_sym = self.tac_table.lookup(id)
                if not tac_sym:
                    raise("ERROR - variable non existent on symbol table")
                
                rhs = self.visit(ctx.expression(0))
                code = rhs.code
                self._emit_assign(dst=id, src=rhs.place, code=code)
                
                node = IRAssign(
                    place=id,
                    name=id,
                    code=code
                )
        else:
            # TODO property asignment
            pass
        return node
                
    def visitLiteralExpr(self, ctx):
        val = ctx.getText()
        place = self._new_temp()
        code = []
        self._emit_assign(dst=place, src=val, code=code)

        return IRNode(place=place, code=code)
    
    
    # ==============================================================
    # ||  [5] Block Statement Flow
    # ==============================================================
    
    def visitBlock(self, ctx):
        """
        Bloques { ... } sin labels automáticos.
        - Mantiene enter/exit de scope para la tabla de símbolos TAC.
        - Concatena el código de sus sentencias en orden.
        - No emite 'label' salvo que las sentencias internas lo hagan.
        """
        self._enter_scope()
        code = []
        for s in ctx.statement():
            node = self.visit(s)
            if node and getattr(node, "code", None):
                code += node.code
        self._exit_scope()
        # Para el resto del pipeline solo importa .code; devolvemos un IRNode básico.
        return IRNode(code=code)
       
    # ==============================================================
    # ||  [6] Expression statement
    # ==============================================================
    
    def visitExpressionStatement(self, ctx):
        sub = self.visit(ctx.expression())
        return sub
    # ==============================================================
    # ||  [7] leftHandSide and primaryAtom
    # ==============================================================
    def visitLeftHandSide(self, ctx):
        """
        leftHandSide: primaryAtom (suffixOp)*;
        Para ahora: resolvemos el 'primaryAtom' básico (identificadores).
        Si hay sufijos, de momento no los transformamos (queda TODO),
        pero devolvemos al menos un IRNode válido para no crashear.
        """
        base = self.visit(ctx.primaryAtom())
        if base is None:
            # fallback ultra-conservador
            name = ctx.getText()
            return IRNode(place=name, code=[])
        # Si hubiera sufijos (., (), []), aquí es donde luego los encadenarás.
        # Por ahora devolvemos el base (identificador simple).
        return base
    def visitIdentifierExpr(self, ctx):
        """
        primaryAtom: Identifier  # IdentifierExpr
        Para TAC, un identificador puede ser usado como 'place' directo.
        No generamos código aquí; el que lo consuma decide si hace 't = id'.
        """
        name = ctx.Identifier().getText()
        return IRNode(place=name, code=[])
