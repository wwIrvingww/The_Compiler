// control_flujo.cps
// ========================================================
// 1) Condiciones en if / while / do-while / for / switch
//    deben ser booleanas
// ========================================================

// --- IF ---
if (8):
    print              // ❌ Esperado: condicion de 'if' no es boolean: '8'

if (true):
    print              // ✅ no error

// --- WHILE ---
while (0):
    print              // ❌ Esperado: condicion de 'while' no es boolean: '0'

while (false):
    print              // ✅ no error

// --- FOR ---
for (1):
    print              // ❌ Esperado: condicion de 'for' no es boolean: '1'

let i: integer = 0;
for (i = 0; i; i = i + 1):
    print              // ❌ Esperado: condicion de 'for' no es boolean: 'i'

for (i = 0; true; i = i + 1):
    break              // ✅ condición booleana

// --- DO-WHILE ---
do:
    print
while (0);             // ❌ Esperado: condicion de 'while' no es boolean: '0'

do:
    print
while (true);          // ✅

// --- SWITCH ---
switch (1):            // ❌ si tu regla exige boolean, aquí debe marcar
    case true:
        print
    default:
        print

switch (false):        // ✅
    default:
        print



// ========================================================
// 2) Validar que break / continue solo dentro de bucles
// ========================================================

break;                 // ❌ Esperado: 'break' fuera de bucle
continue;              // ❌ Esperado: 'continue' fuera de bucle

while (true):
    break              // ✅ permitido en bucle

while (true):
    continue           // ✅ permitido en bucle



// ========================================================
// 3) Validar que return esté dentro de una función
// ========================================================

return 5;              // ❌ Esperado: 'return' fuera de funcion'

// Válido: return dentro de función
function id(x: integer): integer {
    return x;          // ✅
}

// Extra: return dentro de bucle (válido porque está dentro de función)
function first(): integer {
    while (true):
        return 1       // ✅
}
