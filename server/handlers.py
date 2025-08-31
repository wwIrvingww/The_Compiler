# server/handlers.py
from pygls.lsp.types import Diagnostic, DiagnosticSeverity, Range, Position
import re

_LINE_RE = re.compile(r"\[linea\s+(\d+)\]")  # extrae el número de línea de mensajes como "[linea 3] ..."

def build_diagnostics(text: str, errors: list[str]) -> list[Diagnostic]:
    lines = text.splitlines()
    out: list[Diagnostic] = []
    for msg in errors:
        m = _LINE_RE.search(msg)
        line_idx = max(int(m.group(1)) - 1, 0) if m else 0
        start = Position(line=line_idx, character=0)
        end = Position(
            line=line_idx,
            character=len(lines[line_idx]) if 0 <= line_idx < len(lines) else 0,
        )
        out.append(Diagnostic(
            range=Range(start=start, end=end),
            message=msg,
            severity=DiagnosticSeverity.Error,
            source="compiscript",
        ))
    return out
