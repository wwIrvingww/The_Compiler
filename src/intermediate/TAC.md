# 🧠 Formato del Código Intermedio (TAC)

## 🏗️ Estructura General

Cada instrucción del TAC (Three Address Code) se representa con una **cuádrupla** de la forma:

```
(op, arg1, arg2, result)
```

Donde:

| Campo      | Descripción                                                                       |
| ---------- | --------------------------------------------------------------------------------- |
| **op**     | Operación u opcode a ejecutar (ej. `+`, `-`, `=`, `goto`, `if-goto`, `len`, etc.) |
| **arg1**   | Primer argumento (constante, identificador, o temporal).                          |
| **arg2**   | Segundo argumento (si aplica, p.ej. operaciones binarias).                        |
| **result** | Resultado destino o etiqueta (variable, temporal, o label).                       |

Ejemplo:

```
+, a, b, t0     ; t0 = a + b
=, t0, -, x     ; x = t0
```

---

## ⚙️ Conjunto de **Operaciones Soportadas**

### 🔢 1. Aritméticas y Lógicas

| Operador    | Descripción     | Ejemplo TAC                  |
| ----------- | --------------- | ---------------------------- |
| `+`         | Suma            | `+, a, b, t1` → `t1 = a + b` |
| `-`         | Resta           | `-, a, b, t2` → `t2 = a - b` |
| `*`         | Multiplicación  | `*, a, b, t3`                |
| `/`         | División        | `/, a, b, t4`                |
| `%`         | Módulo          | `%, a, b, t5`                |
| `uminus`    | Negación unaria | `uminus, a, -, t6`           |
| `!` / `not` | Negación lógica | `not, cond, -, t7`           |

---

### 🧩 2. Comparaciones

| Operador | Descripción   | Ejemplo         |           |   |   |              |
| -------- | ------------- | --------------- | --------- | - | - | ------------ |
| `==`     | Igual         | `==, a, b, t8`  |           |   |   |              |
| `!=`     | Distinto      | `!=, a, b, t9`  |           |   |   |              |
| `<`      | Menor que     | `<, a, b, t10`  |           |   |   |              |
| `<=`     | Menor o igual | `<=, a, b, t11` |           |   |   |              |
| `>`      | Mayor que     | `>, a, b, t12`  |           |   |   |              |
| `>=`     | Mayor o igual | `>=, a, b, t13` |           |   |   |              |
| `&&`     | AND lógico    | `&&, a, b, t14` |           |   |   |              |
| `        |               | `               | OR lógico | ` |   | , a, b, t15` |

---

### 📝 3. Asignación y Movimiento

| Operador  | Descripción                 | Ejemplo                                |
| --------- | --------------------------- | -------------------------------------- |
| `=`       | Asignación simple           | `=, b, -, a` → `a = b`                 |
| `setprop` | Asignar propiedad de objeto | `setprop, obj, x, val` → `obj.x = val` |
| `getidx`  | Obtener índice de arreglo   | `getidx, arr, i, t1` → `t1 = arr[i]`   |
| `len`     | Longitud de arreglo         | `len, arr, -, t2` → `t2 = len(arr)`    |

---

### 🔁 4. Control de Flujo

| Operador  | Descripción            | Ejemplo                |
| --------- | ---------------------- | ---------------------- |
| `label`   | Define una etiqueta    | `label, -, -, L1`      |
| `goto`    | Salto incondicional    | `goto, L1, -, -`       |
| `if-goto` | Salto condicional      | `if-goto, cond, L2, -` |
| `return`  | Retorna de una función | `return, t0, -, -`     |

> 💡 Las etiquetas (`L0`, `L1`, `L2`, …) se generan automáticamente por el `LabelGenerator` y marcan los puntos de salto.

---

### 🧮 5. Arrays y Propiedades

| Operador         | Descripción               | Ejemplo                              |
| ---------------- | ------------------------- | ------------------------------------ |
| `getidx`         | Accede a un elemento      | `getidx, arr, i, t0` → `t0 = arr[i]` |
| `setprop`        | Asigna propiedad a objeto | `setprop, obj, field, val`           |
| `len`            | Obtiene longitud          | `len, arr, -, t1`                    |
| `new` *(futuro)* | Instancia objeto/clase    | `new, Class, -, t0`                  |

---

### 🧠 6. Temporales y Etiquetas

| Elemento                   | Descripción                                  |
| -------------------------- | -------------------------------------------- |
| **t0, t1, t2…**            | Temporales generados por el `TempAllocator`. |
| **L0, L1, L2…**            | Etiquetas generadas por el `LabelGenerator`. |
| **func_name_entry / exit** | Marcadores de entrada/salida de funciones.   |
