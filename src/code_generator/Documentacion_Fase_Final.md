# 🧩 Compiscript Compiler – Backend MIPS

### **Documentación de Arquitectura y Ejecución**

Este documento describe la arquitectura completa del backend de generación de código del compilador **Compiscript**, así como las instrucciones para ejecutar el proyecto. Incluye detalles de los módulos implementados, flujo interno, manejo de TAC, administración de registros y generación final de código MIPS ejecutable.

---

# 📁 Estructura General del Proyecto

```
THE_COMPILER/
│── src/
│   ├── ast_nodes.py
│   ├── parser/                  ← Gramática ANTLR y parser
│   ├── semantic/                ← Análisis semántico
│   ├── intermediate/
│   │   ├── tac_generator.py     ← Código intermedio (TAC)
│   ├── code_generator/
│   │   ├── pre_analysis.py      ← Pre–análisis por función
│   │   ├── mips_generator.py    ← Traducción TAC → MIPS
│   │   ├── register_allocator.py← Asignación de registros (getReg)
│   │   ├── procedure_manager.py ← Prólogos, epílogos, frames
│   │   └── runtime_integration.py
│   ├── symbol_table/
│   ├── CompilerServer.py
│   └── DriverGen.py             ← Punto principal para TAC + MIPS
│
│── input.cps                    ← Programa de entrada
│── input.cps.asm                ← Código MIPS generado
│── docker-compose.yaml
│── Dockerfile
│── scripts/run_compile.sh       ← Ejecución final automatizada
```

---

# 🧠 Arquitectura del Backend

El backend está compuesto por **tres módulos principales**, cada uno encargado de una parte esencial del proceso de traducción desde TAC a MIPS:

---

## 🔴 1. Procedure Manager – Manejo de llamadas, retornos y stack frames

📌 Archivo: `src/code_generator/procedure_manager.py`

Este módulo genera automáticamente la estructura estándar de una función en MIPS:

### **PRÓLOGO**

Incluye:

* Reserva de espacio en el stack
* Salvado de `$ra` y `$fp`
* Actualización del frame pointer
* Salvado de registros `$s` si la función los usa

Ejemplo generado:

```mips
addiu $sp, $sp, -12
sw $ra, 0($sp)
sw $fp, 4($sp)
move $fp, $sp
```

### **STACK FRAME**

El frame de cada función mantiene:

```
(fp+0)   ← return address (RA) salvado
(fp+4)   ← old frame pointer (FP)
(fp–4)   ← local 1
(fp–8)   ← local 2
...
(sp)    ← registros salvados y temporales
```

Acceso consistente a variables sin importar anidación o recursión.

### **EPÍLOGO**

Restaura:

* Registro `$fp`
* Registro `$ra`
* Registros `$s` usados
* Tamaño del frame

Ejemplo:

```mips
lw $fp, 4($sp)
lw $ra, 0($sp)
addiu $sp, $sp, 12
jr $ra
```

---

## 🔵 2. Register Allocator – Mapeo TAC → REGISTROS MIPS

📌 Archivo: `src/code_generator/register_allocator.py`

Implementa el sistema de asignación de registros `getReg()`.

### Componentes principales:

#### ✔ RegisterDescriptor

Mapea:

```
registro → variable que contiene
dirty → ¿se modificó y debe guardarse?
```

#### ✔ AddressDescriptor

Mapea:

```
variable → {registros donde vive, memoria}
```

### Estrategia de selección:

1. **¿El operando ya tiene un registro asignado?**
   → Reutilizarlo.

2. **¿Hay registros libres?**
   → Asignar uno, priorizando `$t0–$t9`.

3. **¿Todos ocupados? → SPILL**

   * Escoger víctima LRU
   * Si dirty → `sw offset($fp)`
   * Cargar nueva variable si vive en memoria (`lw`)

### Ejemplo:

TAC:

```
t3 = t1 * t2
```

Asignación:

```mips
mul $t3, $t1, $t2
```

---

## 🟢 3. Generador de Código MIPS

📌 Archivo: `src/code_generator/mips_generator.py`

Traduce cada instrucción TAC a una secuencia equivalente en MIPS.

### Operaciones soportadas:

#### ✔ Aritméticas

```
t = a + b   → add
t = a - b   → sub
t = a * b   → mul
```

#### ✔ Relacionales

```
t = a < b   → slt
t = a == b  → seq
```

#### ✔ Lógicos con cortocircuito (&&, ||)

Genera secuencias con condicionales.

#### ✔ Control de Flujo

TAC:

```
if t goto L1
goto L2
```

MIPS:

```mips
bne $t, $zero, L1
j L2
```

#### ✔ Llamadas a funciones

* Prepara `$a0–$a3`
* Ejecuta `jal`
* Obtiene retorno desde `$v0`

---

# 🔧 4. Pre-Analysis

📌 Archivo: `src/code_generator/pre_analysis.py`

Antes de generar MIPS, el compilador analiza:

1. **Tabla de funciones**
2. **Tamaño del frame por función**
3. **Liveness de variables**
4. **Qué registros `$s` usa la función**
5. **Dependencias entre funciones**

Este módulo produce la metadata que el Procedure Manager y el Register Allocator necesitan.

Ejemplo en consola:

```
[1/4] Identificando funciones... ✓
[2/4] Calculando tamaños de frames... ✓
[3/4] Analizando liveness... ✓
[4/4] Detectando uso de registros $s... ✓
```

---

# 🧩 5. Runtime Integration

📌 Archivo: `src/code_generator/runtime_integration.py`

Se encarga de:

* Manejar `.data` (strings, variables globales)
* Colocar `.text` y el símbolo `main`
* Integrar prolog/epilog
* Preparar las syscalls (`print`, `len`, strings, etc.)

---

# 🔄 Flujo Completo del Backend

```
input.cps
     ↓
TAC Generator (intermediate/)
     ↓
Pre-Analysis (pre_analysis.py)
     ↓
Procedure Manager (prólogos/epílogos)
     ↓
Register Allocator (getReg, spill, live ranges)
     ↓
MIPS Generator (traducción TAC → instrucciones)
     ↓
runtime_integration.py
     ↓
input.cps.asm  ← archivo final listo para MARS/SPIM
```

---

# ▶️ Cómo Ejecutar el Compilador

El proyecto funciona **enteramente desde Docker**, usando un solo comando.

### 1. Compilar y correr el contenedor

```bash
docker-compose run dev
```

Entrarás dentro del contenedor en `/app`.

### 2. Ejecutar la fase completa del compilador

```bash
scripts/run_compile.sh
```

Este script realiza:

1. Ejecutar DriverGen.py
2. Generar TAC
3. Generar MIPS
4. Guardar la salida en:

```
input.cps.pretty_tac
input.cps.raw_tac
input.cps.asm
```

---

# 🧪 Ejemplo de Ejecución

### **Entrada (input.cps)**

```cps
function get_squared(n: integer): integer{
    return n * n;
}

function print_sq(a: integer, n: integer){
    print(a);
    print("^2 is ");
    print(n);
    print("\n");
}

let a = get_squared(13);
print_sq(13, a);

let b = get_squared(65);
print_sq(65, b);
```

### **Salida generada (input.cps.asm)**

(Extracto)

```mips
func_get_squared:
    addiu $sp, $sp, -12
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp

    move $t0, $a0
    mul $t1, $t0, $t0
    move $v0, $t1

    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 12
    jr $ra
```

```mips
func_main:
    li $t0, 13
    move $a0, $t0
    jal func_get_squared
    move $t1, $v0

    li $t2, 13
    move $a0, $t2
    move $a1, $t1
    jal func_print_sq
```
