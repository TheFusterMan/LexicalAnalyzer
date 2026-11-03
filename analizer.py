import re

class Analizer:
    def __init__(self):
        self.PATTERNS = {
            'MODIFIER': r'\b(public|private|protected|static|final|abstract|volatile|transient|strictfp)\b',

            'TYPE': r'\b(byte|short|int|long|float|double|boolean|char|String|void)\b',

            'KEYWORD': r'\b(continue|for|new|switch|assert|default|goto|package|synchronized|boolean|do'
                       r'|if|this|break|double|implements|throw|byte|else|import|throws'
                       r'|case|enum|instanceof|return|catch|extends|int|short|try|char|interface'
                       r'|void|class|finally|long|const|float|native|super|while)\b',

            'STRING_LITERAL': r'"(?:\\.|[^"\\])*"',
            'CHAR_LITERAL': r"'(?:\\.|[^'\\])'",
            'NUMBER': r'\b\d+(\.\d+)?([eE][+-]?\d+)?\b',
            'BOOLEAN_LITERAL': r'\b(true|false)\b',

            'IDENTIFIER': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',

            'OPERATOR': r'(>>>=|>>=|<<=|>>>|>>|<<|==|!=|<=|>=|&&|\|\||'
                        r'\+=|-=|\*=|/=|%=|&=|\^=|\|=|\+\+|--|[\+\-*/%&|^!~<>?=])',

            'DELIMITER': r'[:;,.(){}\[\]]',
        }

    def tokenize(self, code):
        code = code.lstrip()
        tokens = []

        while code:
            # Комментарии пропускаются между токенами, чтобы // и /* внутри
            # строковых и символьных литералов оставались частью литерала.
            if code.startswith('//'):
                newline = code.find('\n')
                code = code[newline + 1:].lstrip() if newline >= 0 else ''
                continue
            if code.startswith('/*'):
                end = code.find('*/', 2)
                if end < 0:
                    raise SyntaxError("Незакрытый многострочный комментарий")
                code = code[end + 2:].lstrip()
                continue
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
