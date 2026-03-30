from analizer import Analizer

filename = "Code.java"
code_to_tokenize = ""

with open(filename, "r", encoding="utf-8") as f:
    code_to_tokenize = f.read()

analizer = Analizer()

for token in analizer.tokenize(code_to_tokenize):
    print(token)