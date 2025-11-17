"""
Pre-Análisis para Generación de Código MIPS
Realiza 4 tareas antes de generar código:
1. Identificar funciones
2. Calcular tamaños de frames
3. Liveness analysis
4. Detectar uso de $s0-$s7
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field

from intermediate.tac_nodes import TACOP
from code_generator.procedure_manager import FrameInfo
from symbol_table.runtime_layout import FrameManager


@dataclass
class FunctionInfo:
    """Información básica de una función detectada en TAC"""
    name: str
    start_idx: int
    end_idx: Optional[int] = None
    tac_ops: List[TACOP] = field(default_factory=list)
    has_return: bool = False
    calls_other_funcs: Set[str] = field(default_factory=set)


# ========================================
# 1. IDENTIFICAR FUNCIONES
# ========================================

def identify_functions(tac_code: List[TACOP]) -> Dict[str, FunctionInfo]:
    """
    Encuentra todas las funciones en el código TAC.
    
    Args:
        tac_code: Lista completa de operaciones TAC
    
    Returns:
        Diccionario {func_name: FunctionInfo}
    """
    functions = {}
    current_func = None
    start_idx = 0
    
    for i, tac_op in enumerate(tac_code):
        if tac_op.op == "fn_decl":
            # Cerrar función anterior
            if current_func:
                functions[current_func].end_idx = i - 1
                functions[current_func].tac_ops = tac_code[start_idx:i]
            
            # Abrir nueva función
            func_name = tac_op.result
            current_func = func_name
            start_idx = i
            
            functions[func_name] = FunctionInfo(
                name=func_name,
                start_idx=i,
                tac_ops=[]
            )
        
        elif current_func:
            # Detectar returns
            if tac_op.op == "return":
                functions[current_func].has_return = True
            
            # Detectar llamadas a otras funciones
            elif tac_op.op == "call":
                called_func = tac_op.arg1
                if called_func:
                    functions[current_func].calls_other_funcs.add(called_func)
    
    # Cerrar última función
    if current_func:
        functions[current_func].end_idx = len(tac_code) - 1
        functions[current_func].tac_ops = tac_code[start_idx:]
    
    return functions


# ========================================
# 2. CALCULAR TAMAÑOS DE FRAMES
# ========================================

def calculate_frame_sizes(
    functions: Dict[str, FunctionInfo],
    frame_manager: FrameManager
) -> Dict[str, FrameInfo]:
    """
    Extrae información de frames desde el FrameManager.
    
    Args:
        functions: Diccionario de funciones detectadas
        frame_manager: Instancia de FrameManager con info de runtime
    
    Returns:
        Diccionario {func_name: FrameInfo}
    """
    frame_infos = {}
    
    for func_name, func_data in functions.items():
        frame_info = FrameInfo(func_name=func_name)
        
        try:
            # Intentar diferentes métodos para obtener el frame
            frame = None
            
            # Método 1: get_frame (API estándar)
            if hasattr(frame_manager, 'get_frame'):
                frame = frame_manager.get_frame(func_name)
            
            # Método 2: _frames (acceso directo al dict interno)
            elif hasattr(frame_manager, '_frames') and func_name in frame_manager._frames:
                frame = frame_manager._frames[func_name]
            
            # Método 3: all_frames() y buscar
            elif hasattr(frame_manager, 'all_frames'):
                all_frames = frame_manager.all_frames()
                if func_name in all_frames:
                    frame = all_frames[func_name]
            
            if frame:
                local_size = 0
                param_count = 0
                
                # Iterar sobre símbolos del frame
                if hasattr(frame, 'symbols'):
                    for sym_name, slot in frame.symbols.items():
                        if hasattr(slot, 'category'):
                            if slot.category == "local":
                                local_size += slot.size
                            elif slot.category == "param":
                                param_count += 1
                
                frame_info.local_size = local_size
                frame_info.param_count = param_count
        
        except Exception as e:
            # Si no existe frame o falla la extracción, usar defaults
            # No imprimir warning, es normal para algunas funciones
            pass
        
        frame_infos[func_name] = frame_info
    
    return frame_infos


# ========================================
# 3. LIVENESS ANALYSIS
# ========================================

def is_literal(operand: str) -> bool:
    """
    Verifica si un operando es un literal (no una variable).
    
    Args:
        operand: String del operando (ej: "5", "true", "t0")
    
    Returns:
        True si es literal, False si es variable/temporal
    """
    if not operand:
        return True
    
    # Literales booleanos y null
    if operand.lower() in ("true", "false", "null"):
        return True
    
    # Números enteros
    try:
        int(operand)
        return True
    except ValueError:
        pass
    
    # Números flotantes
    try:
        float(operand)
        return True
    except ValueError:
        pass
    
    # Strings entre comillas
    if operand.startswith('"') and operand.endswith('"'):
        return True
    if operand.startswith("'") and operand.endswith("'"):
        return True
    
    return False


def encode_strs(code: List[TACOP]):
    # Enode strings
    str_encoder = {} # value->idx
    counter = 0
    for i, t in enumerate(code):
        if t.arg1:
            if (t.arg1.startswith('"')):
                if t.arg1 not in str_encoder:
                    str_encoder[t.arg1] = {
                        "id": f"str{counter}",
                    }
                counter+=1
        if t.arg2:
            if (t.arg2.startswith('"')):
                if t.arg2 not in str_encoder:
                    str_encoder[t.arg2] = {
                        "id": f"str{counter}",
                    }
                counter+=1
    
    # No strings -> return case
    if len(str_encoder) == 0:
        return None, None
    
    # Prepare data section
    data_section = []
    for k, v in str_encoder.items():
        data_section.append(
            f"{v["id"]}: .asciiz {k}"
        )

    return str_encoder, data_section
    

def liveness_analysis(func_tac: List[TACOP]) -> Dict[int, Set[str]]:
    """
    Calcula las variables vivas (live) en cada instrucción.
    
    Algoritmo de análisis de flujo de datos (backward):
    - live_out[i] = variables que se USAN después de la instrucción i
    - live_in[i] = (live_out[i] - def[i]) ∪ use[i]
    
    Args:
        func_tac: Lista de operaciones TAC de una función
    
    Returns:
        Diccionario {índice: set de variables vivas después de esa instrucción}
    """
    if not func_tac:
        return {}
    
    n = len(func_tac)
    live_in = [set() for _ in range(n)]
    live_out = [set() for _ in range(n)]
    
    # Construir grafo de flujo de control (CFG simplificado)
    successors = [set() for _ in range(n)]
    for i in range(n):
        tac_op = func_tac[i]
        
        if tac_op.op == "goto":
            # Buscar etiqueta destino
            target_label = tac_op.arg1
            for j in range(n):
                if func_tac[j].op == "label" and func_tac[j].result == target_label:
                    successors[i].add(j)
                    break
        
        elif tac_op.op == "if-goto":
            # Rama verdadera
            target_label = tac_op.arg2
            for j in range(n):
                if func_tac[j].op == "label" and func_tac[j].result == target_label:
                    successors[i].add(j)
                    break
            # Rama falsa (caída)
            if i + 1 < n:
                successors[i].add(i + 1)
        
        elif tac_op.op == "return":
            # Sin sucesores (fin de función)
            pass
        
        else:
            # Flujo secuencial normal
            if i + 1 < n:
                successors[i].add(i + 1)
    
    # Iteración hacia atrás (fixed-point)
    changed = True
    max_iterations = 100
    iteration = 0
    
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        
        for i in range(n - 1, -1, -1):
            tac_op = func_tac[i]
            
            # Variables usadas (use)
            use = set()
            if tac_op.arg1 and not is_literal(tac_op.arg1):
                use.add(tac_op.arg1)
            if tac_op.arg2 and not is_literal(tac_op.arg2):
                use.add(tac_op.arg2)
            
            # Variable definida (def)
            def_var = set()
            if tac_op.result and tac_op.op not in ["label", "goto", "if-goto", "fn_decl"]:
                def_var.add(tac_op.result)
            
            # Calcular live_in
            new_live_in = (live_out[i] - def_var) | use
            
            if new_live_in != live_in[i]:
                live_in[i] = new_live_in
                changed = True
            
            # Propagar a sucesores
            for succ_idx in successors[i]:
                live_out[i] |= live_in[succ_idx]
    
    return {i: live_out[i] for i in range(n)}


# ========================================
# 4. DETECTAR USO DE $s0-$s7
# ========================================

def detect_saved_registers_usage(
    func_tac: List[TACOP],
    liveness: Dict[int, Set[str]],
    func_info: FunctionInfo
) -> Set[str]:
    """
    Detecta si una función necesita usar registros $s0-$s7.
    
    Heurísticas:
    1. Si hay variables que viven a través de llamadas (call), necesitan $s
    2. Si hay más de 10 temporales simultáneos vivos, necesitamos $s
    3. Si la función es recursiva, probablemente necesita $s
    
    Args:
        func_tac: Lista de operaciones TAC de la función
        liveness: Resultado del análisis de liveness
        func_info: Información de la función
    
    Returns:
        Set de registros $s necesarios (ej: {"$s0", "$s1"})
    """
    max_live = 0
    live_across_call = set()
    
    for i, tac_op in enumerate(func_tac):
        # Contar variables vivas simultáneas
        live_vars = liveness.get(i, set())
        max_live = max(max_live, len(live_vars))
        
        # Variables vivas antes de una llamada (necesitan preservarse)
        if tac_op.op == "call":
            live_before = liveness.get(i, set())
            live_across_call.update(live_before)
    
    # Decidir cuántos $s necesitamos
    needed_s_regs = set()
    
    # 1. Variables que sobreviven llamadas → usar $s
    num_preserved = len(live_across_call)
    for i in range(min(num_preserved, 8)):  # Máximo 8 registros $s
        needed_s_regs.add(f"$s{i}")
    
    # 2. Muchos temporales simultáneos (>10) → necesitamos $s adicionales
    # Asumimos que $t0-$t9 (10 registros) se usan primero
    if max_live > 10:
        extra_s_needed = min((max_live - 10 + 1) // 2, 8)
        for i in range(extra_s_needed):
            needed_s_regs.add(f"$s{i}")
    
    # 3. Función recursiva → reservar al menos $s0
    if func_info.name in func_info.calls_other_funcs:
        needed_s_regs.add("$s0")
    
    return needed_s_regs


# ========================================
# CLASE PRINCIPAL: PRE-ANÁLISIS COMPLETO
# ========================================

class MIPSPreAnalysis:
    """
    Coordina las 4 tareas del pre-análisis antes de generar código MIPS.
    """
    
    def __init__(self, tac_code: List[TACOP], frame_manager: FrameManager):
        """
        Args:
            tac_code: Lista completa de operaciones TAC
            frame_manager: Instancia de FrameManager con info de runtime
        """
        self.tac_code = tac_code
        self.frame_manager = frame_manager
        
        str_encoder, data_section = encode_strs(tac_code)
        self.data_section = []
        self.str_encoder = {}
        if str_encoder:
            self.str_encoder = str_encoder
            self.data_section = data_section
        # Resultados del análisis (se llenan al llamar analyze())
        self.functions: Dict[str, FunctionInfo] = {}
        self.frame_infos: Dict[str, FrameInfo] = {}
        self.liveness: Dict[str, Dict[int, Set[str]]] = {}
        self.saved_regs_usage: Dict[str, Set[str]] = {}
    
    def analyze(self) -> None:
        """Ejecuta las 4 etapas del pre-análisis"""
        print(" Iniciando pre-análisis...")
        
        # 1. Identificar funciones
        print("  [1/4] Identificando funciones...")
        self.functions = identify_functions(self.tac_code)
        print(f"        ✓ Encontradas {len(self.functions)} funciones")
        
        # 2. Calcular tamaños de frames
        print("  [2/4] Calculando tamaños de frames...")
        self.frame_infos = calculate_frame_sizes(self.functions, self.frame_manager)
        print(f"        ✓ Frames calculados")
        
        # 3. Liveness analysis por función
        print("  [3/4] Analizando liveness...")
        for func_name, func_info in self.functions.items():
            self.liveness[func_name] = liveness_analysis(func_info.tac_ops)
        print(f"        ✓ Liveness completado")
        
        # 4. Detectar uso de $s0-$s7
        print("  [4/4] Detectando uso de registros $s...")
        for func_name, func_info in self.functions.items():
            saved_regs = detect_saved_registers_usage(
                func_info.tac_ops,
                self.liveness[func_name],
                func_info
            )
            self.saved_regs_usage[func_name] = saved_regs
            
            # Actualizar FrameInfo con registros $s detectados
            if func_name in self.frame_infos:
                self.frame_infos[func_name].uses_saved_regs = saved_regs
        
        print(f"        ✓ Registros $s detectados")
        print(" Pre-análisis completado\n")
    
    def get_function_info(self, func_name: str) -> Tuple[List[TACOP], FrameInfo, Dict[int, Set[str]], Set[str]]:
        """
        Devuelve toda la información necesaria para generar código de una función.
        
        Args:
            func_name: Nombre de la función
        
        Returns:
            Tupla (tac_ops, frame_info, liveness, saved_regs)
        """
        return (
            self.functions[func_name].tac_ops,
            self.frame_infos[func_name],
            self.liveness[func_name],
            self.saved_regs_usage[func_name]
        )
    
    def print_summary(self) -> None:
        """Imprime resumen del análisis para debugging"""
        print("=" * 60)
        print("RESUMEN DEL PRE-ANÁLISIS")
        print("=" * 60)
        
        for func_name in self.functions:
            func_info = self.functions[func_name]
            frame = self.frame_infos.get(func_name)
            
            print(f"\n {func_name}:")
            print(f"   • Instrucciones TAC: {len(func_info.tac_ops)}")
            print(f"   • Tiene return: {func_info.has_return}")
            
            if func_info.calls_other_funcs:
                print(f"   • Llama a: {', '.join(func_info.calls_other_funcs)}")
            
            if frame:
                print(f"   • Locales: {frame.local_size} bytes")
                print(f"   • Parámetros: {frame.param_count}")
                
                if frame.uses_saved_regs:
                    regs_str = ', '.join(sorted(frame.uses_saved_regs))
                    print(f"   • Registros $s: {regs_str}")
                else:
                    print(f"   • Registros $s: ninguno")
                
                print(f"   • Frame total: {frame.total_frame_size} bytes")
            
            # Mostrar liveness summary
            if func_name in self.liveness:
                max_live = max(len(live_set) for live_set in self.liveness[func_name].values()) if self.liveness[func_name] else 0
                print(f"   • Máximo de variables vivas: {max_live}")
        
        print("\n" + "=" * 60)
    
    def get_all_functions(self) -> List[str]:
        """Devuelve lista de nombres de todas las funciones"""
        return list(self.functions.keys())


# ========================================
# FUNCIONES AUXILIARES PARA DEBUGGING
# ========================================

def print_liveness_table(func_name: str, func_tac: List[TACOP], liveness: Dict[int, Set[str]]) -> None:
    """
    Imprime tabla de liveness para debugging.
    
    Args:
        func_name: Nombre de la función
        func_tac: Lista de operaciones TAC
        liveness: Resultado del análisis de liveness
    """
    print(f"\n=== Liveness Table: {func_name} ===")
    print(f"{'Idx':<5} {'Instrucción':<40} {'Live Out'}")
    print("-" * 80)
    
    for i, tac_op in enumerate(func_tac):
        instr = str(tac_op)[:40]
        live_out = liveness.get(i, set())
        live_str = ', '.join(sorted(live_out)) if live_out else '∅'
        
        print(f"{i:<5} {instr:<40} {{{live_str}}}")
    
    print()
