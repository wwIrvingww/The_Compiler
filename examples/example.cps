// Caso 1: variable no declarada
b = 10;   // ❌ debería marcar: variable 'b' no declarada

// Caso 2: redeclaración de variable en mismo ámbito
let a: integer = 1;
let a: integer = 2;   // ❌ ya está definido en el ambito actual

// Caso 3: función redeclarada
function f(x: integer): integer {
    return x;
}
function f(y: integer): integer {  // ❌ redeclaración de función 'f'
    return y;
}
// Caso 4: return fuera de función
return 5;  // ❌ 'return' fuera de funcion
// Caso 5: if 
if (8):
    print
while (8):
for (8):
// Caso correcto: declaración y uso
let c: integer = 5;
c = 7;  // ✅ no debería marcar error
