class Animal{
    var especie: string;
    function constructor(esp: string){
        this.especie = esp;
    }
}
class Dog: Animal{
    var raza: string;
}

let d = new Dog("perro");
d.raza = "Terrier";