from parser.CompiscriptVisitor import CompiscriptVisitor
from intermediate.tac_nodes import *
from typing import Optional, List, Dict, Any
from symbol_table import SymbolTable
from intermediate.labels import LabelGenerator


class TacGenerator(CompiscriptVisitor):
    def __init__(self, symbol_table):
        self.sem_table = symbol_table
        self.tac_table = SymbolTable()
        self.code : List['TACOP'] = []
        self.label_generator = LabelGenerator(prefix="t", start=0)
        self.const_scopes : List[set] = [set()]

    # ----- Aux functions ------ #
    def _new_temp(self):
        return self.label_generator.new_label()
    
    # ---- Flow ----- #
    def visitExpression(self, ctx):
        sub = ctx.assignmentExpr
        return sub
    
    def visitExprNoAssign(self, ctx):
        sub = self.visit(ctx.logicalOrExpr())
        return sub
    # ----- Ternary/operations ----- #
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
        print(left)
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.multiplicativeExpr(1))
        print(right)
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

    # ----- Primary and Unary ----- #
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
    
    # ----- Literals ------ #
    
    def visitLiteralExpr(self, ctx):
        val = ctx.getText()
        place = self._new_temp()
        code = [TACOP(
            op="=", arg1=val, result=place
        )]
        return IRNode(place=place, code=code)
    
    def visitVariableDeclaration(self, ctx):
        id = ctx.Identifier().getText()
        init = ctx.initializer()
        node = None
        
        if init:
            print("here")
            expr_rslt = self.visit(init.expression())
            temporal = self._new_temp()
            node = IRAssign(
                place=temporal,
                name=id,
                code = [
                    *expr_rslt.code,
                        TACOP(
                        op="=",
                        arg1=expr_rslt.place,
                        result=id
                    )
                ]
            )  
            
            
        
    
        