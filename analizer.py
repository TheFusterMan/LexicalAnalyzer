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

            'ANNOTATION': r'@[a-zA-Z_][a-zA-Z0-9_]*',
            'STRING_LITERAL': r'"(?:\\.|[^"\\])*"',
            'CHAR_LITERAL': r"'(?:\\.|[^'\\])'",
            'NUMBER': r'\b\d+(\.\d+)?([eE][+-]?\d+)?\b',
            'BOOLEAN_LITERAL': r'\b(true|false)\b',

            'IDENTIFIER': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',

            'OPERATOR': r'(>>>=|>>=|<<=|>>>|>>|<<|==|!=|<=|>=|&&|\|\||'
                        r'\+=|-=|\*=|/=|%=|&=|\^=|\|=|\+\+|--|[\+\-*/%&|^!~<>?=])',

            'DELIMITER': r'[:;,.(){}\[\]]',
        }
        self.token_lines = []

    def tokenize(self, code):
        self.token_lines = []
        line = 1
        tokens = []

        while code:
            ws_match = re.match(r'\s+', code)
            if ws_match:
                line += ws_match.group(0).count('\n')
                code = code[ws_match.end():]
                continue

            if code.startswith('//'):
                newline = code.find('\n')
                if newline >= 0:
                    line += 1
                    code = code[newline + 1:]
                else:
                    code = ''
                continue

            if code.startswith('/*'):
                end = code.find('*/', 2)
                if end < 0:
                    raise SyntaxError(f"Строка {line}: Незакрытый многострочный комментарий")
                line += code[:end + 2].count('\n')
                code = code[end + 2:]
                continue

            match = None
            for token_type, pattern in self.PATTERNS.items():
                match = re.match(pattern, code)
                if match:
                    lexeme = match.group(0)
                    tokens.append((token_type, lexeme))
                    self.token_lines.append(line)
                    line += lexeme.count('\n')
                    code = code[len(lexeme):]
                    break

            if not match:
                raise SyntaxError(f"Строка {line}: Illegal character '{code[0]}'")

        return tokens