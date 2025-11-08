
function sum(n: integer): integer{
    if (n <=1){
        return 1;
    } else{
        return 1 + sum(n-1);
    }
}

var res = sum(10);