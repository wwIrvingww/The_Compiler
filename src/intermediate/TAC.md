# 📄 Formato del Código Intermedio (TAC)

## 🏗️ Estructura del TAC

Cada instrucción se representa como una **tripleta**:

```
(op, arg1, arg2, result)
```

* **op** → operación u opcode (ej. `+`, `-`, `*`, `/`, `=`, `goto`, `ifgoto`, etc.)
* **arg1** → primer operando (puede ser constante, identificador, temporal)
* **arg2** → segundo operando (opcional)
* **result** → variable destino (temporal o identificador final)

Ejemplo:

```
(*, a, a, t1)       ; t1 = a * a
(=, t1, -, x)       ; x = t1
```

---

## 🧩 Conjunto de **Opcodes Soportados**

### Aritméticos

* `add` → suma (`+`)
* `sub` → resta (`-`)
* `mult` → multiplicación (`*`)
* `div` → división (`/`)
* `uminus` → negación unaria (`-x`)

### Asignación y movimiento

* `=` → asignación (`x = y`)
* `move` → mover valores entre temporales (`t1 = t2`)

### Comparaciones

* `eq` → igual (`==`)
* `neq` → distinto (`!=`)
* `lt` → menor (`<`)
* `le` → menor o igual (`<=`)
* `gt` → mayor (`>`)
* `ge` → mayor o igual (`>=`)

### Control de flujo

* `goto L` → salto incondicional
* `ifgoto` → salto condicional (`if x goto L`)
* `ifFalsegoto` → salto condicional negado

### Funciones

* `param x` → pasar parámetro
* `call f, n` → llamada a función con `n` argumentos
* `return x` → retornar valor

### Memoria y arreglos

* `load` → cargar de memoria
* `store` → guardar en memoria
* `[]=` → asignar en arreglo
* `=[]` → leer de arreglo

---

## 🔖 Temporales y Etiquetas

* **Temporales (`t0, t1, t2...`)** → generados automáticamente por el compilador para resultados intermedios.
* **Etiquetas (`L0, L1, L2...`)** → marcan puntos de salto en `if`, `while`, `for`.

---

## 📌 Ejemplo

Código fuente:

```c
let x = 2 * 2;
```

TAC:

```
t0 = 2
t1 = 2
t2 = t0 * t1
x  = t2
```

Tripletas:

```
(*, 2, 2, t2)
(=, t2, -, x)
```