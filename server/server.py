# server/server.py
import sys
import logging
import pathlib

from pygls.server import LanguageServer
from pygls.lsp.types import Diagnostic, DiagnosticSeverity, Position, Range

# Asegura que se pueda importar tu paquete src/
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from semantic.flow_validator import FlowValidator

logging.basicConfig(filename="lsp_server.log", level=logging.DEBUG, filemode="w")
log = logging.getLogger(__name__)

ls = LanguageServer("compiscript-ls", "v0.1")

def make_diag_from_error(msg: str):
    import re
    m = re.search(r"línea\s+([0-9]+)", msg)
    line = int(m.group(1)) - 1 if m else 0
    start = Position(line=line, character=0)
    end = Position(line=line, character=200)
    return Diagnostic(range=Range(start=start, end=end),
                      message=msg,
                      severity=DiagnosticSeverity.Error)

@ls.feature('textDocument/didOpen')
def did_open(ls, params):
    uri = params.text_document.uri
    code = params.text_document.text
    validate_and_publish(uri, code)

@ls.feature('textDocument/didChange')
def did_change(ls, params):
    uri = params.text_document.uri
    changes = params.content_changes
    if changes and getattr(changes[0], "text", None) is not None:
        code = changes[0].text
    else:
        code = ""
    validate_and_publish(uri, code)

@ls.feature('textDocument/didSave')
def did_save(ls, params):
    uri = params.text_document.uri
    path = ls.uri_to_path(uri)
    with open(path, "r", encoding="utf8") as f:
        code = f.read()
    validate_and_publish(uri, code)

def validate_and_publish(uri: str, code: str):
    diagnostics = []
    try:
        from antlr4 import InputStream, CommonTokenStream
        from parser.CompiscriptLexer import CompiscriptLexer
        from parser.CompiscriptParser import CompiscriptParser

        input_stream = InputStream(code)
        lexer = CompiscriptLexer(input_stream)
        tokens = CommonTokenStream(lexer)
        parser = CompiscriptParser(tokens)
        tree = parser.program()

        flow_errs = FlowValidator.validate(tree)
        for e in flow_errs:
            diagnostics.append(make_diag_from_error(e))

    except Exception as ex:
        diagnostics.append(make_diag_from_error(f"Parser/server error: {ex}"))
        log.exception("validate error")

    ls.publish_diagnostics(uri, diagnostics)

if __name__ == "__main__":
    try:
        ls.start_io()
    except Exception:
        log.exception("LSP server crashed")
