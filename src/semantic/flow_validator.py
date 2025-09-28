# src/semantic/flow_validator.py

from parser.CompiscriptParser import CompiscriptParser
from parser.CompiscriptVisitor import CompiscriptVisitor

class FlowValidator(CompiscriptVisitor):
    def __init__(self):
        # stack para saber si estamos dentro de una función
        self._func_stack = []
        self.errors = []

        # pila de scopes: cada elemento es un set() de nombres declarados en ese scope
        # el scope [0] será el global
        self._scope_stack = [set()]

    def visitFunctionDeclaration(self, ctx):
        # entramos en función: nuevo scope
        self._func_stack.append(True)
        self._scope_stack.append(set())  # nuevo scope para la función
        self.visitChildren(ctx)
        self._scope_stack.pop()
        self._func_stack.pop()
        return None

    def visitReturnStatement(self, ctx):
        # si no hay función en la pila, es error
        if not self._func_stack:
            line = ctx.start.line
            self.errors.append(f"[linea {line}] 'return' fuera de funcion")
        return self.visitChildren(ctx)

    def visitIfStatement(self, ctx):
        # condicion exacta
        cond = ctx.expression()
        text = cond.getText()
        if text not in ("true", "false"):
            line = getattr(cond.start, "line", getattr(ctx.start, "line", 1))
            self.errors.append(f"[linea {line}] condicion de 'if' no es boolean: {text!r}")
        return self.visitChildren(ctx)


    def visitWhileStatement(self, ctx):
        text = ctx.expression().getText()
        if text not in ("true", "false"):
            line = ctx.start.line
            self.errors.append(f"[linea {line}] condicion de 'while' no es boolean: {text!r}")
        return self.visitChildren(ctx)

    def visitForStatement(self, ctx):
        # la condición está en expression(0)
        cond_ctx = ctx.expression(0)
        if cond_ctx:
            text = cond_ctx.getText()
            if text not in ("true", "false"):
                line = cond_ctx.start.line
                self.errors.append(f"[linea {line}] condicion de 'for' no es boolean: {text!r}")
        return self.visitChildren(ctx)

    def visitVariableDeclaration(self, ctx):
        """
        Detecta declaraciones del estilo:
          let a : integer = 5;
        y añade 'a' al scope actual.
        """
        try:
            # Preferimos extraer el identificador vía ctx.Identifier() si está disponible.
            if hasattr(ctx, "Identifier") and ctx.Identifier() is not None:
                ids = ctx.Identifier()
                # puede ser una lista (en ciertos nodos de ANTLR) o un único token
                if isinstance(ids, list):
                    # por convención el primer Identifier suele ser el nombre
                    name = ids[0].getText()
                else:
                    name = ids.getText()
                self._scope_stack[-1].add(name)
            else:
                # fallback simple (muy raro): usa getText y extrae con split
                txt = ctx.getText()
                parts = txt.replace(";", " ").split()
                if len(parts) >= 2 and parts[0].startswith("let"):
                    self._scope_stack[-1].add(parts[1])
        except Exception:
            # no bloquear la validación por un pequeño fallo de parsing/ctx
            pass

        return self.visitChildren(ctx)

    def visitAssignment(self, ctx):
        """
        Detecta asignaciones tipo: b = 10;
        Si la variable a la izquierda no está declarada en ningún scope,
        agrega un error.
        """
        try:
            # Preferimos extraer el identificador directamente desde ctx
            name = None
            if hasattr(ctx, "Identifier") and ctx.Identifier() is not None:
                ids = ctx.Identifier()
                if isinstance(ids, list):
                    # si es lista: en casos complejos (propiedades) cogen el último o el primero
                    name = ids[0].getText()
                else:
                    name = ids.getText()
            else:
                # fallback: intentar obtener de la forma 'X ='
                txt = ctx.getText()
                parts = txt.split("=")
                if parts:
                    left = parts[0].strip()
                    # el primer token es el identificador
                    name = left.split()[0] if left.split() else None

            if name:
                declared = False
                for s in reversed(self._scope_stack):
                    if name in s:
                        declared = True
                        break
                if not declared:
                    line = getattr(ctx.start, "line", 1)
                    self.errors.append(f"[linea {line}] variable '{name}' no declarada")
        except Exception:
            pass

        return self.visitChildren(ctx)

    @staticmethod
    def validate(tree):
        v = FlowValidator()
        v.visit(tree)
        return v.errors
