# src/semantic/flow_validator.py

from parser.CompiscriptParser import CompiscriptParser
from parser.CompiscriptVisitor import CompiscriptVisitor

class FlowValidator(CompiscriptVisitor):
    def __init__(self):
        # stack para saber si estamos dentro de una función
        self._func_stack = []
        self.errors = []

    def visitFunctionDeclaration(self, ctx):
        self._func_stack.append(True)
        self.visitChildren(ctx)
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

    @staticmethod
    def validate(tree):
        v = FlowValidator()
        v.visit(tree)
        return v.errors
