#!/usr/bin/env bash
# scripts/gen_parser.sh

antlr4 -Dlanguage=Python3 -listener \
       -o src/parser \
       Compiscript.g4
