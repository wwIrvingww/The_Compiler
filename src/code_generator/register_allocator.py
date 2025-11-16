"""
Register Allocator / Administrador de Registros para MIPS.

Responsabilidades principales:
- Mantener un mapeo entre variables/temporales y registros físicos ($t0-$t9, $s0-$s7).
- Decidir qué registro usar para cada operando/resultados de TAC.
- Reusar registros ya asignados cuando sea posible.
- Elegir víctimas para SPILL cuando no haya registros libres.
- Emitir instrucciones lw/sw para cargar o guardar valores en memoria
  (opcional, si se proporcionan offsets de stack).

Conceptos clave:

1) RegisterDescriptor:
   - Para cada registro físico, almacena:
       · qué variable/temporal contiene (o None)
       · si el valor en el registro es "dirty" (más nuevo que memoria)

2) AddressDescriptor:
   - Para cada variable/temporal, almacena los lugares donde vive:
       · conjunto de registros
       · opcionalmente el string especial 'mem' si también está en memoria

Uso típico (desde el generador de código):

    from code_generator.register_allocator import RegisterAllocator

    alloc = RegisterAllocator()

    # antes de compilar la función:
    for var_name, offset in var_offsets.items():
        alloc.bind_variable_to_memory(var_name, offset)

    # por instrucción TAC:
    reg_a, pre_a = alloc.get_register_for("a", live_out, for_read=True, for_write=False)
    reg_b, pre_b = alloc.get_register_for("b", live_out, for_read=True, for_write=False)
    reg_res, pre_r = alloc.get_register_for("t0", live_out, for_read=False, for_write=True)

    # emitir pre_a + pre_b + pre_r como lw/spill previos
    # luego generar la instrucción "add reg_res, reg_a, reg_b"
    # y marcar que reg_res fue escrito:
    alloc.mark_written(reg_res)

    # al final de la función:
    flush_code = alloc.flush_all()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class RegisterState:
    """
    Estado de un registro físico.

    Atributos:
        name: nombre del registro (ej. "$t0").
        var: nombre de la variable/temporal que vive en este registro (o None).
        dirty: True si el valor del registro es más reciente que la memoria.
    """
    name: str
    var: Optional[str] = None
    dirty: bool = False

    @property
    def is_free(self) -> bool:
        return self.var is None


class RegisterAllocator:
    """
    Administrador de registros para MIPS.

    Maneja:
      - RegisterDescriptor: Dict[reg_name, RegisterState]
      - AddressDescriptor : Dict[var_name, Set[str]]  (registros y/o "mem")

    El allocator no depende directamente de TACOP, solo de:
      - nombres de variables/temporales (strings)
      - conjuntos de variables vivas a la salida de cada instrucción (live_out)
      - offsets en el frame (opcional, para generar lw/sw reales)

    Si se proporcionan offsets de stack, se generan lw/sw de verdad.
    Si no, se emiten solo comentarios, y el integrador puede ajustar luego.
    """

    def __init__(
        self,
        available_registers: Optional[List[str]] = None,
        base_pointer: str = "$fp",
        var_offsets: Optional[Dict[str, int]] = None,
    ) -> None:
        # Configuración de registros disponibles
        if available_registers is None:
            # Conjunto típico de registros temporales + de salvado
            available_registers = [
                "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7", "$t8", "$t9",
                "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
            ]

        self.base_pointer: str = base_pointer
        self.var_offsets: Dict[str, int] = var_offsets.copy() if var_offsets else {}

        # RegisterDescriptor: reg_name -> RegisterState
        self.registers: Dict[str, RegisterState] = {
            r: RegisterState(name=r) for r in available_registers
        }

        # AddressDescriptor: var_name -> set("mem" or reg_name)
        self.address: Dict[str, Set[str]] = {}

    # ============================================================
    # BINDING CON MEMORIA
    # ============================================================

    def bind_variable_to_memory(self, var_name: str, offset: int) -> None:
        """
        Indica que una variable/temporal tiene un lugar reservado en memoria
        en offset($fp). Esto permite que el allocator genere lw/sw reales.
        """
        self.var_offsets[var_name] = int(offset)
        locs = self.address.setdefault(var_name, set())
        locs.add("mem")

    # ============================================================
    # UTILIDADES INTERNAS
    # ============================================================

    def _ensure_var_entry(self, var_name: str) -> None:
        if var_name not in self.address:
            self.address[var_name] = set()

    def _free_register(self, reg_name: str) -> None:
        reg = self.registers[reg_name]
        if reg.var is not None:
            # Quitar registro de la AddressDescriptor de la variable
            locs = self.address.get(reg.var)
            if locs is not None and reg_name in locs:
                locs.remove(reg_name)
        reg.var = None
        reg.dirty = False

    # ============================================================
    # SPILLING
    # ============================================================

    def _spill_register(self, reg_name: str) -> List[str]:
        """
        Hace SPILL del registro si es dirty y la variable tiene offset.

        Retorna las instrucciones MIPS necesarias (posiblemente lista vacía).
        """
        reg = self.registers[reg_name]
        if reg.var is None or not reg.dirty:
            return []

        var_name = reg.var
        offset = self.var_offsets.get(var_name)
        code: List[str] = []

        if offset is not None:
            # Guardar en memoria
            code.append(
                f"    sw {reg_name}, {offset}({self.base_pointer})    # spill {var_name}"
            )
            self._ensure_var_entry(var_name)
            self.address[var_name].add("mem")
        else:
            # No sabemos dónde guardar; dejamos comentario para debugging.
            code.append(
                f"    # WARNING: cannot spill {var_name} from {reg_name} (no offset)"
            )

        # Después del spill, el registro queda libre
        self._free_register(reg_name)
        return code

    def _choose_victim(self, live_out: Set[str]) -> str:
        """
        Elige un registro víctima para SPILL cuando no hay libres.

        Estrategia:
          1. Si existe un registro que esté libre, no deberíamos llegar aquí.
          2. Preferir registros cuyo contenido no esté en live_out.
          3. Si todos están en live_out, preferir aquellos con offset en memoria.
          4. Como último recurso, devolver cualquiera (puede causar pérdida si no hay offset).
        """
        # 1) no-live variables
        candidates_not_live: List[str] = []
        candidates_spillable: List[str] = []
        all_regs: List[str] = list(self.registers.keys())

        for reg_name in all_regs:
            reg = self.registers[reg_name]
            if reg.var is None:
                return reg_name
            if reg.var not in live_out:
                candidates_not_live.append(reg_name)
            elif reg.var in self.var_offsets:
                candidates_spillable.append(reg_name)

        if candidates_not_live:
            return candidates_not_live[0]
        if candidates_spillable:
            return candidates_spillable[0]
        # Peor caso: no hay buena víctima, regresamos el primero
        return all_regs[0]

    # ============================================================
    # API PRINCIPAL
    # ============================================================

    def get_register_for(
        self,
        var_name: str,
        live_out: Set[str],
        for_read: bool,
        for_write: bool,
    ) -> Tuple[str, List[str]]:
        """
        Asigna (o reutiliza) un registro para una variable/temporal.

        Parámetros:
            var_name: nombre de variable/temporal.
            live_out: conjunto de variables vivas a la salida de la instrucción actual.
            for_read: True si se necesita leer el valor actual de la variable.
            for_write: True si la instrucción va a escribir/actualizar la variable.

        Retorna:
            (reg_name, code)
            - reg_name: registro asignado
            - code: lista de instrucciones MIPS (lw/spill) que deben emitirse
                    antes de usar el registro en la instrucción actual.
        """
        self._ensure_var_entry(var_name)
        code: List[str] = []

        # 1) Si ya está en algún registro, reutilizarlo
        for reg_name, reg_state in self.registers.items():
            if reg_state.var == var_name:
                # Si necesitamos leer y no hay constancia de que esté en memoria,
                # no pasa nada: asumimos que el valor en el registro es correcto.
                return reg_name, code

        # 2) Buscar registro libre
        free_reg: Optional[str] = None
        for reg_name, reg_state in self.registers.items():
            if reg_state.is_free:
                free_reg = reg_name
                break

        # 3) Si no hay registro libre, elegir víctima y hacer SPILL si hace falta
        if free_reg is None:
            victim = self._choose_victim(live_out)
            code.extend(self._spill_register(victim))
            free_reg = victim

        # 4) En este punto, free_reg está libre
        reg_state = self.registers[free_reg]
        self._free_register(free_reg)  # por si acaso
        reg_state.var = var_name
        reg_state.dirty = False

        # Actualizar address descriptor
        self.address[var_name].add(free_reg)

        # 5) Si se necesita leer y la variable también está en memoria, cargarla
        if for_read and "mem" in self.address[var_name]:
            offset = self.var_offsets.get(var_name)
            if offset is not None:
                code.append(
                    f"    lw {free_reg}, {offset}({self.base_pointer})    # load {var_name}"
                )
            else:
                code.append(
                    f"    # WARNING: cannot load {var_name} into {free_reg} (no offset)"
                )

        # Si la variable se usará solo para escribir, no necesitamos cargar su valor previo.
        # El llamador deberá invocar mark_written() después de generar la instrucción.

        return free_reg, code

    def mark_written(self, reg_name: str) -> None:
        """
        Marca el registro como dirty después de que se haya escrito en él.
        Esto indica que su contenido es más nuevo que el de memoria.
        """
        reg = self.registers[reg_name]
        if reg.var is not None:
            reg.dirty = True
            self._ensure_var_entry(reg.var)
            # Después de escribir, el valor en memoria deja de estar sincronizado
            if "mem" in self.address[reg.var]:
                # No eliminamos 'mem' para permitir políticas más conservadoras,
                # pero si se desea estricto, se podría comentar la siguiente línea.
                # self.address[reg.var].remove("mem")
                pass

    # ============================================================
    # FLUSH FINAL
    # ============================================================

    def flush_all(self) -> List[str]:
        """
        Fuerza un SPILL de todos los registros dirty al final de la función.
        Retorna la lista de instrucciones MIPS generadas.
        """
        code: List[str] = []
        for reg_name in list(self.registers.keys()):
            code.extend(self._spill_register(reg_name))
        return code

    # ============================================================
    # DEBUG / INSPECCIÓN
    # ============================================================

    def debug_registers(self) -> str:
        """
        Devuelve una representación de la tabla de registros,
        útil para debugging.
        """
        lines: List[str] = []
        for reg_name, state in self.registers.items():
            if state.var is None:
                lines.append(f"{reg_name}: free")
            else:
                tag = "dirty" if state.dirty else "clean"
                lines.append(f"{reg_name}: {state.var} ({tag})")
        return "\n".join(lines)

    def debug_address(self) -> str:
        """
        Devuelve una representación de la AddressDescriptor,
        útil para debugging.
        """
        lines: List[str] = []
        for var_name, locs in sorted(self.address.items()):
            locs_str = ", ".join(sorted(locs)) if locs else "∅"
            lines.append(f"{var_name}: {{{locs_str}}}")
        return "\n".join(lines)
