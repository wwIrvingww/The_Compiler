# server/server.py
# --- bootstrap sys.path para que 'parser' (en src/) sea importable ---
import os, sys
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))          # .../server
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, os.pardir))# repo root
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
# Asegura que src/ y server/ estén en sys.path
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import sys
import logging
import pathlib

from pygls.server import LanguageServer
from pygls.lsp.types import SemanticTokensLegend, SemanticTokensParams, SemanticTokens, SemanticTokensRegistrationOptions
from handlers import SEM_LEGEND, build_semantic_tokens
from pygls.uris import to_fs_path
from urllib.parse import urlparse, unquote

from handlers import SEM_LEGEND, build_semantic_tokens
from pygls.lsp.methods import TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL
from pygls.lsp.types import SemanticTokensParams, SemanticTokens
from pygls.lsp.types import Diagnostic, DiagnosticSeverity, Range, Position






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

def uri_to_path(uri: str) -> str:
    # convierte file:///C:/... en C:\...
    p = unquote(urlparse(uri).path)
    # En Windows pygls/URI suele venir con una barra inicial: /C:/Users/...
    if p.startswith('/') and len(p) > 2 and p[2] == ':':
        p = p[1:]
    return p

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
    try:
        path = uri_to_path(uri)
        with open(path, "r", encoding="utf8") as f:
            code = f.read()
    except Exception as e:
        log.exception("could not read file on didSave")
        code = ""
    validate_and_publish(uri, code)

@ls.feature(
    TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    SemanticTokensRegistrationOptions(legend=SEM_LEGEND, full=True)
)
def semantic_tokens_full(params: SemanticTokensParams) -> SemanticTokens:
    doc = ls.workspace.get_document(params.text_document.uri)
    return build_semantic_tokens(doc.source)


def build_diagnostics(text: str, errors: list[str]) -> list[Diagnostic]:
    import re
    diags: list[Diagnostic] = []
    lines = text.splitlines()

    for msg in errors:
        # intenta extraer la línea: "[linea 3]" o "línea 3"
        m = re.search(r"(?:\[\s*linea\s*(\d+)\s*\])|(?:l[íi]nea\s+(\d+))", msg, re.IGNORECASE)
        line = (int(next(g for g in m.groups() if g)) - 1) if m else 0

        # intenta subrayar el lexema entre comillas '...'
        start_col = 0
        end_col = 1
        if 0 <= line < len(lines):
            lex = None
            t = re.search(r"'([^']+)'", msg)
            if t:
                lex = t.group(1)
            if lex is not None:
                pos = lines[line].find(lex)
                if pos >= 0:
                    start_col = pos
                    end_col = pos + len(lex)
                else:
                    end_col = max(1, len(lines[line]))
            else:
                end_col = max(1, len(lines[line]))

        diags.append(Diagnostic(
            range=Range(
                start=Position(line=line, character=start_col),
                end=Position(line=line, character=end_col)
            ),
            message=msg,
            severity=DiagnosticSeverity.Error
        ))
    return diags


def validate_and_publish(uri: str, code: str):
    diagnostics: list[Diagnostic] = []
    try:
        from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
        from parser.CompiscriptLexer import CompiscriptLexer
        from parser.CompiscriptParser import CompiscriptParser
        from semantic.ast_and_semantic import AstAndSemantic

        log.debug("Starting parse/validate for uri=%s (code length=%d)", uri, len(code or ""))
        input_stream = InputStream(code)
        lexer = CompiscriptLexer(input_stream)
        tokens = CommonTokenStream(lexer)
        parser = CompiscriptParser(tokens)
        tree = parser.program()

        # Validador semántico principal (único)
        walker = ParseTreeWalker()
        listener = AstAndSemantic()
        walker.walk(listener, tree)
        all_errs = listener.errors or []
        log.debug("AstAndSemantic returned %d errors: %r", len(all_errs), all_errs)

        # Construir diagnósticos
        try:
            diagnostics = build_diagnostics(code, all_errs)
        except Exception:
            log.exception("build_diagnostics failed")
            diagnostics = [make_diag_from_error(e) for e in all_errs]

    except Exception as ex:
        msg = f"Parser/server error: {ex}"
        diagnostics.append(make_diag_from_error(msg))
        log.exception("validate error")

    ls.publish_diagnostics(uri, diagnostics)
    log.debug("Published %d diagnostics for %s", len(diagnostics), uri)


if __name__ == "__main__":
    try:
        ls.start_io()
    except Exception:
        log.exception("LSP server crashed")
