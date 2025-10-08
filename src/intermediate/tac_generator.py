from ast_nodes import is_list
from parser.CompiscriptVisitor import CompiscriptVisitor
from intermediate.tac_nodes import *
from typing import Optional, List, Dict, Any
from symbol_table import SymbolTable
from intermediate.labels import LabelGenerator
from intermediate.temps import TempAllocator
from symbol_table.runtime_layout import FrameManager

class TacGenerator(CompiscriptVisitor):
    def __init__(self, symbol_table):
        self.sem_table = symbol_table
        self.tac_table = SymbolTable()
        self.frame_manager = FrameManager()  # 🔹 nuevo
        self.code: List['TACOP'] = []
        self.label_generator = LabelGenerator(prefix="L", start=0)
        self.temp_allocator = TempAllocator(prefix="t", start=0)
        self.const_scopes: List[set] = [set()]
        self.break_stack: List[str] = []
        self.continue_stack: List[str] = []
        self.current_class: Optional[str] = None

    # ==============================================================
    # ||  [0] Aux Functions
    # ==============================================================
    def _detect_type(self, txt: str):
        text = txt.strip()
        if text.lower() in ("true", "false"):
            return ("boolean", 1)
        try:
            float(text)
            return ("numeric", 4)
        except ValueError:
            pass
        
        if text.startswith('[') and text.endswith(']'):
            return ("array", 4)
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            return ("string", 4)
        
        return ("numeric", 4)
        
    def _emit_array_offset_store(
            self,
            arr_tem: str, 
            src: str,
            offset: int, 
            index : str, 
            code: list,
        ):
        effective_address = None
        comment = None
        if index == 0:
            effective_address = arr_tem
            comment = f"len({arr_tem}) = {src}"
        else:
            offset_bytes = self._emit_bin(op_tok="*",a=index, b=offset, code=code)
            effective_address = self._emit_bin(op_tok="+", a=arr_tem, b=offset_bytes, code=code)
            comment = f"{arr_tem}[{index}] = {src}"
        code.append(
            TACOP(
                op="store",
                result=effective_address,
                arg1=src,
                comment=comment
            )
        )
        
    def _emit_array_offset_load(
        self,
        arr_tem: str, 
        offset: int, 
        index : str, 
        is_len: bool,
        code: list,
        ):
        t0 = index
        if not is_len:
            t0 = self._emit_bin(op_tok="+",a=index, b=1, code=code)
        offset_bytes = self._emit_bin(op_tok="*",a=t0, b=offset, code=code)
        effective_address = self._emit_bin(op_tok="+", a=arr_tem, b=offset_bytes, code=code)
        t = self._new_temp()
        code.append(
            TACOP(
                op="load",
                arg1=effective_address,
                result=t
            )
        )
        return t
        
    
    ## Array emits
    def _emit_array_idx_store(self, arr_tem :str, val: str, idx: str, code: list):
        code.append(TACOP(
            op="STORE_IDX",
            arg1=idx,
            arg2=val,
            result=arr_tem
        ))
    
    def _emit_array_idx_load(self, arr_tem :str, idx: str, code: list):
        t = self._new_temp()
        code.append(TACOP(
            op="LOAD_IDX",
            arg1=arr_tem,
            arg2=idx,
            result=t
        ))
        return t
    
    def _emit_create_array(self, id :str, code):
        if id:
            code.append(
                TACOP(
                    op="CREATE_ARRAY",
                    result=id
                )
            )
            return None
        else:
            t = self._new_temp()
            code.append(
                TACOP(
                    op="CREATE_ARRAY",
                    result=t
                )
            )
            return t

    
    def _emit_array_push(self, arr_temp: str, val_temp: str, code: list):
        code.append(
            TACOP(
                op="PUSH_TO_ARRAY",
                result=arr_temp,
                arg1=val_temp
            )
        )
    
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
    
    def _emit_class_begin(self, cls: str, base: Optional[str], code: list):
        code.append(TACOP(op="class", arg1=cls, arg2=(base or "-")))

    def _emit_class_attr(self, cls: str, name: str, ty_name: Optional[str], code: list):
        code.append(TACOP(op="attr", arg1=cls, arg2=name, result=(ty_name or "-")))

    def _emit_class_method(self, cls: str, mname: str, entry_label: str, code: list):
        code.append(TACOP(op="method", arg1=cls, arg2=mname, result=entry_label))

    def _emit_class_end(self, cls: str, code: list):
        code.append(TACOP(op="endclass", arg1=cls))
    
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

    def get_code(self):
        return list(self.code)
    
    def _func_labels(self, name: str):
        fq = f"{self.current_class}.{name}" if self.current_class else name
        return (f"func_{fq}_entry", f"func_{fq}_exit")
    
    def _emit_store_prop(self, obj_place: str, prop_name: str, src_place: str, code: list):
        # STORE_PROP: arg1 = objeto, arg2 = nombre_prop, result = valor
        code.append(TACOP(op="STORE_PROP", arg1=obj_place, arg2=prop_name, result=src_place))

    @staticmethod
    def peephole(code: List[TACOP]) -> List[TACOP]:
        """
        Reglas seguras (order-independent) pensadas para MIPS:
          1) Eliminar asignaciones no-op:  x = x
          2a) Simplificar if-goto con constantes literales:
              - if true goto L  -> goto L
              - if false goto L -> nop
          2b) Simplificar patrón inmediato de temp booleano:
              - t = true;  if t goto L  -> goto L
              - t = false; if t goto L  -> nop
              (sin instrucciones entre ambas)
          3) Eliminar 'goto' hacia la etiqueta inmediata siguiente:
              - goto L; label L -> elimina el goto
          4) (Opcional) Fusionar labels consecutivos (conservador, sin renombrar)
        """
        out: List[TACOP] = []

        # ---- pass 1: x=x y if-goto(literal) ----
        for ins in code:
            op = ins.op
            # 1) x = x
            if op == "=" and ins.result is not None and ins.arg1 is not None:
                if ins.result == ins.arg1:
                    # no-op
                    continue

            # 2a) if-goto con literal
            if op == "if-goto" and ins.arg1 is not None:
                cond = ins.arg1.strip()
                if cond in ("true", "True"):
                    out.append(TACOP(op="goto", arg1=ins.arg2))
                    continue
                if cond in ("false", "False"):
                    # nop
                    continue

            out.append(ins)

        code = out
        out = []

        # ---- pass 2: patrón t=bool; if t goto L (inmediato) ----
        i = 0
        while i < len(code):
            cur = code[i]
            if (cur.op == "=" and cur.result and cur.arg1 in ("true", "True", "false", "False")
                and i + 1 < len(code) and code[i+1].op == "if-goto"
                and code[i+1].arg1 == cur.result):
                # Simplificar par
                if cur.arg1.lower() == "true":
                    out.append(TACOP(op="goto", arg1=code[i+1].arg2))
                # si es false, no se añade nada (nop)
                i += 2
                continue

            out.append(cur)
            i += 1

        code = out
        out = []

        # ---- pass 3: elimina 'goto' hacia label inmediata ----
        i = 0
        while i < len(code):
            cur = code[i]
            if cur.op == "goto" and i + 1 < len(code) and code[i+1].op == "label":
                tgt = cur.arg1 or cur.result
                nxt_lab = code[i+1].result or code[i+1].arg1
                if tgt == nxt_lab:
                    # saltamos el goto, dejamos el label
                    out.append(code[i+1])
                    i += 2
                    continue
            out.append(cur)
            i += 1

        # ---- pass 4: borrar instrucciones inalcanzables tras un goto hasta el próximo label ----
        out = []
        i = 0
        while i < len(code):
            ins = code[i]
            out.append(ins)
            if ins.op == "goto":
                # saltar todo hasta el próximo label
                j = i + 1
                while j < len(code) and code[j].op != "label":
                    j += 1
                i = j
                continue
            i += 1

        code = out
        out = []

        # ---- pass 5: labels consecutivos (conservador) ----
        prev_was_label = False
        for ins in code:
            if ins.op == "label" and prev_was_label:
                # conservamos ambos (no renombramos ni reescribimos saltos)
                pass
            prev_was_label = (ins.op == "label")
            out.append(ins)

        return out

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
        
        code = self.peephole(code)
        self.code = code
        self.dump_runtime_info()
        return IRNode(code=code)
    
    def visitStatement(self, ctx):
        child = (
            ctx.variableDeclaration() or    # ✅
            ctx.constantDeclaration() or    # ✅
            ctx.assignment() or             # ✅
            ctx.functionDeclaration() or    # ✅ 
            ctx.classDeclaration() or       # ✅
            ctx.expressionStatement() or    # ⏳ pending
            ctx.printStatement() or         # ✅ Not important
            ctx.block() or                  # ✅
            ctx.ifStatement() or            # ✅ 
            ctx.whileStatement() or         # ✅
            ctx.doWhileStatement() or       # ✅
            ctx.forStatement() or           # ✅
            ctx.foreachStatement() or       # ✅
            ctx.tryCatchStatement() or      # 🚧 Not implemented yet
            ctx.switchStatement() or        # ✅
            ctx.breakStatement() or         # ✅
            ctx.continueStatement() or      # ✅
            ctx.returnStatement()           # ✅
        )
        return self.visit(child)

    # ==============================================================
    # ||  [2] Conditional Expressions (if-else, switch)
    # ==============================================================
    
    # IF-ELSE
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


    # SWITCH
    def visitSwitchStatement(self, ctx):
        """
        switch '(' expression ')' '{' switchCase* defaultCase? '}'
        """
        scrut = self.visit(ctx.expression())
        code = []
        if scrut and scrut.code: code += scrut.code

        cases = ctx.switchCase() or []
        has_default = ctx.defaultCase() is not None

        Lend = self._new_label()
        Lcases = [self._new_label() for _ in cases]
        Ldefault = self._new_label() if has_default else Lend

        # saltos a cada case
        for i, cctx in enumerate(cases):
            cexpr = self.visit(cctx.expression())
            if cexpr and cexpr.code: code += cexpr.code
            tcmp = self._emit_bin("==", scrut.place, cexpr.place, code)
            self._emit_if_goto(tcmp, Lcases[i], code)

        # si no match, ir a default o fin
        self._emit_goto(Ldefault, code)

        # emitir cada case
        for i, cctx in enumerate(cases):
            self._emit_label(Lcases[i], code)
            # statements del case
            for s in cctx.statement():
                n = self.visit(s)
                if n and n.code: code += n.code
            # tras un case, por defecto caemos al end (si quieres 'fallthrough', no pongas este goto)
            self._emit_goto(Lend, code)

        # default
        if has_default:
            self._emit_label(Ldefault, code)
            for s in ctx.defaultCase().statement():
                n = self.visit(s)
                if n and n.code: code += n.code

        self._emit_label(Lend, code)
        return IRNode(code=code)
    
    # ==============================================================
    # ||  [3] Loops (while, dowhile, for, foreach)
    # ==============================================================
    
    # WHILE
    def visitWhileStatement(self, ctx):
        # while '(' expression ')' block
        Lcond = self._new_label()
        Lbody = self._new_label()
        Lend  = self._new_label()

        code = []
        # gestionar break/continue
        self.continue_stack.append(Lcond)
        self.break_stack.append(Lend)

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
        # pop stacks
        self.continue_stack.pop()
        self.break_stack.pop()

        return IRNode(code=code)

    # DO ... WHILE
    def visitDoWhileStatement(self, ctx):
        # do block while '(' expression ')' ';'
        Lbody = self._new_label()
        Lcond = self._new_label()
        Lend  = self._new_label()

        code = []
        # en do..while, continue debe saltar a Lcond (chequear condición)
        self.continue_stack.append(Lcond)
        self.break_stack.append(Lend)

        self._emit_label(Lbody, code)
        body = self.visit(ctx.block())
        code += body.code

        self._emit_label(Lcond, code)
        cond = self.visit(ctx.expression())
        code += cond.code
        self._emit_if_goto(cond.place, Lbody, code)  # repetir si true
        self._emit_goto(Lend, code)

        self._emit_label(Lend, code)

        self.continue_stack.pop()
        self.break_stack.pop()

        return IRNode(code=code)

    # FOR
    def visitForStatement(self, ctx):
        """
        for '(' (variableDeclaration | assignment | ';') expression? ';' expression? ')' block;
        """
        code = []

        # init
        if ctx.variableDeclaration():
            init_node = self.visit(ctx.variableDeclaration());  code += init_node.code if init_node else []
        elif ctx.assignment():
            init_node = self.visit(ctx.assignment());           code += init_node.code if init_node else []

        # cond y update
        cond_node, upd_node = None, None
        if ctx.expression():
            exprs = ctx.expression()
            if isinstance(exprs, list):
                if len(exprs) >= 1: cond_node = self.visit(exprs[0])
                if len(exprs) >= 2: upd_node  = self.visit(exprs[1])
            else:
                cond_node = self.visit(exprs)

        Lcond = self._new_label()
        Lbody = self._new_label()
        Lstep = self._new_label()
        Lend  = self._new_label()

        # gestionar break/continue
        self.continue_stack.append(Lstep)
        self.break_stack.append(Lend)

        # condición
        self._emit_label(Lcond, code)
        if cond_node is not None:
            code += cond_node.code
            self._emit_if_goto(cond_node.place, Lbody, code)
            self._emit_goto(Lend, code)
        else:
            self._emit_goto(Lbody, code)

        # body
        self._emit_label(Lbody, code)
        body_node = self.visit(ctx.block())
        code += body_node.code
        self._emit_goto(Lstep, code)

        # step
        self._emit_label(Lstep, code)
        if upd_node is not None:
            code += upd_node.code
        self._emit_goto(Lcond, code)

        # fin
        self._emit_label(Lend, code)
        # en este mejor ponemos continue hacia el step, no a la condición
        self.continue_stack.pop()
        self.break_stack.pop()

        return IRNode(code=code)

    # FOREACH
    def visitForeachStatement(self, ctx):
        item_name = ctx.Identifier().getText()
        arr_node  = self.visit(ctx.expression())

        t_i   = self._new_temp()   # índice
        t_n   = self._new_temp()   # longitud
        Lcond = self._new_label()
        Lbody = self._new_label()
        Lstep = self._new_label()  #  bloque step
        Lend  = self._new_label()

        code = []
        # __i = 0
        self._emit_assign(dst=t_i, src="0", code=code)
        # __n = len(arr)
        if arr_node and arr_node.code: code += arr_node.code
        code.append(TACOP(op="len", arg1=arr_node.place, result=t_n))

        # gestionar break/continue
        self.continue_stack.append(Lstep)   
        self.break_stack.append(Lend)

        # while (__i < __n)
        self._emit_label(Lcond, code)
        t_cmp = self._emit_bin("<", t_i, t_n, code)
        self._emit_if_goto(t_cmp, Lbody, code)
        self._emit_goto(Lend, code)

        # body: item = arr[__i];
        self._emit_label(Lbody, code)
        t_item = self._new_temp()
        code.append(TACOP(op="getidx", arg1=arr_node.place, arg2=t_i, result=t_item))
        self._emit_assign(dst=item_name, src=t_item, code=code)

        # cuerpo foreach
        body = self.visit(ctx.block())
        if body and body.code: code += body.code

        # step: __i = __i + 1
        self._emit_label(Lstep, code)
        t_next = self._emit_bin("+", t_i, "1", code)
        self._emit_assign(dst=t_i, src=t_next, code=code)
        self._emit_goto(Lcond, code)

        self._emit_label(Lend, code)

        self.continue_stack.pop()
        self.break_stack.pop()

        return IRNode(code=code)

    
    # ==============================================================
    # ||  [3]  Flow control (break, return, continue)
    # ==============================================================
    
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

    # BREAK
    def visitBreakStatement(self, ctx):
        # Salta al fin del lazo actual
        if not self.break_stack:
            return IRNode(code=[])  # semántica ya reporta error; acá evita crashear
        code = []
        self._emit_goto(self.break_stack[-1], code)
        return IRNode(code=code)

    # CONTINUE
    def visitContinueStatement(self, ctx):
        # Salta al "siguiente ciclo" (condición o step, según el lazo)
        if not self.continue_stack:
            return IRNode(code=[])
        code = []
        self._emit_goto(self.continue_stack[-1], code)
        return IRNode(code=code)

    # ==============================================================
    # ||  [4] Ternary Expressions (operaciones en general)
    # ==============================================================
    
    def visitTernaryExpr(self, ctx):
        # conditionalExpr: logicalOrExpr ('?' expression ':' expression)?
        if ctx.getChildCount() == 1:
            return self.visit(ctx.logicalOrExpr())

        # Hay ternario
        cond_node = self.visit(ctx.logicalOrExpr())
        then_node = self.visit(ctx.expression(0))
        else_node = self.visit(ctx.expression(1))

        Lthen = self._new_label()
        Lelse = self._new_label()
        Lend  = self._new_label()

        # Usamos un temp para el "valor" del ternario (aunque tu gramática lo use como statement,
        # así también queda correcto si alguien lo usa en una expresión).
        result = self._new_temp()
        code = []

        # cond
        if cond_node and cond_node.code: code += cond_node.code
        self._emit_if_goto(cond_node.place, Lthen, code)
        self._emit_goto(Lelse, code)

        # then
        self._emit_label(Lthen, code)
        if then_node and then_node.code: code += then_node.code
        # si el then_node produce un valor, lo guardamos; si no, lo dejamos como está
        if getattr(then_node, "place", None) is not None:
            self._emit_assign(dst=result, src=then_node.place, code=code)
        self._emit_goto(Lend, code)

        # else
        self._emit_label(Lelse, code)
        if else_node and else_node.code: code += else_node.code
        if getattr(else_node, "place", None) is not None:
            self._emit_assign(dst=result, src=else_node.place, code=code)

        # end
        self._emit_label(Lend, code)
        return IRNode(place=result, code=code)
    
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
    # ||  [5] Declarations
    # ==============================================================

    # Constant Declaration
    def visitConstantDeclaration(self, ctx):
        """
        const Identifier typeAnnotation? '=' expression ';'
        """
        name = ctx.Identifier().getText()
        expr_node = self.visit(ctx.expression())
        code = []
        if expr_node and expr_node.code:
            code += expr_node.code
        # asignación
        self._emit_assign(dst=name, src=expr_node.place, code=code)

        # registra símbolo TAC (marcar const en metadata actual del scope)
        meta = dict(self.const_scopes[-1]) if isinstance(self.const_scopes[-1], dict) else {"const": True}
        if isinstance(self.const_scopes[-1], set):
            meta = {"const": True}
            self.const_scopes[-1].add(name)
        self.tac_table.define(symbol_or_name=name, sym_type=None, metadata=meta)

        return IRNode(code=code)

    # Print Statement
    def visitPrintStatement(self, ctx):
        """
        print '(' expression ')' ';'
        """
        val = self.visit(ctx.expression())
        code = []
        if val and val.code:
            code += val.code
        code.append(TACOP(op="print", arg1=val.place))
        return IRNode(code=code)
    
    # Function Declaration
    def visitFunctionDeclaration(self, ctx):
        """
        function Identifier '(' parameters? ')' (':' type)? block;
        """
        fname = ctx.Identifier().getText()
        Lentry, Lexit = self._func_labels(fname)

        # Abrir scope TAC y registrar parámetros como símbolos
        self._enter_scope()
        if ctx.parameters():
            for pctx in ctx.parameters().parameter():
                pname = pctx.Identifier().getText()
                # en TAC basta con darlos de alta (tipo opcional)
                self.tac_table.define(symbol_or_name=pname, sym_type=None, metadata={})

        # Cuerpo
        # body = self.visit(ctx.block())

        code = []
        self._emit_label(Lentry, code)
        body_ir = self.visit(ctx.block())
        if body_ir and body_ir.code:
            code += body_ir.code
        self._emit_label(Lexit, code)

        self._exit_scope()
        return IRNode(place=None, code=code)

    # ==============================================================
    # ||  [6] Primary and Unary
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
            sub = self.visit(ctx.literalExpr())
            return sub

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
    # ||  [7] Variable Declaration flow
    # ==============================================================
    
    def visitVariableDeclaration(self, ctx):
        id = ctx.Identifier().getText()
        init = ctx.initializer()
        code = []
        node = None
        ty = None
        sem_info = self.sem_table.lookup(id)
        if sem_info:
            ty = sem_info.type
            if is_list(ty) and not init:
                self._emit_create_array(id=id, code=code)
                node = IRAssign(
                    place=id,
                    name=id,
                    code = code
                )
        
        if init:
            expr_rslt = self.visit(init.expression())
            code += expr_rslt.code
            
            self._emit_assign(dst=id, src=expr_rslt.place, code=code)
  
            node = IRAssign(
                place=id,
                name=id,
                code = code
            )
        frame_id = self.frame_manager.current_frame_id()
        if frame_id:
            size = self.frame_manager.size_of_type(getattr(ty, "name", None))
            self.frame_manager.allocate_local(frame_id, id, type_name=getattr(ty, "name", None), size=size)
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
                frame_id = self.frame_manager.current_frame_id()
                if frame_id:
                    self.frame_manager.attach_runtime_info(self.sem_table, id, frame_id, category="local")

                node = IRAssign(
                    place=id,
                    name=id,
                    code=code
                )
        else:
            # --- asignación a propiedad: obj.prop = expr ---
            full_txt = ctx.getText()
            if "=" not in full_txt:
                raise RuntimeError("Asignación sin '=' en texto")

            lhs_text, rhs_text = full_txt.split("=", 1)
            if "." not in lhs_text:
                raise RuntimeError("LHS no contiene '.' para asignación a propiedad")

            obj_name, prop_name = lhs_text.rsplit(".", 1)

            rhs_ir = self.visit(ctx.expression(0))

            code = []
            if rhs_ir and rhs_ir.code:
                code += rhs_ir.code

            self._emit_store_prop(
                obj_place=obj_name,
                prop_name=prop_name,
                src_place=rhs_ir.place,
                code=code
            )

            node = IRAssign(
                place=None,
                name=f"{obj_name}.{prop_name}",
                code=code
            )
        return node
               

    
    def visitLiteralExpr(self, ctx):
        if ctx.arrayLiteral():
            sub = self.visit(ctx.arrayLiteral())
            return sub
        val = ctx.getText()
        place = self._new_temp()
        code = []
        self._emit_assign(dst=place, src=val, code=code)

        return IRNode(place=place, code=code)
    
    def visitExprNoAssign(self, ctx):
        sub = self.visit(ctx.conditionalExpr())
        return sub
    
    def visitAssignExpr(self, ctx):
        # ctx.lhs es un leftHandSide (labeled)
        lhs_node = self.visitLeftHandSide(ctx.lhs, mode="store")                   # debe devolver algo con .place
        rhs_node = self.visit(ctx.assignmentExpr())      # valor a asignar
        code = []

        if lhs_node:
            code += lhs_node.code
        if rhs_node:
            code += rhs_node.code
            
        r_place = rhs_node.place
        l_place = lhs_node.place
        # Asignación simple a variable (o a lo que retorne leftHandSide por ahora)

        if isinstance(lhs_node, IRArray):
            l_place = lhs_node.base
            self._emit_array_offset_store(
                arr_tem=lhs_node.base, 
                src=r_place,
                offset=4,
                index=lhs_node.index,
                code=code
            )
        else:
            self._emit_assign(dst=lhs_node.place, src=r_place, code=code)
        

        # Devuelve el 'place' del LHS como resultado de la expresión de asignación
        return IRNode(place=l_place, code=code)
    
    def visitPropertyAssignExpr(self, ctx):
        """
        lhs '.' Identifier '=' assignmentExpr
        Emite: setprop obj, prop, val
        """
        obj_node = self.visit(ctx.lhs)                # objeto a la izquierda del punto
        prop_name = ctx.Identifier().getText()
        rhs_node = self.visit(ctx.assignmentExpr())

        code = []
        if obj_node and obj_node.code: code += obj_node.code
        if rhs_node and rhs_node.code: code += rhs_node.code

        code.append(TACOP(op="setprop", arg1=obj_node.place, arg2=prop_name, result=rhs_node.place))
        # Devolver el valor asignado como resultado de la expresión
        return IRNode(place=rhs_node.place, code=code)

    # ==============================================================
    # ||  [8] Block Statement Flow
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
    # ||  [9] Expression statement
    # ==============================================================
    
    def visitExpressionStatement(self, ctx):
        sub = self.visit(ctx.expression())
        return sub
    # ==============================================================
    # ||  [10] leftHandSide and primaryAtom
    # ==============================================================
    def visitLeftHandSide(self, ctx, mode="load"):
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
        if ctx.suffixOp():
            for sop_idx in ctx.suffixOp():
                text = sop_idx.getText()
                if text[0] =="[": # handling for index suffix
                    sop = self.visit(sop_idx.expression())
                    code = sop.code
                    if mode == "load":
                        i_place = self._emit_array_offset_load(base.place, 4, sop.place, False, code)
                        return IRNode(
                            place=i_place,
                            code=code
                        )
                    else:
                        return IRArray(
                            place=f"{base.place}[{sop.place}]",
                            base=base.place,
                            index=sop.place,
                            code = code
                        )

                    
                if text[0] =="(":  # Handle for call
                    pass
                if text[0] ==".": # handle for attribute
                    pass
        return base
    
    def visitIdentifierExpr(self, ctx):
        """
        primaryAtom: Identifier  # IdentifierExpr
        Para TAC, un identificador puede ser usado como 'place' directo.
        No generamos código aquí; el que lo consuma decide si hace 't = id'.
        """
        name = ctx.Identifier().getText()
        return IRNode(place=name, code=[])
    
    def visitClassDeclaration(self,ctx):
        """
        class Identifier (':' Identifier)? '{' classMember* '}'
        """
        cls_name = ctx.Identifier(0).getText()
        base_name = None
        if ctx.Identifier() and len(ctx.Identifier()) > 1:
            base_name = ctx.Identifier(1).getText()

        out = []
        self._emit_class_begin(cls_name, base_name, out)

        # activar contexto de clase (para prefijar labels de métodos)
        prev = self.current_class
        self.current_class = cls_name

        # Si la semántica ya registró la clase/miembros, podemos leerlos de la tabla:
        class_sym = None
        try:
            # tu tabla semántica expone lookup_class? (si no, usa self.sem_table.lookup(cls_name) y comprueba type == "class")
            class_sym = getattr(self.sem_table, "lookup_class", None)
            class_sym = class_sym(cls_name) if callable(class_sym) else self.sem_table.lookup(cls_name)
        except Exception:
            class_sym = None

        attrs_meta = {}
        methods_meta = {}
        if class_sym and getattr(class_sym, "type", None) == "class":
            attrs_meta = class_sym.metadata.get("attributes", {}) or {}
            methods_meta = class_sym.metadata.get("methods", {}) or {}

        # 1) Emitir atributos como metadatos (NO ejecutamos inicializadores aquí)
        #    Preferimos la info de la tabla semántica; si no está, caemos al parse.
        if attrs_meta:
            for aname, asym in attrs_meta.items():
                ty_name = getattr(asym, "type", None)
                self._emit_class_attr(cls_name, aname, ty_name, out)
        else:
            # fallback: leer nombres desde el parse si no hubo semántica
            for m in ctx.classMember():
                if m.variableDeclaration():
                    vctx = m.variableDeclaration()
                    aname = vctx.Identifier().getText()
                    self._emit_class_attr(cls_name, aname, None, out)

        # 2) Emitir mapping método → label, y generar el TAC de cada método
        for m in ctx.classMember():
            if m.functionDeclaration():
                fctx = m.functionDeclaration()
                mname = fctx.Identifier().getText()
                Lentry, _ = self._func_labels(mname)

                # relación (cls, método) -> entry label
                self._emit_class_method(cls_name, mname, Lentry, out)

                # Generar el cuerpo del método con labels calificados
                mir = self.visitFunctionDeclaration(fctx)
                if mir and mir.code:
                    out += mir.code

            # IMPORTANTE: NO visites variable/constant aquí, para no “ejecutar” nada de clase.

        self._emit_class_end(cls_name, out)

        # restaurar contexto
        self.current_class = prev

        return IRNode(place=None, code=out)

    def dump_runtime_info(self):
        print("\n== RUNTIME FRAMES ==")
        for fid, frame in self.frame_manager._frames.items():
            print(f"Frame '{fid}':")
            for name, slot in frame.symbols.items():
                print(f"   {name:10s} offset={slot.offset:3d} size={slot.size:2d} type={slot.type_name}")


    # ==============================================================
    # ||  [11] Array Management
    # ==============================================================
    
    def visitIndexExpr(self, ctx):
        sub = self.visit(ctx.expression())
        return sub
    
    
    def _split_array_elements(self, text: str):
        """Splits top-level array elements, respecting nested brackets."""
        elems = []
        buf = []
        depth = 0
        for ch in text:
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
            elif ch == ',' and depth == 0:
                elems.append(''.join(buf).strip())
                buf = []
                continue
            buf.append(ch)
        if buf:
            elems.append(''.join(buf).strip())
        return elems


    def _fake_array_ctx(self, text: str):
        """
        Create a lightweight mock ctx for recursive array literals.
        Assumes you only need .getText().
        """
        class FakeCtx:
            def __init__(self, t): self.t = t
            def getText(self): return self.t
        return FakeCtx(text)
    
    def visitArrayLiteral(self, ctx):
        code = []
        
        arr_temp = self._emit_create_array(id=None,code=code)
        arr_text = ctx.getText().strip()[1:-1].strip()
        arr_iter = self._split_array_elements(arr_text)
        
        offset_size = 4
        count = 1
        for elem in arr_iter:
            
            if not elem:
                continue
            if elem.startswith('[') and elem.endswith(']'):
                nested_ctx = self._fake_array_ctx(elem)
                nested_node = self.visitArrayLiteral(nested_ctx)
                i_place = nested_node.place
                code += nested_node.code
                self._emit_array_offset_store(arr_temp, i_place, offset_size, count, code)
            else:
                i_place = self._new_temp()
                self._emit_assign(dst=i_place,src=elem, code=code)
                self._emit_array_offset_store(arr_temp, i_place, offset_size, count, code)
            count+=1
        self._emit_array_offset_store(arr_temp, count-1, 0, 0, code)
        return IRNode(
            place=arr_temp,
            code=code
        )