function fib(n: integer): integer{
    if (n <= 1){
        return 1;
    } else{
        let a = fib(n-1);
        let b = fib(n-2);
        return a + b;
    }
}

let f = fib(10);
print(f);