# server/handlers.py
from __future__ import annotations

import re
from typing import List, Tuple

# Diagnósticos (como ya lo tenías)
from pygls.lsp.types import Diagnostic, DiagnosticSeverity, Range, Position

# --- Semantic tokens (para coloring) ---
from pygls.lsp.types import (
    SemanticTokensLegend,
    SemanticTokens,
)
# no usamos SemanticTokenTypes por compatibilidad entre versiones

# ANTLR y tu parser
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker, ParseTreeListener
from parser.CompiscriptLexer import CompiscriptLexer
from parser.CompiscriptParser import CompiscriptParser


# -------------------------
# 1) Construcción de diagnósticos
# -------------------------

# server/handlers.py
from pygls.lsp.types import Diagnostic, DiagnosticSeverity, Range, Position
import re

# Acepta tanto "[linea N]" como "[line N]"
_LINE_RE = re.compile(r"\[(?:linea|line)\s+(\d+)\]", re.IGNORECASE)

# Para resaltar solo el fragmento entre comillas si existe: 'ident', '8', etc.
_SNIPPET_RE = re.compile(r"'([^']+)'")

def build_diagnostics(text: str, errors: list[str]) -> list[Diagnostic]:
    lines = text.splitlines()
    out: list[Diagnostic] = []

    for msg in errors:
        # 1) línea (1-based -> 0-based)
        m = _LINE_RE.search(msg)
        line_idx = max(int(m.group(1)) - 1, 0) if m else 0

        # 2) columna: intenta resaltar el 'snippet' si el msg lo trae en comillas
        start_char = 0
        end_char = len(lines[line_idx]) if 0 <= line_idx < len(lines) else 0

        n = _SNIPPET_RE.search(msg)
        if n and 0 <= line_idx < len(lines):
            snippet = n.group(1)
            col = lines[line_idx].find(snippet)
            if col != -1:
                start_char = col
                end_char = col + len(snippet)

        out.append(Diagnostic(
            range=Range(
                start=Position(line=line_idx, character=start_char),
                end=Position(line=line_idx, character=end_char),
            ),
            message=msg,
            severity=DiagnosticSeverity.Error,
            source="compiscript",
        ))

    return out


# -------------------------
# 2) Semantic Highlighting (coloring) - builder local compatible con LSP
# -------------------------

# Legend con STRINGS para máxima compatibilidad
SEM_LEGEND = SemanticTokensLegend(
    token_types=[
        "variable",   # index 0
        "function",   # index 1
        "parameter",  # index 2
    ],
    token_modifiers=[],
)

class SimpleSemanticTokensBuilder:
    """
    Construye la lista de enteros para SemanticTokens (LSP):
    Cada token -> [deltaLine, deltaStart, length, tokenType, tokenModifiers]
    """

    def __init__(self, legend: SemanticTokensLegend):
        self._legend = legend
        # mapa token type string -> index (según el orden de la leyenda)
        self._type_to_index = {t: i for i, t in enumerate(self._legend.token_types)}
        self._tokens: List[Tuple[int, int, int, int, int]] = []

    def push(self, line: int, char: int, length: int, token_type: str, modifiers: List[str] = None):
        """
        Añade un token con coordenadas (line 0-based, char 0-based).
        token_type debe ser uno de los strings de la leyenda (ej. 'variable').
        modifiers se ignoran en esta versión (se pueden mapear a bitmask si hace falta).
        """
        if token_type not in self._type_to_index:
            return
        idx = self._type_to_index[token_type]
        modbits = 0  # no usamos modificadores por ahora
        self._tokens.append((line, char, length, idx, modbits))

    def build(self) -> List[int]:
        # ordenar por (line, char)
        self._tokens.sort(key=lambda t: (t[0], t[1]))
        data: List[int] = []
        prev_line = 0
        prev_char = 0
        first = True
        for (line, char, length, ttype, tmod) in self._tokens:
            if first:
                delta_line = line
                delta_start = char
                first = False
            else:
                delta_line = line - prev_line
                delta_start = char if delta_line != 0 else (char - prev_char)
            data.extend([delta_line, delta_start, length, ttype, tmod])
            prev_line = line
            prev_char = char
        return data


