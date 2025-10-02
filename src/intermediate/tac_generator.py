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
        if len(ctx.logicalAndExpr()) == 1:
            sub = self.visit(ctx.logicalAndExpr(0))
            return sub
        
        left = self.visit(ctx.logicalAndExpr(0))
        right = self.visit(ctx.logicalAndExpr(1))
        
        code = left.code + right.code
        temp = self._emit_bin("||", left.place, right.place, code)
        
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
        
        code = left.code + right.code
        temp = self._emit_bin(op, left.place, right.place, code)
        
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
        
        code = left.code + right.code
        temp = self._emit_bin(op, left.place, right.place, code)
        
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
        
        sub = self.visit(ctx.unaryExpr())
        op = ctx.getChild(0).getText()
        
        code = sub.code
        temp = self._emit_un(op, sub.place, code)
        
        return IRNode(
            place = temp,
            code = code
        )
    
    def visitPrimaryExpr(self, ctx):
        place = self._new_temp()
        val = ctx.getText()
        
        code = []
        self._emit_assign(dst=place, src=val, code=code)
        
        return IRNode(
            place=place,
            value = val,
            code = code
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
        self._enter_scope()
        stmts = ctx.statement()
        
        start_label = self._new_label()
        end_label = self._new_label()
        code = []
        # Append start label to block
        self._emit_label(start_label, code)
        
        # Navigate statements
        if stmts:
            for s in stmts:
                tem = self.visit(s)
                code = code + tem.code
                
        # Append end to the block
        self._emit_label(end_label, code)
        node= IRBlock(
            start_label= start_label,
            end_label=end_label,
            code = code
        )
        return node
                
    # ==============================================================
    # ||  [6] Expression statement
    # ==============================================================
    
    def visitExpressionStatement(self, ctx):
        sub = self.visit(ctx.expression())
        return sub