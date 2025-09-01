import pytest
from antlr4 import InputStream, CommonTokenStream
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser
from semantic.ast_and_semantic import AstAndSemantic  # tu AstAndSemantic en src/semantic.py

def run_semantic(code: str):
    """Helper: parsea y devuelve errores y AST."""
    lexer = CompiscriptLexer(InputStream(code))
    parser = CompiscriptParser(CommonTokenStream(lexer))
    tree = parser.program()
    sem = AstAndSemantic()
    from antlr4 import ParseTreeWalker
    ParseTreeWalker().walk(sem, tree)
    return sem.errors, sem.ast.get(tree)


# ---------------- CASOS POSITIVOS ---------------- #

def test_class_with_constructor_and_method():
    code = """
    class Persona {
        var nombre: string;
        var edad: integer;

        function constructor(nombre: string, edad: integer) {
            this.nombre = nombre;
            this.edad = edad;
        }

        function saludar() {
            print("Hola " + this.nombre);
        }
    }

    let p = new Persona("Diego", 21);
    p.saludar();
    """
    errors, ast = run_semantic(code)
    assert errors == []   # no debe haber errores semánticos


# ---------------- CASOS NEGATIVOS ---------------- #

def test_access_to_nonexistent_property():
    code = """
    class A {
        var x: integer;
    }
    let a = new A(1);
    let y = a.y;  // 'y' no existe
    """
    errors, _ = run_semantic(code)
    assert any("no existe" in e for e in errors)

def test_this_outside_class():
    code = """
    function f() {
        let x = this;  // this fuera de clase
    }
    """
    errors, _ = run_semantic(code)
    assert any("this" in e for e in errors)

def test_wrong_constructor_args():
    code = """
    class B {
        function constructor(x: integer) {
            this.x = x;
        }
    }
    let b = new B(); // faltan args
    """
    errors, _ = run_semantic(code)
    assert any("Constructor" in e for e in errors)