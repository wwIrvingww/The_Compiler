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
    
    # ==============================================================
    # ||  [2] Ternary Expressions (operaciones en general)
    # ==============================================================
    
    def visitTernaryExpr(self, ctx):
        if ctx.getChildCount() == 1:            
            sub = self.visit(ctx.logicalOrExpr())
            return sub
    
    def visitRelationalExpr(self, ctx):
        if len(ctx.additiveExpr()) == 1:
            sub = self.visit(ctx.additiveExpr(0))
            return sub
        left = self.visit(ctx.additiveExpr(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.additiveExpr(1))
        temp = self._new_temp()
        code = left.code + right.code
        code.append(
            TACOP(
                op = op,
                result=temp,
                arg1=left.place,
                arg2=right.place
            )
        )
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
        temp = self._new_temp()
        code = left.code + right.code
        code.append(
            TACOP(
                op = op,
                result=temp,
                arg1=left.place,
                arg2=right.place
            )
        )
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
        temp = self._new_temp()
        code = left.code + right.code
        code.append(
            TACOP(
                op = "&&",
                result=temp,
                arg1=left.place,
                arg2=right.place
            )
        )
        return IRNode(
            place=temp,
            code=code
        )
        
    def visitLogicalOrExpr(self, ctx):
        if len(ctx.logicalAndExpr()) == 1:
            sub = self.visit(ctx.logicalAndExpr(0))
            return sub
        
        left = self.visit(ctx.logicalAndExpr(0))
        right = self.visit(ctx.logicalAndExpr(1))
        temp = self._new_temp()
        code = left.code + right.code
        code.append(
            TACOP(
                op = "||",
                result=temp,
                arg1=left.place,
                arg2=right.place
            )
        )
        return IRNode(
            place=temp,
            code=code
        )

    def visitMultiplicativeExpr(self, ctx):
        if len(ctx.unaryExpr()) == 1:
            sub = self.visit(ctx.unaryExpr(0))
            return sub
        left = self.visit(ctx.unaryExpr(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.unaryExpr(1))
        
        temp = self._new_temp()
        code = left.code + right.code
        code.append(
            TACOP(
                op = op,
                result=temp,
                arg1=left.place,
                arg2=right.place
            )
        )
        return IRNode(
            place=temp,
            code=code
        )
    
    def visitAdditiveExpr(self, ctx):
        if len(ctx.multiplicativeExpr()) == 1:
            sub = self.visit(ctx.multiplicativeExpr(0))
            return sub
        left = self.visit(ctx.multiplicativeExpr(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.multiplicativeExpr(1))
        temp = self._new_temp()
        code = left.code + right.code
        code.append(
            TACOP(
                op = op,
                result=temp,
                arg1=left.place,
                arg2=right.place
            )
        )
        return IRNode(
            place=temp,
            code=code
        )

    # ==============================================================
    # ||  [3] Primary and Unary
    # ==============================================================
    
    def visitUnaryExpr(self, ctx):
        if ctx.getChildCount() == 1:
            sub1 = self.visit(ctx.primaryExpr())
            return sub1
        op = ctx.getChild(0).getText()
        if op == "-":
            op = "uminus"
        if op == "!":
            op == "not"
        sub = self.visit(ctx.unaryExpr())
        temp = self._new_temp()
        code = sub.code
        code.append(
            TACOP(
                op=op,
                result=temp,
                arg1=sub.place
            )
        )
        return IRNode(
            place = temp,
            code = code
        )
    
    def visitPrimaryExpr(self, ctx):
        place = self._new_temp()
        return IRNode(
            place=place,
            value = ctx.getText(),
            code = [
                TACOP(
                    op="=",
                    result=place,
                    arg1=ctx.getText()
                )
            ]
        )
    
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
            code.append(
                TACOP(
                    op="=",
                    arg1=expr_rslt.place,
                    result=id
                )
            )
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
                code.append(
                    TACOP(
                        op="=",
                        result=id,
                        arg1=rhs.place
                    )
                )
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
        code = [TACOP(
            op="=", arg1=val, result=place
        )]
        return IRNode(place=place, code=code)
    
    
    # ==============================================================
    # ||  [5] Block Statement Flow
    # ==============================================================
    
    def visitBlock(self, ctx):
        self._enter_scope()
        stmts = ctx.statement()
        start = self._new_label()
        end = self._new_label()
        # Append start label to block
        code = [
            TACOP(
                op="label",
                result=start
            )
        ]
        # Navigate statements
        if stmts:
            for s in stmts:
                tem = self.visit(s)
                code = code + tem.code
                
        # Append end to the block
        code.append(
            TACOP(
                op="label",
                result=end
            )
        )
        node= IRBlock(
            start_label= start,
            end_label=end,
            code = code
        )
        return node
                
    # ==============================================================
    # ||  [6] Expression statement
    # ==============================================================
    
    def visitExpressionStatement(self, ctx):
        sub = self.visit(ctx.expression())
        return sub