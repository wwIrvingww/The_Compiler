"""
Gestor de Procedimientos
Responsabilidad: Generar prólogos y epílogos de funciones en MIPS
- PRÓLOGO: Guardar $ra, $fp, reservar espacio para locales, guardar $s0-$s7
- EPÍLOGO: Restaurar registros, liberar stack, retornar
"""

import pprint
from typing import List, Set, Optional
from dataclasses import dataclass
from symbol_table.runtime_layout import FrameManager

@dataclass
class FrameInfo:
    """Información del stack frame de una función"""
    func_name: str
    local_size: int = 0          # Bytes para variables locales
    param_count: int = 0         # Número de parámetros
    uses_saved_regs: Set[str] = None  # $s0-$s7 usados
    max_call_args: int = 0       # Máximo args en llamadas internas
    most_negative_offset: int = 0
    fsize : int = 0
    def __post_init__(self):
        if self.uses_saved_regs is None:
            self.uses_saved_regs = set()
    
    @property
    def saved_regs_size(self) -> int:
        """Bytes necesarios para guardar $s0-$s7"""
        return len(self.uses_saved_regs) * 4
    
    @property
    def total_frame_size(self) -> int:
        """Tamaño total del frame (excluye $ra/$fp)"""
        return self.local_size + self.saved_regs_size


