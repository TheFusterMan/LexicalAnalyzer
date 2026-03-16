import re

class Analizer:
    def __init__(self):
        self.patterns = {
            'KEYWORD': r'\b(public|private|static|void|class|return|if|else|while|import|package)\b',

            'TYPE': r'\b(String|int|float|double|boolean)\b',

            'STRING_LITERAL': r'"(?:\\.|[^"\\])*"',
            'NUMBER': r'\b\d+(\.\d+)?\b',
            'BOOLEAN_LITERAL': r'\b(true|false)\b',

            'IDENTIFIER': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',

            'OPERATOR': r'(==|!=|<=|>=|&&|\|\||[+\-*/=<>])',

            'DELIMITER': r'[;,.(){}\[\]]',
        }

    def tokenize(self, code):
        code = code.lstrip()
        tokens = []

        while code:
            match = None

            for token_type, pattern in self.patterns.items():
                match = re.match(pattern, code)

                if match:
                    tokens.append((token_type, match.group(0)))
                    code = code[len(match.group(0)):].lstrip()
                    break

            if not match:
                raise SyntaxError(f"Illegal character '{code[0]}'")

        return tokens