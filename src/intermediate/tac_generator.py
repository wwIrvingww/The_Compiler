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

    # Hooks de localización
    def _place_of_identifier(self, id_text: str) -> str:
        # Uso a futuro: usa self.sem_table + runtime_layout para mapear a [fp+off] o registro.
        return id_text

    def _place_of_property(self, obj_place: str, prop_name: str) -> str:
        return f"{obj_place}.{prop_name}"

    def _place_of_index(self, base_place: str, index_place: str) -> str:
        # Uso a futuro: load/store con desplazamiento.
        return f"{base_place}[{index_place}]"

    # hooks de TAC
    def _emit_assign(self, dst: str, src: str, code: list):
        code.append(TACOP(op="=", arg1=src, result=dst))

    def _emit_bin(self, op_tok: str, a: str, b: str, code: list) -> str:
        binmap = {
            "+":"+", "-":"-", "*":"*", "/":"/", "%":"%",
            "==":"==", "!=":"!=", "<":"<", "<=":"<=", ">":">", ">=":">=",
            "&&":"&&", "||":"||",
        }
        op = binmap[op_tok]
        t = self._new_temp()
        code.append(TACOP(op=op, arg1=a, arg2=b, result=t))
        return t

    def _emit_un(self, op_tok: str, a: str, code: list) -> str:
        op = "uminus" if op_tok == "-" else ("not" if op_tok == "!" else op_tok)
        t = self._new_temp()
        code.append(TACOP(op=op, arg1=a, result=t))
        return t

    # hooks de control de flujo
    def _emit_label(self, lab: str, code: list):
        code.append(TACOP(op="label", result=lab))

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
    def _emit_call(self, fname: str, arg_places: list[str], code: list) -> str:
        for p in arg_places:
            code.append(TACOP(op="param", arg1=p)) 
        code.append(TACOP(op="call", arg1=fname, arg2=str(len(arg_places))))
        t = self._new_temp()
        code.append(TACOP(op="=", arg1="ret", result=t))
        return t

    # hook para mostrar el tac como lista y evitar errores
    def get_code(self) -> list:
        return list(self.code)

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
            
            
        
    
        