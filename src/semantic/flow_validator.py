# src/semantic/flow_validator.py

from parser.CompiscriptParser import CompiscriptParser
from parser.CompiscriptVisitor import CompiscriptVisitor
import re


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
        # ctx.expression() es la condición
        cond = ctx.expression()
        text = cond.getText()
        if text not in ("true", "false"):
            line = ctx.start.line
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
        # intentamos extraer el nombre con getText() y regex para ser robustos
        try:
            txt = ctx.getText()  # ejemplo: "leta:integer=5;" o "let a : integer = 5;"
            # buscamos 'let' seguido de identificador
            m = re.search(r'\blet\s+([A-Za-z_]\w*)', txt)
            if m:
                name = m.group(1)
                # añade al scope actual (tope de la pila)
                self._scope_stack[-1].add(name)
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
            txt = ctx.getText()  # ejemplo: "b=10;"
            # capturamos el nombre a la izquierda del '='
            m = re.match(r'\s*([A-Za-z_]\w*)\s*=', txt)
            if m:
                name = m.group(1)
                # buscar en la pila de scopes (desde tope hacia global)
                declared = False
                for s in reversed(self._scope_stack):
                    if name in s:
                        declared = True
                        break
                if not declared:
                    # línea aproximada: usamos ctx.start.line si está disponible
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
