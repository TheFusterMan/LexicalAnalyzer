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
        if self.current_token() and self.current_token()[1] == 'package':
            statements.append(self.parse_package())

        while self.current_token() and self.current_token()[1] == 'import':
            statements.append(self.parse_import())

        while self.current_token() is not None:
            statements.append(self.parse_statement())
        return Program(statements)

    def parse_package(self):
        self.consume('KEYWORD', 'package')
        name = self.consume('IDENTIFIER')[1]
        while self.current_token() and self.current_token()[1] == '.':
            self.consume('DELIMITER', '.')
            name += "." + self.consume('IDENTIFIER')[1]
        self.consume('DELIMITER', ';')
        return PackageDeclaration(name)

    def parse_import(self):
        self.consume('KEYWORD', 'import')
        path = self.consume('IDENTIFIER')[1]
        while self.current_token() and self.current_token()[1] == '.':
            self.consume('DELIMITER', '.')
            path += "." + self.consume('IDENTIFIER')[1]
        self.consume('DELIMITER', ';')
        return ImportDeclaration(path)

    def parse_statement(self):
        token = self.current_token()
        if token is None:
            raise SyntaxError("EOF")

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

        if token[0] == 'KEYWORD' and token[1] == 'do':
            return self.parse_do_while()

        if token[0] == 'KEYWORD' and token[1] == 'for':
            return self.parse_for()

        if token[0] == 'KEYWORD' and token[1] == 'if':
            return self.parse_if()

        if token[0] == 'KEYWORD' and token[1] == 'return':
            return self.parse_return()

        if token[0] == 'KEYWORD' and token[1] == 'const':
            return self.parse_constant_declaration()

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

    def parse_do_while(self):
        self.consume('KEYWORD', 'do')
        body = self.parse_block()
        self.consume('KEYWORD', 'while')
        self.consume('DELIMITER', '(')
        condition = self.parse_expression()
        self.consume('DELIMITER', ')')
        self.consume('DELIMITER', ';')
        return DoWhileStatement(body, condition)

    def parse_for(self):
        self.consume('KEYWORD', 'for')
        self.consume('DELIMITER', '(')

        init = None
        if self.current_token() and self.current_token()[1] != ';':
            if self.current_token()[0] == 'TYPE':
                init = self.parse_variable_declaration_no_semi()
            else:
                init = self.parse_assignment_or_expression_no_semi()
        self.consume('DELIMITER', ';')

        condition = None
        if self.current_token() and self.current_token()[1] != ';':
            condition = self.parse_expression()
        self.consume('DELIMITER', ';')

        update = None
        if self.current_token() and self.current_token()[1] != ')':
            update = self.parse_assignment_or_expression_no_semi()
        self.consume('DELIMITER', ')')

        body = self.parse_block()
        return ForStatement(init, condition, update, body)

    def parse_variable_declaration_no_semi(self):
        var_type = self.consume('TYPE')[1]
        var_name = self.consume('IDENTIFIER')[1]
        value = None
        if self.current_token() and self.current_token()[1] == '=':
            self.consume('OPERATOR', '=')
            value = self.parse_expression()
        return VariableDeclaration(var_type, var_name, value)

    def parse_assignment_or_expression_no_semi(self):
        if self.current_token() and self.current_token()[0] == 'IDENTIFIER' and self.pos + 1 < len(self.tokens) and \
                self.tokens[self.pos + 1][1] == '=':
            target = self.consume('IDENTIFIER')[1]
            self.consume('OPERATOR', '=')
            value = self.parse_expression()
            return Assignment(target, value)
        else:
            return self.parse_expression()

    def parse_constant_declaration(self):
        self.consume('KEYWORD', 'const')
        var_type = self.consume('TYPE')[1]
        var_name = self.consume('IDENTIFIER')[1]
        self.consume('OPERATOR', '=')
        value = self.parse_expression()
        self.consume('DELIMITER', ';')
        return ConstantDeclaration(var_type, var_name, value)

    def parse_if(self):
        self.consume('KEYWORD', 'if')
        self.consume('DELIMITER', '(')
        condition = self.parse_expression()
        self.consume('DELIMITER', ')')
        then_branch = self.parse_statement()
        else_branch = None

        if self.current_token() and self.current_token()[0] == 'KEYWORD' and self.current_token()[1] == 'else':
            self.consume('KEYWORD', 'else')
            else_branch = self.parse_statement()

        return IfStatement(condition, then_branch, else_branch)

    def parse_return(self):
        self.consume('KEYWORD', 'return')
        value = None
        if self.current_token() and self.current_token()[1] != ';':
            value = self.parse_expression()
        self.consume('DELIMITER', ';')
        return ReturnStatement(value)

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
        elif token[0] == 'CHAR_LITERAL':
            return CharLiteral(token[1])
        else:
            raise SyntaxError(f"Ожидалось число, строка или идентификатор, получено {token}")

    @staticmethod
    def print_ast(node, indent=""):
        if isinstance(node, Program):
            print(indent + "Program:")
            for stmt in node.statements:
                Parser.print_ast(stmt, indent + "  ")
        elif isinstance(node, PackageDeclaration):
            print(indent + f"Package: {node.name}")
        elif isinstance(node, ImportDeclaration):
            print(indent + f"Import: {node.path}")
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
        elif isinstance(node, DoWhileStatement):
            print(indent + "DoWhile:")
            Parser.print_ast(node.body, indent + "  ")
            Parser.print_ast(node.condition, indent + "  [Cond] ")
        elif isinstance(node, ForStatement):
            print(indent + "For:")
            if node.init:
                Parser.print_ast(node.init, indent + "  [Init] ")
            if node.condition:
                Parser.print_ast(node.condition, indent + "  [Cond] ")
            if node.update:
                Parser.print_ast(node.update, indent + "  [Update] ")
            Parser.print_ast(node.body, indent + "  ")
        elif isinstance(node, ConstantDeclaration):
            print(indent + f"ConstantDecl (Type: {node.var_type}, Name: {node.name})")
            Parser.print_ast(node.value, indent + "  |= ")
        elif isinstance(node, IfStatement):
            print(indent + "If:")
            Parser.print_ast(node.condition, indent + "  [Cond] ")
            Parser.print_ast(node.then_branch, indent + "  [Then] ")
            if node.else_branch:
                Parser.print_ast(node.else_branch, indent + "  [Else] ")
        elif isinstance(node, ReturnStatement):
            print(indent + "Return:")
            if node.value:
                Parser.print_ast(node.value, indent + "  ")
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
        elif isinstance(node, CharLiteral):
            print(indent + f"Char({node.value})")
        elif isinstance(node, Identifier):
            print(indent + f"Identifier({node.name})")