# Recursion y definicion interna funcional!

function a(){
    function b(){
        a();
    }
    b();
}
a();

let z = [1,2,3];