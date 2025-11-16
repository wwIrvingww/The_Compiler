function fib(n: integer): integer{
    if (n <= 1){
        return n;
    }
    else{
        let val = fib(n-1) + fib(n-2);
        print(val);
        return val;
    }
}

let ret = fib(10);
print(ret);