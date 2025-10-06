# tests/test_tac_classes.py
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from src.parser.CompiscriptLexer import CompiscriptLexer
from src.parser.CompiscriptParser import CompiscriptParser
from src.semantic.ast_and_semantic import AstAndSemantic
from src.intermediate.tac_generator import TacGenerator

def _tac(code: str):
    input_stream = InputStream(code)
    lx = CompiscriptLexer(input_stream)
    ts = CommonTokenStream(lx)
    ps = CompiscriptParser(ts)
    tree = ps.program()

    sem = AstAndSemantic()
    ParseTreeWalker().walk(sem, tree)
    assert sem.errors == [], f"Semánticos: {sem.errors}"

    gen = TacGenerator(sem.table)
    gen.visit(tree)
    get_code = getattr(gen, "get_code", None)
    return get_code() if callable(get_code) else gen.code

def test_tac_class_decl_simple():
    code = """
    class Persona {
        var nombre: string;
        var edad: integer;

        function saludar() {
            print(this.nombre);
        }
    }
    """
    tac = _tac(code)

    # 1) Cabecera y cierre de clase
    has_class     = any(i.op == "class"    and i.arg1 == "Persona" for i in tac)
    has_endclass  = any(i.op == "endclass" and i.arg1 == "Persona" for i in tac)
    assert has_class,    "Debe emitir op='class' con arg1='Persona'"
    assert has_endclass, "Debe emitir op='endclass' con arg1='Persona'"

    # 2) Atributos de clase
    has_attr_nom  = any(i.op == "attr" and i.arg1 == "Persona" and i.arg2 == "nombre" for i in tac)
    has_attr_edad = any(i.op == "attr" and i.arg1 == "Persona" and i.arg2 == "edad"   for i in tac)
    assert has_attr_nom,  "Debe emitir 'attr' para 'nombre'"
    assert has_attr_edad, "Debe emitir 'attr' para 'edad'"

    # 3) Método mapeado a label de entrada (method Persona.saludar → label)
    meth_map = next((i for i in tac if i.op == "method" and i.arg1 == "Persona" and i.arg2 == "saludar"), None)
    assert meth_map is not None, "Debe emitir 'method' con (Persona, saludar, entry_label)"
    entry_label = meth_map.result
    assert entry_label and "saludar_entry" in entry_label, "El 'result' del method debe ser el label de entrada"

    # === DEBUG: inspeccionar labels antes de los asserts de la sección 4 ===
    labels = [i for i in tac if i.op == "label"]
    print("ALL LABELS:", [(i.result, type(i.result)) for i in labels])
    bad = [i for i in labels if isinstance(i.result, tuple)]
    if bad:
        print("LABELS con tupla:", [(i.result, type(i.result)) for i in bad])

    # 4) Labels del cuerpo del método: entry/exit
    has_entry_label = any(i.op == "label" and i.result == entry_label for i in tac)
    has_exit_label  = any(i.op == "label" and i.result and i.result.endswith("saludar_exit") for i in tac)
    assert has_entry_label, f"Debe existir label de entrada '{entry_label}'"
    assert has_exit_label,  "Debe existir label de salida '*saludar_exit'"
