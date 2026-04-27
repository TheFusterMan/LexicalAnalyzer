from analizer import Analizer
from ast_structures import *
from parser import Parser

filename = "Code.java"
code_to_tokenize = ""

with open(filename, "r", encoding="utf-8") as f:
    code_to_tokenize = f.read()

print("--- 1. Лексический анализ (Токены) ---")
analizer = Analizer()
tokens = analizer.tokenize(code_to_tokenize)
for token in tokens:
    print(token)

print("\n--- 2. Синтаксический анализ (AST) ---")
parser = Parser(tokens)
ast = parser.parse()

Parser.print_ast(ast)