class ProcedureManager:
    """
    Gestor de Procedimientos para MIPS
    Genera secuencias de entrada/salida de funciones siguiendo convención:
    
    Layout del Stack Frame:
    ┌─────────────────┐ ← $fp (frame pointer)
    │  $ra guardado   │ +4($fp)
    │  $fp anterior   │  0($fp)
    ├─────────────────┤
    │  local_0        │ -4($fp)
    │  local_1        │ -8($fp)
    │  ...            │
    │  local_n        │ -(4+n*4)($fp)
    ├─────────────────┤
    │  $s0 guardado   │ ← Si se usa
    │  $s1 guardado   │
    │  ...            │
    │  $s7 guardado   │
    └─────────────────┘ ← $sp (stack pointer)
    """
    
    def __init__(self, frame_manager=None):
        """
        Args:
            frame_manager: Instancia de FrameManager (opcional)
                          Si se provee, extrae info automáticamente
        """
        self.frame_manager = frame_manager
        self.frame_cache = {}  # {func_name: FrameInfo}
        self.var_offsets = {}
    
    def get_frame_info(self, func_name: str) -> FrameInfo:
        """
        Obtiene información del frame de una función.
        Si hay FrameManager, extrae datos reales. Sino, usa defaults.
        """
        # Cachear para no recalcular
        if func_name in self.frame_cache:
            return self.frame_cache[func_name]
        
        frame_info = FrameInfo(func_name=func_name)
        
        if self.frame_manager:
            try:
                # Intentar obtener frame del FrameManager]
                self.frame_manager.enter_frame(func_name)
                frame = self.frame_manager.current_frame()
                if frame:
                    # Calcular tamaño de locales
                    local_size = 0
                    param_count = 0
                    fparams = frame.params
                    flocals = frame.locals
                    for sym_name, slot in fparams.items():
                        param_count += 1
                    for sym_name, slot in flocals.items():
                        local_size+= slot[1]
                    
                    frame_info.local_size = local_size
                    frame_info.param_count = param_count
                    frame_info.fsize = local_size + (4*param_count)
                    
                self.frame_manager.exit_frame()
            except Exception as e:
                print(e)
                # Si falla, usar defaults (frame vacío)
                pass
        
        self.frame_cache[func_name] = frame_info
        return frame_info
    
    def generate_prologue(
        self, 
        func_name: str, 
        frame_info: Optional[FrameInfo] = None,
        max_offset:int = 0
    ) -> List[str]:
        """
        Genera el prólogo de una función en MIPS.
        
        Pasos:
        1. Guardar $ra y $fp en el stack
        2. Establecer nuevo frame pointer ($fp = $sp)
        3. Reservar espacio para variables locales
        4. Guardar registros $s0-$s7 si se usan
        
        Args:
            func_name: Nombre de la función
            frame_info: Info del frame (opcional, se calcula si no se provee)
        
        Returns:
            Lista de instrucciones MIPS (strings)
        """
        if frame_info is None:
            frame_info: FrameInfo = self.get_frame_info(func_name)
            
        code = []
        
        eff_size = frame_info.fsize + 8 +abs(max_offset)# 8 por ra y fp
        # Etiqueta de la función
        code.append(f"{func_name}:")
        code.append(f"    # === PRÓLOGO {func_name} ===")
        
        # 1. Guardar $ra y $fp (8 bytes totales)
        # code.append("    # Guardar $ra y $fp")
        code.append(f"    addiu $sp, $sp, -{eff_size}")
        code.append(f"    sw $ra, 0($sp)")
        code.append(f"    sw $fp, 4($sp)")
        
        # 2. Establecer nuevo frame pointer
        # code.append("    # Establecer nuevo frame pointer")
        code.append("    move $fp, $sp")

        if self.var_offsets:
            offs_for_func = self.var_offsets.get(func_name)
            if offs_for_func and "self" in offs_for_func:
                self_off = offs_for_func["self"]
                code.append(f"    sw $a0, {self_off}($fp)        # iniciar self en el frame")

        # 3. Reservar espacio para locales + registros salvados
        # total_space = frame_info.total_frame_size
        # if total_space > 0:
        #     code.append(f"    # Reservar espacio: {frame_info.local_size} bytes locales + {frame_info.saved_regs_size} bytes $s")
        #     code.append(f"    addiu $sp, $sp, -{total_space}")
        
        # 4. Guardar registros $s0-$s7 si se usan
        if frame_info.uses_saved_regs:
            code.append("    # Guardar registros $s")
            saved_list = sorted(frame_info.uses_saved_regs)
            offset = -frame_info.local_size  # Empezar después de locales
            
            for reg in saved_list:
                code.append(f"    sw {reg}, {offset}($fp)")
                offset -= 4
        
        code.append(f"    # === FIN PRÓLOGO {func_name} ===")
        code.append("")
        
        return code
    
    def generate_epilogue(
        self, 
        func_name: str, 
        frame_info: Optional[FrameInfo] = None,
        has_return_value: bool = False,
        max_offset: int = 0
    ) -> List[str]:
        """
        Genera el epílogo de una función en MIPS.
        
        Pasos (en orden inverso al prólogo):
        1. Restaurar registros $s0-$s7 si se guardaron
        2. Liberar espacio de locales (restaurar $sp)
        3. Restaurar $ra y $fp del caller
        4. Retornar con jr $ra
        
        Args:
            func_name: Nombre de la función
            frame_info: Info del frame (opcional)
            has_return_value: Si True, asume que $v0 tiene el valor de retorno
        
        Returns:
            Lista de instrucciones MIPS (strings)
        """
        if frame_info is None:
            frame_info = self.get_frame_info(func_name)
        
        code = []
        
        code.append(f"    # === EPÍLOGO {func_name} ===")
        
        # 1. Restaurar registros $s0-$s7 (en orden inverso)
        if frame_info.uses_saved_regs:
            code.append("    # Restaurar registros $s")
            saved_list = sorted(frame_info.uses_saved_regs, reverse=True)
            offset = -(frame_info.local_size + (len(saved_list) - 1) * 4)
            
            for reg in saved_list:
                code.append(f"    lw {reg}, {offset}($fp)")
                offset += 4
        
        # 2. Liberar espacio de locales
        
        # print(eff_size)
        # if eff_size > 0:
        #     code.append(f"    # Liberar espacio del frame ({eff_size} bytes)")
        #     code.append(f"    addiu $sp, $sp, {eff_size}")
        
        # 3. Restaurar $ra y $fp
        eff_size = frame_info.fsize + 8 + abs(max_offset)
        # code.append("    # Restaurar $ra y $fp del caller")
        code.append("    lw $fp, 4($sp)")
        code.append("    lw $ra, 0($sp)")
        code.append(f"    addiu $sp, $sp, {eff_size}")
        
        # 4. Retornar
        # if has_return_value:
        #     code.append("    # Retornar (valor en $v0)")
        # else:
        #     code.append("    # Retornar")
        code.append("    jr $ra\t# ret en $v0")
        code.append(f"    # === FIN EPÍLOGO {func_name} ===")
        code.append("")
        
        return code
    
    def generate_simple_function(
        self, 
        func_name: str,
        body_instructions: List[str],
        frame_info: Optional[FrameInfo] = None,
        has_return: bool = False,
        var_offsets = None
    ) -> List[str]:
        """
        Genera una función completa (prólogo + cuerpo + epílogo).
        Útil para tests y funciones simples.
        
        Args:
            func_name: Nombre de la función
            body_instructions: Lista de instrucciones del cuerpo
            frame_info: Info del frame (opcional)
            has_return: Si la función retorna un valor
        
        Returns:
            Lista completa de instrucciones MIPS
        """
        code = []
        self.var_offsets = var_offsets or {}
        # Prólogo
        max_offset = 0

        # Si nos pasaron var_offsets, intentamos usar los de ESTA función
        if var_offsets:
            offs = var_offsets.get(func_name)
            if offs:
                # offs es un dict {var_name: offset}
                max_offset = 0
                for off in offs.values():
                    max_offset = min(max_offset, off)
        
        code.extend(self.generate_prologue(func_name, frame_info, max_offset))
        
        # Cuerpo
        if body_instructions:
            code.append("    # === CUERPO ===")
            code.extend(body_instructions)
            code.append("")
        
        # Epílogo
        code.extend(self.generate_epilogue(func_name, frame_info, has_return, max_offset))
        
        return code
    
    def mark_saved_reg_usage(self, func_name: str, reg: str):
        """
        Marca que una función usa un registro $s0-$s7.
        Esto debe ser llamado durante la asignación de registros.
        
        Args:
            func_name: Nombre de la función
            reg: Registro usado (ej: "$s0")
        """
        frame_info = self.get_frame_info(func_name)
        if reg.startswith("$s"):
            frame_info.uses_saved_regs.add(reg)
    
    def set_local_size(self, func_name: str, size: int):
        """
        Establece manualmente el tamaño de locales.
        Útil si no hay FrameManager disponible.
        """
        frame_info = self.get_frame_info(func_name)
        frame_info.local_size = size
    
    def generate_main_wrapper(self) -> List[str]:
        """
        Genera el wrapper para main (punto de entrada del programa).
        En MIPS, main debe retornar con syscall exit.
        """
        code = [
            ".text",
            ".globl main",
            "",
            "main:",
            "    # Llamar a func_main (tu función principal)",
            "    jal func_main",
            "    ",
            "    # Salir del programa (syscall exit)",
            "    li $v0, 10",
            "    syscall"
        ]
        return code


