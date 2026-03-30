import re

class Analizer:
    def __init__(self):
        self.PATTERNS = {
            'KEYWORD': r'\b(abstract|continue|for|new|switch|assert|default|goto|package|synchronized|boolean|do'
                       r'|if|private|this|break|double|implements|protected|throw|byte|else|import|public|throws'
                       r'|case|enum|instanceof|return|transient|catch|extends|int|short|try|char|final|interface'
                       r'|static|void|class|finally|long|strictfp|volatile|const|float|native|super|while)\b',

            'TYPE': r'\b(byte|short|int|long|float|double|boolean|char|String)\b',

            'STRING_LITERAL': r'"(?:\\.|[^"\\])*"',
            'NUMBER': r'\b\d+(\.\d+)?\b',
            'BOOLEAN_LITERAL': r'\b(true|false)\b',

            'IDENTIFIER': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',

            'OPERATOR': r'(>>>=|>>=|<<=|>>>|>>|<<|==|!=|<=|>=|&&|\|\||'
                        r'\+=|-=|\*=|/=|%=|&=|\^=|\|=|\+\+|--|[\+\-*/%&|^!<>?=])',

            'DELIMITER': r'[;,.(){}\[\]]',
        }

    def tokenize(self, code):
        code = code.lstrip()
        tokens = []

        while code:
            match = None

            for token_type, pattern in self.PATTERNS.items():
                match = re.match(pattern, code)

                if match:
                    tokens.append((token_type, match.group(0)))
                    code = code[len(match.group(0)):].lstrip()
                    break

            if not match:
                raise SyntaxError(f"Illegal character '{code[0]}'")

        return tokens