class _SemTokListener(ParseTreeListener):
    """
    Listener mínimo que marca:
      - variables: nombre en declaración `let a : T ...` (enterVariableDeclaration)
      - funciones: nombre en `function f(...) ...` (enterFunctionDeclaration)
      - parámetros: cuando la gramática expone Identifiers en la función
    Ajusta los nombres de métodos si tu gramática usa otras reglas.
    """

    def __init__(self, builder: SimpleSemanticTokensBuilder):
        self.b = builder

    def enterVariableDeclaration(self, ctx):
        try:
            if hasattr(ctx, "Identifier") and ctx.Identifier():
                ids = ctx.Identifier()
                name_node = ids[0] if isinstance(ids, list) else ids
                # obtener token de ANTLR
                tok = None
                try:
                    tok = name_node.getSymbol()
                except Exception:
                    tok = getattr(name_node, 'symbol', None)
                if not tok:
                    # fallback a usar getText() y posición del ctx
                    text = name_node.getText()
                    line = getattr(ctx.start, "line", 1) - 1
                    col = getattr(ctx.start, "column", 0)
                    self.b.push(line, col, len(text), "variable")
                else:
                    text = getattr(tok, 'text', None) or name_node.getText()
                    line = max(getattr(tok, 'line', getattr(ctx.start, 'line', 1)) - 1, 0)
                    col = getattr(tok, 'column', getattr(ctx.start, 'column', 0))
                    self.b.push(line, col, len(text), "variable")
        except Exception:
            pass

    def enterFunctionDeclaration(self, ctx):
        try:
            if hasattr(ctx, "Identifier") and ctx.Identifier():
                ids = ctx.Identifier()
                # suponemos convención: primer Identifier -> nombre función, siguientes -> parámetros
                if isinstance(ids, list) and ids:
                    fn_node = ids[0]
                    tok = None
                    try:
                        tok = fn_node.getSymbol()
                    except Exception:
                        tok = getattr(fn_node, 'symbol', None)
                    if tok:
                        ftext = getattr(tok, 'text', None) or fn_node.getText()
                        fline = max(getattr(tok, 'line', getattr(ctx.start, 'line', 1)) - 1, 0)
                        fcol = getattr(tok, 'column', getattr(ctx.start, 'column', 0))
                        self.b.push(fline, fcol, len(ftext), "function")
                    else:
                        # fallback
                        ftext = fn_node.getText()
                        fline = getattr(ctx.start, "line", 1) - 1
                        fcol = getattr(ctx.start, "column", 0)
                        self.b.push(fline, fcol, len(ftext), "function")

                    # parámetros
                    for p in ids[1:]:
                        try:
                            ptok = None
                            try:
                                ptok = p.getSymbol()
                            except Exception:
                                ptok = getattr(p, 'symbol', None)
                            if ptok:
                                ptext = getattr(ptok, 'text', None) or p.getText()
                                pline = max(getattr(ptok, 'line', getattr(ctx.start, 'line', 1)) - 1, 0)
                                pcol = getattr(ptok, 'column', getattr(ctx.start, 'column', 0))
                                self.b.push(pline, pcol, len(ptext), "parameter")
                            else:
                                ptext = p.getText()
                                pline = getattr(ctx.start, "line", 1) - 1
                                pcol = getattr(ctx.start, "column", 0)
                                self.b.push(pline, pcol, len(ptext), "parameter")
                        except Exception:
                            pass
        except Exception:
            pass


def build_semantic_tokens(text: str) -> SemanticTokens:
    """
    Parse el código y devuelve SemanticTokens (para 'semanticTokens/full').
    Implementa un builder local para compatibilidad con distintas versiones de pygls.
    """
    try:
        input_stream = InputStream(text or "")
        lexer = CompiscriptLexer(input_stream)
        tokens = CommonTokenStream(lexer)
        parser = CompiscriptParser(tokens)
        tree = parser.program()

        builder = SimpleSemanticTokensBuilder(SEM_LEGEND)
        walker = ParseTreeWalker()
        walker.walk(_SemTokListener(builder), tree)

        return SemanticTokens(data=builder.build())
    except Exception:
        # En caso de error de parse, devuelve lista vacía: el cliente simplemente no colorea.
        return SemanticTokens(data=[])