# ========================================
# Utilidades para debugging y visualización
# ========================================

def visualize_frame_layout(frame_info: FrameInfo) -> str:
    """
    Genera una representación ASCII del layout del stack frame.
    Útil para debugging.
    """
    lines = []
    lines.append(f"=== Frame Layout: {frame_info.func_name} ===")
    lines.append("┌─────────────────────┐")
    lines.append("│  $ra guardado       │ +4($fp)")
    lines.append("│  $fp anterior       │  0($fp) ← $fp")
    lines.append("├─────────────────────┤")
    
    # Variables locales
    if frame_info.local_size > 0:
        num_locals = frame_info.local_size // 4
        for i in range(num_locals):
            offset = -4 * (i + 1)
            lines.append(f"│  local_{i:<11} │ {offset}($fp)")
    else:
        lines.append("│  (sin locales)      │")
    
    # Registros guardados
    if frame_info.uses_saved_regs:
        lines.append("├─────────────────────┤")
        saved_list = sorted(frame_info.uses_saved_regs)
        offset = -(frame_info.local_size + 4)
        for reg in saved_list:
            lines.append(f"│  {reg} guardado       │ {offset}($fp)")
            offset -= 4
    
    lines.append("└─────────────────────┘ ← $sp")
    lines.append(f"Total frame size: {frame_info.total_frame_size} bytes")
    
    return "\n".join(lines)


# ========================================
# Función de conveniencia para generar .asm completo
# ========================================

def generate_asm_file(
    functions: List[tuple],  # [(func_name, body_instructions, has_return)]
    data_section: List[str] = None,
    procedure_manager: ProcedureManager = None,
    var_offsets = None
) -> str:
    """
    Genera un archivo .asm completo con múltiples funciones.
    
    Args:
        functions: Lista de tuplas (func_name, body_instructions, has_return)
        data_section: Instrucciones de la sección .data (opcional)
        procedure_manager: Instancia de ProcedureManager (opcional)
    
    Returns:
        String con el contenido completo del .asm
    """
    if procedure_manager is None:
        procedure_manager = ProcedureManager()
    
    lines = []
    
    # Sección .data
    if data_section:
        lines.append(".data")
        lines.extend(data_section)
        lines.append("")
    
    # Sección .text
    lines.extend(procedure_manager.generate_main_wrapper())
    lines.append("")
    
    # Funciones
    for func_name, body, has_return in functions:
        func_code = procedure_manager.generate_simple_function(
            func_name, body, has_return=has_return, var_offsets=var_offsets,
        )
        lines.extend(func_code)
        lines.append("")
    
    return "\n".join(lines)