from ast_structures import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_type=None, expected_value=None):
        token = self.current_token()
        if token is None:
            raise SyntaxError("Неожиданный конец файла (EOF)")

        token_type, token_value = token

        if expected_type and token_type != expected_type:
            raise SyntaxError(f"Ожидался тип токена {expected_type}, получено {token_type} ('{token_value}')")

        if expected_value and token_value != expected_value:
            raise SyntaxError(f"Ожидалось значение '{expected_value}', получено '{token_value}'")

        self.pos += 1
        return token

    def parse_modifiers(self):
        modifiers = []
        while self.current_token() and self.current_token()[0] == 'MODIFIER':
            modifiers.append(self.consume('MODIFIER')[1])
        return modifiers

    def parse(self):
        statements = []
        while self.current_token() is not None:
            statements.append(self.parse_statement())
        return Program(statements)

    def parse_statement(self):
        token = self.current_token()
        if token[0] == 'MODIFIER' or (token[0] == 'KEYWORD' and token[1] == 'class'):
            modifiers = self.parse_modifiers()
            if self.current_token()[1] == 'class':
                return self.parse_class_declaration(modifiers)
            else:
                return self.parse_method_declaration(modifiers)

        if token[0] == 'TYPE':
            if self.pos + 2 < len(self.tokens) and self.tokens[self.pos + 2][1] == '(':
                return self.parse_method_declaration([])
            return self.parse_variable_declaration()

        if token[0] == 'DELIMITER' and token[1] == '{':
            return self.parse_block()

        if token[0] == 'KEYWORD' and token[1] == 'while':
            return self.parse_while()

        if token[0] == 'IDENTIFIER':
            return self.parse_assignment_or_method_call()

        raise SyntaxError(f"Неизвестное начало выражения: {token}")

    def parse_class_declaration(self, modifiers):
        self.consume('KEYWORD', 'class')
        name = self.consume('IDENTIFIER')[1]
        self.consume('DELIMITER', '{')

        body = []
        while self.current_token() and self.current_token()[1] != '}':
            body.append(self.parse_statement())

        self.consume('DELIMITER', '}')
        return ClassDeclaration(modifiers, name, body)

    def parse_method_declaration(self, modifiers):
        return_type = self.consume()[1]
        name = self.consume('IDENTIFIER')[1]

        self.consume('DELIMITER', '(')

        params = []
        while self.current_token() and self.current_token()[1] != ')':
            params.append(self.consume()[1])
        self.consume('DELIMITER', ')')

        body = self.parse_block()
        return MethodDeclaration(modifiers, return_type, name, params, body)

    def parse_block(self):
        self.consume('DELIMITER', '{')
        statements = []
        while self.current_token() and self.current_token()[1] != '}':
            statements.append(self.parse_statement())
        self.consume('DELIMITER', '}')
        return Block(statements)

    def parse_while(self):
        self.consume('KEYWORD', 'while')
        self.consume('DELIMITER', '(')
        condition = self.parse_expression()
        self.consume('DELIMITER', ')')
        body = self.parse_block()
        return WhileStatement(condition, body)

    def parse_variable_declaration(self):
        var_type = self.consume()[1]
        var_name = self.consume('IDENTIFIER')[1]

        value = None
        if self.current_token() and self.current_token()[1] == '=':
            self.consume('OPERATOR', '=')
            value = self.parse_expression()

        self.consume('DELIMITER', ';')
        return VariableDeclaration(var_type, var_name, value)

    def parse_assignment_or_method_call(self):

        target = self.consume('IDENTIFIER')[1]
        while self.current_token() and self.current_token()[1] == '.':
            self.consume('DELIMITER', '.')
            target += "." + self.consume('IDENTIFIER')[1]

        token = self.current_token()


        if token[1] == '=':
            self.consume('OPERATOR', '=')
            value = self.parse_expression()
            self.consume('DELIMITER', ';')
            return Assignment(target, value)


        elif token[1] == '(':
            self.consume('DELIMITER', '(')
            args = []
            if self.current_token()[1] != ')':
                args.append(self.parse_expression())
            self.consume('DELIMITER', ')')
            self.consume('DELIMITER', ';')
            return MethodCall(target, args)

        raise SyntaxError(f"Ожидалось присваивание или вызов метода после {target}")

    def parse_expression(self):
        left = self.parse_primary()

        token = self.current_token()

        while token and token[0] == 'OPERATOR':
            operator = self.consume('OPERATOR')[1]
            right = self.parse_primary()
            left = BinaryOperation(left, operator, right)
            token = self.current_token()

        return left

    def parse_primary(self):
        token = self.consume()

        if token[0] == 'NUMBER':
            return NumberLiteral(token[1])
        elif token[0] == 'IDENTIFIER':
            return Identifier(token[1])
        elif token[0] == 'STRING_LITERAL':
            return StringLiteral(token[1])
        else:
            raise SyntaxError(f"Ожидалось число, строка или идентификатор, получено {token}")

    @staticmethod
    def print_ast(node, indent=""):
        if isinstance(node, Program):
            print(indent + "Program:")
            for stmt in node.statements:
                Parser.print_ast(stmt, indent + "  ")
        elif isinstance(node, ClassDeclaration):
            print(indent + f"Class: {node.name} (Mods: {node.modifiers})")
            for stmt in node.body:
                Parser.print_ast(stmt, indent + "  ")
        elif isinstance(node, MethodDeclaration):
            print(indent + f"Method: {node.name} returns {node.return_type} (Mods: {node.modifiers})")
            Parser.print_ast(node.body, indent + "  ")
        elif isinstance(node, Block):
            print(indent + "Block:")
            for stmt in node.statements:
                Parser.print_ast(stmt, indent + "  ")
        elif isinstance(node, WhileStatement):
            print(indent + "While:")
            Parser.print_ast(node.condition, indent + "  [Cond] ")
            Parser.print_ast(node.body, indent + "  ")
        elif isinstance(node, VariableDeclaration):
            print(indent + f"VariableDecl (Type: {node.var_type}, Name: {node.name})")
            if node.value:
                Parser.print_ast(node.value, indent + "  |= ")
        elif isinstance(node, Assignment):
            print(indent + f"Assignment (Target: {node.target})")
            Parser.print_ast(node.value, indent + "  |= ")
        elif isinstance(node, MethodCall):
            print(indent + f"MethodCall (Target: {node.target})")
            for arg in node.args:
                Parser.print_ast(arg, indent + "  [Arg] ")
        elif isinstance(node, BinaryOperation):
            print(indent + f"BinOp ({node.operator})")
            Parser.print_ast(node.left, indent + "  L: ")
            Parser.print_ast(node.right, indent + "  R: ")
        elif isinstance(node, NumberLiteral):
            print(indent + f"Number({node.value})")
        elif isinstance(node, StringLiteral):
            print(indent + f"String({node.value})")
        elif isinstance(node, Identifier):
            print(indent + f"Identifier({node.name})")