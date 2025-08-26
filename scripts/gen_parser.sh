#!/usr/bin/env bash
# scripts/gen_parser.sh


java -jar /usr/local/lib/antlr-4.13.1-complete.jar \
       -Dlanguage=Python3 -listener -visitor\
       -o src/parser \
       Compiscript.g4
