// # =======================
// #    1. Fors y prints
// # =======================
for (let i = 1; i <= 20; i = i + 1){
    let b = i * i;
    print(i);
    print(", ");
    print(b);
    print("\n");
}

// # =======================
// #    2. funciones simples
// # =======================
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

// # =======================
// #    3. ifs simples
// # =======================

let p = 0;
for (let i = 0; i < 30; i = i + 1){
    if (i % 3 == 0){
        p = i * i;
        print(i);
        print("^2 is ");
        print(p);
        print("\n");
    } else{
        print(i);
        print(" is not divisible by 3\n");
    }
}

// # =======================
// #    4. arrays simples
// # =======================

let arr = [1,3,51,2,52,68,1,734];
let l = len(arr);

for (let i = 0; i< l, i = i +1){
    print(arr[i]);
}