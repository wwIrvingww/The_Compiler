"""
MIPS code generator: TAC -> MIPS assembly.

This module uses:
- MIPSPreAnalysis: to split TAC by function and get liveness info.
- ProcedureManager: to build prologue / epilogue / main wrapper.
- RegisterAllocator: to manage temporary and variable registers.

The goal is to provide a simple but structured translation from a small
subset of TAC operations to runnable MIPS code for MARS.
"""
import pprint
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional

from intermediate.tac_nodes import TACOP
from symbol_table.runtime_layout import FrameManager
from code_generator.pre_analysis import MIPSPreAnalysis
from code_generator.procedure_manager import ProcedureManager, FrameInfo, generate_asm_file
from code_generator.register_allocator import RegisterAllocator


@dataclass
class FunctionCodegenContext:
    """Per-function helpers and metadata used during codegen."""
    name: str
    frame_info: FrameInfo
    liveness: Dict[int, Set[str]]
    body: List[str]
    reg_alloc: RegisterAllocator
    param_counter: int = 0


class MIPSCodeGenerator:
    """
    High level driver that turns TAC into a full .asm string.

    Usage:
        gen = MIPSCodeGenerator(tac_code, frame_manager)
        asm_text = gen.generate()
    """

    def __init__(self, tac_code: List[TACOP], frame_manager: Optional[FrameManager] = None):
        self.tac_code = tac_code
        self.frame_manager = frame_manager or FrameManager()
        self.pre = MIPSPreAnalysis(tac_code, self.frame_manager)
        self.proc_manager = ProcedureManager(self.frame_manager)
        
        self.string_temps: Dict[str, str] = {}

        
    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def generate(self) -> str:
        """
        Run pre-analysis and then translate every function TAC block into MIPS.

        Returns:
            Complete .asm program as a single string.
        """
        # 1) Run pre-analysis (functions, frame sizes, liveness, saved regs)
        self.pre.analyze()

        functions_payload: List[Tuple[str, List[str], bool]] = []

        # 2) Generate body for each function
        for func_name in self.pre.get_all_functions():
            
            func_tac, frame_info, liveness, _saved_regs = self.pre.get_function_info(func_name)
            ctx = FunctionCodegenContext(
                name=func_name,
                frame_info=frame_info,
                liveness=liveness,
                body=[],
                reg_alloc=RegisterAllocator(base_pointer="$fp"),
            )

            self._generate_function_body(ctx, func_tac)

            has_return = any(op.op == "return" for op in func_tac)
            functions_payload.append((func_name, ctx.body, has_return))

        # 3) Use ProcedureManager helper to assemble a complete .asm
        asm_text = generate_asm_file(
            functions=functions_payload,
            data_section=self.pre.data_section,
            procedure_manager=self.proc_manager,
        )
        return asm_text

    # ------------------------------------------------------------
    # Core codegen for a single function
    # ------------------------------------------------------------

    def _generate_function_body(self, ctx: FunctionCodegenContext, func_tac: List[TACOP]) -> None:
        """
        Translate every TAC operation of a function into MIPS, storing lines
        in ctx.body.
        """
        for index, tac in enumerate(func_tac):
            live_out = ctx.liveness.get(index, set())

            if tac.op == "fn_decl":
                # The ProcedureManager will generate labels + prologue.
                # Here we only leave a helpful comment.
                ctx.body.append(f"    # Function {tac.result} body")
                continue

            # Assignment / movement
            if tac.op == "=":
                self._emit_assign(ctx, tac, live_out)
            # Arithmetic
            elif tac.op in "+-*/%":
                self._emit_arithmetic(ctx, tac, live_out)
            # Relational / logical (boolean result in result)
            elif tac.op in {"==", "!=", "<", "<=", ">", ">=", "&&", "||"}:
                self._emit_relop(ctx, tac, live_out)
            # Control flow
            elif tac.op == "label":
                self._emit_label(ctx, tac)
            elif tac.op == "goto":
                self._emit_goto(ctx, tac)
            elif tac.op == "if-goto":
                self._emit_if_goto(ctx, tac, live_out)
            elif tac.op == "return":
                self._emit_return(ctx, tac, live_out)
            # Parameters push
            elif tac.op == "push_param":
                self._emit_push_param(ctx, tac, live_out)
            elif tac.op == "load_param":
                self._emit_load_param(ctx, tac, live_out)
            elif tac.op == "print":
                self._emit_print(ctx, tac, live_out, False)
            elif tac.op == "print_s":
                self._emit_print(ctx, tac, live_out, True)
            elif tac.op == "call":
                self._emit_call(ctx, tac, live_out)
            else:
                # For unsupported ops, emit a comment so it is visible in output.
                ctx.body.append(f"    # TODO: unsupported TAC op {tac.op} ({tac})")

    # ------------------------------------------------------------
    # Helpers: literal detection
    # ------------------------------------------------------------

    @staticmethod
    def _is_int_literal(value: Optional[str]) -> bool:
        if value is None:
            return False
        try:
            int(value)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------
    # Emitters
    # ------------------------------------------------------------


    def _emit_assign(self, ctx: FunctionCodegenContext, tac: TACOP, live_out: Set[str]) -> None:
        dest = tac.result
        src = tac.arg1

        if dest is None or src is None:
            return

        # Case 1: literal integer or boolean
        if self._is_int_literal(src):
            reg, pre = ctx.reg_alloc.get_register_for(dest, live_out, for_read=False, for_write=True)
            ctx.body.extend(pre)
            ctx.body.append(f"    li {reg}, {src}    # {dest} = {src}")
            ctx.reg_alloc.mark_written(reg)
            return
        if src in ("true", "false"):
            val = "1" if src == "true" else "0"
            reg, pre = ctx.reg_alloc.get_register_for(dest, live_out, for_read=False, for_write=True)
            ctx.body.extend(pre)
            ctx.body.append(f"    li {reg}, {val}    # {dest} = {src}")
            ctx.reg_alloc.mark_written(reg)
            return
        if src.startswith('"'):
            # No tocamos el RegisterAllocator para este temp: no nos interesa
            # que las cadenas entren al juego de liveness y reasignación.
            data_info = self.pre.str_encoder.get(src)
            if data_info is None:
                ctx.body.append(f"    # WARNING: string literal {src} no encontrado en str_encoder")
                return
            data_label = data_info["id"]
            self.string_temps[dest] = data_label
            ctx.body.append(f"    # {dest} = (str){src} -> {data_label}")
            return
        # Case 2: move between variables/temporaries
        src_reg, pre1 = ctx.reg_alloc.get_register_for(src, live_out, for_read=True, for_write=False)
        dest_reg, pre2 = ctx.reg_alloc.get_register_for(dest, live_out, for_read=False, for_write=True)
        ctx.body.extend(pre1)
        ctx.body.extend(pre2)
        if src_reg != dest_reg:
            ctx.body.append(f"    move {dest_reg}, {src_reg}    # {dest} = {src}")
        ctx.reg_alloc.mark_written(dest_reg)

    def _emit_push_param(self, ctx, tac, live_out):
        pcount = ctx.param_counter
        if pcount < 4:
            src = tac.result
            dest = f"$a{pcount}"
            
            if self._is_int_literal(src):
                reg, pre = ctx.reg_alloc.get_register_for(f"param[{pcount}]", live_out, for_read=False, for_write=True)
                ctx.body.extend(pre)
                ctx.body.append(f"    li {reg}, {src}    # param[{pcount}] ={src}")
                ctx.reg_alloc.mark_written(reg)
                ctx.body.append(f"    move {dest}, {reg}")
                ctx.param_counter+=1
                return
            if src in ("true", "false"):
                val = "1" if src == "true" else "0"
                reg, pre = ctx.reg_alloc.get_register_for(f"param[{pcount}]", live_out, for_read=False, for_write=True)
                ctx.body.extend(pre)
                ctx.body.append(f"    li {reg}, {val}    # param[{pcount}] = {src}")
                ctx.reg_alloc.mark_written(reg)
                ctx.body.append(f"    move {dest}, {reg}")
                ctx.param_counter+=1
                return

            # Case 2: move between variables/temporaries
            src_reg, pre1 = ctx.reg_alloc.get_register_for(src, live_out, for_read=True, for_write=False)
            ctx.body.extend(pre1)
            if src_reg != dest:
                ctx.body.append(f"    move {dest}, {src_reg}    # param[{pcount}] = {src}")
            ctx.param_counter+=1
        else:
            ctx.body.append(f"    # TODO: params >4 go with stack")    
        
    def _emit_load_param(self, ctx, tac, live_out):
        dest = tac.result
        param_idx = int(tac.arg1)
        if param_idx < 4:
            dest_reg, pre1 = ctx.reg_alloc.get_register_for(dest, live_out, for_read=True, for_write=False)
            ctx.body.extend(pre1)
            ctx.body.append(f"    move {dest_reg}, $a{param_idx}    # {dest_reg} = param[{param_idx}]")
            ctx.body.append(f"    sw $a{param_idx}, {param_idx*4 + 8}($sp)")
        else:
            ctx.body.append(f"    # TODO: params >4 go with stack")    
        
        
    def _emit_call(self, ctx, tac, live_out):
        fname = tac.arg1
        dest = tac.result
        ctx.body.append(
            f"    jal {fname}   # call {fname}()"
        )
        if dest:
            dest_reg, pre1 = ctx.reg_alloc.get_register_for(dest, live_out, for_read=True, for_write=False)
            ctx.body.extend(pre1)
            ctx.body.append(f"    move {dest_reg}, $v0    # ret of {fname}()")
        ctx.param_counter=0
        
    def _emit_print(self, ctx, tac, live_out, is_str):
        src = tac.arg1
        if is_str:
            # Intentamos primero usar el mapeo temp -> label, generado en _emit_assign
            label = self.string_temps.get(src)

            if label is not None:
                # No usamos RegisterAllocator: cargamos la etiqueta directo
                ctx.body.append(f"    li $v0, 4    # print string")
                ctx.body.append(f"    la $a0, {label}    # print({src})")
                ctx.body.append(f"    syscall")
                return

            # Fallback por si algún día tienes strings dinámicos o algo raro:
            # usa el allocator, como antes.
            src_reg, pre1 = ctx.reg_alloc.get_register_for(
                src,
                live_out,
                for_read=True,
                for_write=False
            )
            ctx.body.extend(pre1)
            ctx.body.append(f"    li $v0, 4    # print string (fallback)")
            ctx.body.append(f"    move $a0, {src_reg}    # print({src_reg})")
            ctx.body.append(f"    syscall")
            return

        # -------- Caso normal: print int (igual que ya lo tenías) --------
        src_reg, pre1 = ctx.reg_alloc.get_register_for(
            src,
            live_out,
            for_read=True,
            for_write=False
        )
        ctx.body.extend(pre1)
        ctx.body.append(f"    li $v0, 1    # print int")
        ctx.body.append(f"    move $a0, {src_reg}    # print({src_reg})")
        ctx.body.append(f"    syscall")
            # src = tac.arg1
            # preg, pre = ctx.reg_alloc.get_register_for(src, live_out, for_read=True, for_write=False)
            # ctx.body.append(
            #     f"    li {preg}, $v0    # ret of {fname}()"
            # )
    
    def _emit_arithmetic(self, ctx: FunctionCodegenContext, tac: TACOP, live_out: Set[str]) -> None:
        op = tac.op
        a = tac.arg1
        b = tac.arg2
        dest = tac.result
        if dest is None or a is None or b is None:
            return

        op_map: Dict[str, str] = {
            "+": "add",
            "-": "sub",
            "*": "mul",
            "/": "div",  # MARS acepta 'div rd, rs, rt' como pseudoinstrucción
        }
        
        if (op == "%"):
            reg_a, pre1 = ctx.reg_alloc.get_register_for(a, live_out, for_read=True, for_write=False)
            reg_b, pre2 = ctx.reg_alloc.get_register_for(b, live_out, for_read=True, for_write=False)
            reg_dest, pre3 = ctx.reg_alloc.get_register_for(dest, live_out, for_read=False, for_write=True)

            ctx.body.extend(pre1)
            ctx.body.extend(pre2)
            ctx.body.extend(pre3)

            ctx.body.append(f"    div {reg_dest}, {reg_a}, {reg_b}    # {a}%{b}")
            ctx.body.append(f"    mfhi {reg_dest}    # (remainder)")
            ctx.reg_alloc.mark_written(reg_dest)
            return
            
        mips_op = op_map[op]

        reg_a, pre1 = ctx.reg_alloc.get_register_for(a, live_out, for_read=True, for_write=False)
        reg_b, pre2 = ctx.reg_alloc.get_register_for(b, live_out, for_read=True, for_write=False)
        reg_dest, pre3 = ctx.reg_alloc.get_register_for(dest, live_out, for_read=False, for_write=True)

        ctx.body.extend(pre1)
        ctx.body.extend(pre2)
        ctx.body.extend(pre3)

        ctx.body.append(f"    {mips_op} {reg_dest}, {reg_a}, {reg_b}    # {dest} = {a} {op} {b}")
        ctx.reg_alloc.mark_written(reg_dest)

    def _emit_relop(self, ctx: FunctionCodegenContext, tac: TACOP, live_out: Set[str]) -> None:
        op = tac.op
        a = tac.arg1
        b = tac.arg2
        dest = tac.result
        if dest is None or a is None or b is None:
            return

        # Pseudo-instructions available in MARS: seq, sne, slt, sle, sgt, sge
        op_map: Dict[str, str] = {
            "==": "seq",
            "!=": "sne",
            "<": "slt",
            "<=": "sle",
            ">": "sgt",
            ">=": "sge",
            "&&": "and",
            "||": "or",
        }
        mips_op = op_map[op]

        reg_a, pre1 = ctx.reg_alloc.get_register_for(a, live_out, for_read=True, for_write=False)
        reg_b, pre2 = ctx.reg_alloc.get_register_for(b, live_out, for_read=True, for_write=False)
        reg_dest, pre3 = ctx.reg_alloc.get_register_for(dest, live_out, for_read=False, for_write=True)

        ctx.body.extend(pre1)
        ctx.body.extend(pre2)
        ctx.body.extend(pre3)

        ctx.body.append(f"    {mips_op} {reg_dest}, {reg_a}, {reg_b}    # {dest} = {a} {op} {b}")
        ctx.reg_alloc.mark_written(reg_dest)

    def _emit_label(self, ctx: FunctionCodegenContext, tac: TACOP) -> None:
        label = tac.result or tac.arg1
        if label:
            ctx.body.append(f"{label}:")

    def _emit_goto(self, ctx: FunctionCodegenContext, tac: TACOP) -> None:
        target = tac.arg1
        if target:
            ctx.body.append(f"    j {target}    # goto {target}")

    def _emit_if_goto(self, ctx: FunctionCodegenContext, tac: TACOP, live_out: Set[str]) -> None:
        cond = tac.arg1
        target = tac.arg2
        if not target or cond is None:
            return

        # Constant-fold very simple boolean literals
        if cond == "true":
            ctx.body.append(f"    j {target}    # if true goto {target}")
            return
        if cond == "false":
            # nunca salta
            ctx.body.append(f"    # if false goto {target} (omitido)")
            return

        reg_cond, pre = ctx.reg_alloc.get_register_for(cond, live_out, for_read=True, for_write=False)
        ctx.body.extend(pre)
        ctx.body.append(f"    bne {reg_cond}, $zero, {target}    # if {cond} goto {target}")

    def _emit_return(self, ctx: FunctionCodegenContext, tac: TACOP, live_out: Set[str]) -> None:
        if tac.arg1 is None:
            ctx.body.append("    # return (void)")
            return

        reg_val, pre = ctx.reg_alloc.get_register_for(tac.arg1, live_out, for_read=True, for_write=False)
        ctx.body.extend(pre)
        ctx.body.append(f"    move $v0, {reg_val}    # return {tac.arg1}")
        # No hacemos jr $ra aquí; el epílogo del ProcedureManager se encarga.
