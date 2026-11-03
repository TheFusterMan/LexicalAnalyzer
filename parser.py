from dataclasses import fields

from ast_structures import *


class Parser:
    # Приоритеты бинарных операций Java (от низкого к высокому).
    PRECEDENCE = {
        '||': 1, '&&': 2, '|': 3, '^': 4, '&': 5,
        '==': 6, '!=': 6,
        '<': 7, '<=': 7, '>': 7, '>=': 7,
        '<<': 8, '>>': 8, '>>>': 8,
        '+': 9, '-': 9,
        '*': 10, '/': 10, '%': 10,
    }
    ASSIGNMENT_OPERATORS = {
        '=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=',
        '<<=', '>>=', '>>>=',
    }

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.loop_depth = 0
        self.switch_depth = 0

    def at(self, value):
        token = self.current_token()
        return token is not None and token[1] == value

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

        if expected_value is not None and token_value != expected_value:
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
            if self.at('class'):
                return self.parse_class_declaration(modifiers)
            if self.is_method_declaration():
                return self.parse_method_declaration(modifiers)
            declaration = self.parse_variable_declaration()
            if 'final' in modifiers:
                if declaration.value is None:
                    raise SyntaxError("Для final требуется инициализатор")
                return ConstantDeclaration(declaration.var_type, declaration.name, declaration.value)
            return declaration

        if token[0] == 'TYPE':
            if self.is_method_declaration():
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

        if token[0] == 'KEYWORD' and token[1] == 'switch':
            return self.parse_switch()

        if token[0] == 'KEYWORD' and token[1] in ('break', 'continue'):
            keyword = self.consume('KEYWORD')[1]
            if keyword == 'break' and not (self.loop_depth or self.switch_depth):
                raise SyntaxError("break допустим только внутри цикла или switch")
            if keyword == 'continue' and not self.loop_depth:
                raise SyntaxError("continue допустим только внутри цикла")
            self.consume('DELIMITER', ';')
            return BreakStatement() if keyword == 'break' else ContinueStatement()

        if token[0] == 'KEYWORD' and token[1] == 'return':
            return self.parse_return()

        if token[0] == 'KEYWORD' and token[1] == 'const':
            return self.parse_constant_declaration()

        if token[0] == 'IDENTIFIER' or token[1] in ('++', '--', '('):
            return self.parse_assignment_or_method_call()

        raise SyntaxError(f"Неизвестное начало выражения: {token}")

    def is_method_declaration(self):
        position = self.pos
        if position >= len(self.tokens) or self.tokens[position][0] != 'TYPE':
            return False
        position += 1
        while position + 1 < len(self.tokens) and self.tokens[position][1] == '[' and self.tokens[position + 1][1] == ']':
            position += 2
        return (position + 1 < len(self.tokens)
                and self.tokens[position][0] == 'IDENTIFIER'
                and self.tokens[position + 1][1] == '(')

    def parse_array_suffix(self):
        suffix = ''
        while self.at('['):
            self.consume('DELIMITER', '[')
            self.consume('DELIMITER', ']')
            suffix += '[]'
        return suffix

    def parse_type(self, allow_void=False):
        var_type = self.consume('TYPE')[1]
        suffix = self.parse_array_suffix()
        if var_type == 'void' and (not allow_void or suffix):
            raise SyntaxError("void допустим только как тип возврата метода")
        return var_type + suffix

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
        return_type = self.parse_type(allow_void=True)
        name = self.consume('IDENTIFIER')[1]

        self.consume('DELIMITER', '(')

        params = []
        if not self.at(')'):
            while True:
                if self.at('final'):
                    self.consume('MODIFIER', 'final')
                param_type = self.parse_type()
                param_name = self.consume('IDENTIFIER')[1]
                param_type += self.parse_array_suffix()
                params.append(Parameter(param_type, param_name))
                if not self.at(','):
                    break
                self.consume('DELIMITER', ',')
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
        body = self.parse_loop_body()
        return WhileStatement(condition, body)

    def parse_do_while(self):
        self.consume('KEYWORD', 'do')
        body = self.parse_loop_body()
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

        body = self.parse_loop_body()
        return ForStatement(init, condition, update, body)

    def parse_loop_body(self):
        self.loop_depth += 1
        try:
            return self.parse_statement()
        finally:
            self.loop_depth -= 1

    def parse_variable_declaration_no_semi(self):
        var_type = self.parse_type()
        var_name = self.consume('IDENTIFIER')[1]
        var_type += self.parse_array_suffix()
        value = None
        if self.current_token() and self.current_token()[1] == '=':
            self.consume('OPERATOR', '=')
            value = self.parse_initializer(var_type)
        return VariableDeclaration(var_type, var_name, value)

    def parse_assignment_or_expression_no_semi(self):
        expression = self.parse_expression()
        token = self.current_token()
        if token and token[1] in self.ASSIGNMENT_OPERATORS:
            self.require_assignable(expression)
            operator = self.consume('OPERATOR')[1]
            value = self.parse_expression()
            target = expression.name if isinstance(expression, Identifier) else expression
            return Assignment(target, value, operator)
        if isinstance(expression, MethodCall):
            return expression
        if isinstance(expression, UnaryOperation) and expression.operator in ('++', '--'):
            return ExpressionStatement(expression)
        raise SyntaxError("Ожидалось присваивание, вызов метода или инкремент/декремент")

    @staticmethod
    def require_assignable(expression):
        if isinstance(expression, (Identifier, ArrayAccess)):
            return
        if isinstance(expression, MemberAccess) and expression.member != 'length':
            return
        raise SyntaxError("Левая часть должна быть переменной или элементом массива")

    def parse_constant_declaration(self):
        self.consume('KEYWORD', 'const')
        var_type = self.parse_type()
        var_name = self.consume('IDENTIFIER')[1]
        var_type += self.parse_array_suffix()
        self.consume('OPERATOR', '=')
        value = self.parse_initializer(var_type)
        self.consume('DELIMITER', ';')
        return ConstantDeclaration(var_type, var_name, value)

    def parse_switch(self):
        self.consume('KEYWORD', 'switch')
        self.consume('DELIMITER', '(')
        expression = self.parse_expression()
        self.consume('DELIMITER', ')')
        self.consume('DELIMITER', '{')
        cases = []
        has_default = False
        self.switch_depth += 1
        try:
            while self.current_token() and not self.at('}'):
                if self.at('case'):
                    self.consume('KEYWORD', 'case')
                    value = self.parse_expression()
                    if any(case.value == value for case in cases):
                        raise SyntaxError("Повторная метка case в switch")
                    self.consume('DELIMITER', ':')
                    cases.append(SwitchCase(value, []))
                elif self.at('default'):
                    if has_default:
                        raise SyntaxError("Повторный default в switch")
                    self.consume('KEYWORD', 'default')
                    self.consume('DELIMITER', ':')
                    has_default = True
                    cases.append(SwitchCase(None, []))
                else:
                    if not cases:
                        raise SyntaxError("В switch ожидалось case или default")
                    cases[-1].statements.append(self.parse_statement())
            self.consume('DELIMITER', '}')
        finally:
            self.switch_depth -= 1
        return SwitchStatement(expression, cases)

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
        declaration = self.parse_variable_declaration_no_semi()
        self.consume('DELIMITER', ';')
        return declaration

    def parse_assignment_or_method_call(self):
        statement = self.parse_assignment_or_expression_no_semi()
        self.consume('DELIMITER', ';')
        return statement

    def parse_initializer(self, var_type):
        if self.at('{'):
            if not var_type.endswith('[]'):
                raise SyntaxError("Инициализатор {...} допустим только для массива")
            return self.parse_array_initializer()
        return self.parse_expression()

    def parse_array_initializer(self):
        self.consume('DELIMITER', '{')
        elements = []
        while not self.at('}'):
            element = self.parse_array_initializer() if self.at('{') else self.parse_expression()
            elements.append(element)
            if not self.at(','):
                break
            self.consume('DELIMITER', ',')
        self.consume('DELIMITER', '}')
        return ArrayInitializer(elements)

    def parse_array_creation(self):
        self.consume('KEYWORD', 'new')
        element_type = self.consume('TYPE')[1]
        if element_type == 'void':
            raise SyntaxError("Массив не может иметь тип void")
        dimensions = []
        empty_dimension = False
        while self.at('['):
            self.consume('DELIMITER', '[')
            if self.at(']'):
                empty_dimension = True
                dimensions.append(None)
            else:
                if empty_dimension:
                    raise SyntaxError("Размер после пустого измерения массива недопустим")
                dimensions.append(self.parse_expression())
            self.consume('DELIMITER', ']')
        if not dimensions:
            raise SyntaxError("После new ожидались измерения массива")
        initializer = self.parse_array_initializer() if self.at('{') else None
        if initializer is not None and any(size is not None for size in dimensions):
            raise SyntaxError("Нельзя одновременно указать размер массива и инициализатор")
        if initializer is None and all(size is None for size in dimensions):
            raise SyntaxError("Для массива требуется размер или инициализатор")
        return ArrayCreation(element_type, dimensions, initializer)

    def parse_expression(self, min_precedence=1):
        left = self.parse_unary()
        while self.current_token():
            precedence = self.PRECEDENCE.get(self.current_token()[1], 0)
            if precedence < min_precedence:
                break
            operator = self.consume('OPERATOR')[1]
            right = self.parse_expression(precedence + 1)
            left = BinaryOperation(left, operator, right)
        return left

    def parse_unary(self):
        if self.current_token() and self.current_token()[1] in ('+', '-', '!', '~', '++', '--'):
            operator = self.consume('OPERATOR')[1]
            operand = self.parse_unary()
            if operator in ('++', '--'):
                self.require_assignable(operand)
            return UnaryOperation(operator, operand)
        return self.parse_postfix()

    @staticmethod
    def qualified_name(expression):
        if isinstance(expression, Identifier):
            return expression.name
        if isinstance(expression, MemberAccess):
            target = Parser.qualified_name(expression.target)
            if target is not None:
                return target + '.' + expression.member
        return None

    def parse_postfix(self):
        expression = self.parse_primary()
        while self.current_token():
            if self.at('['):
                self.consume('DELIMITER', '[')
                index = self.parse_expression()
                self.consume('DELIMITER', ']')
                expression = ArrayAccess(expression, index)
            elif self.at('.'):
                self.consume('DELIMITER', '.')
                expression = MemberAccess(expression, self.consume('IDENTIFIER')[1])
            elif self.at('('):
                self.consume('DELIMITER', '(')
                args = []
                if not self.at(')'):
                    while True:
                        args.append(self.parse_expression())
                        if not self.at(','):
                            break
                        self.consume('DELIMITER', ',')
                self.consume('DELIMITER', ')')
                target = self.qualified_name(expression)
                expression = MethodCall(target if target is not None else expression, args)
            elif self.current_token()[1] in ('++', '--'):
                self.require_assignable(expression)
                expression = UnaryOperation(self.consume('OPERATOR')[1], expression, postfix=True)
                break
            else:
                break
        return expression

    def parse_primary(self):
        if self.at('('):
            self.consume('DELIMITER', '(')
            expression = self.parse_expression()
            self.consume('DELIMITER', ')')
            return expression
        if self.at('new'):
            return self.parse_array_creation()
        token = self.consume()

        if token[0] == 'NUMBER':
            return NumberLiteral(token[1])
        elif token[0] == 'IDENTIFIER':
            return Identifier(token[1])
        elif token[0] == 'STRING_LITERAL':
            return StringLiteral(token[1])
        elif token[0] == 'CHAR_LITERAL':
            return CharLiteral(token[1])
        elif token[0] == 'BOOLEAN_LITERAL':
            return BooleanLiteral(token[1])
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
            for param in node.params:
                Parser.print_ast(param, indent + "  [Param] ")
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
            print(indent + f"Assignment ({node.operator})")
            if isinstance(node.target, str):
                print(indent + f"  Target: {node.target}")
            else:
                Parser.print_ast(node.target, indent + "  [Target] ")
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
        elif isinstance(node, ASTNode):
            print(indent + node.__class__.__name__ + ':')
            for field in fields(node):
                value = getattr(node, field.name)
                if isinstance(value, ASTNode):
                    Parser.print_ast(value, indent + f"  [{field.name}] ")
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, ASTNode):
                            Parser.print_ast(item, indent + f"  [{field.name}] ")
                elif value is not None:
                    print(indent + f"  {field.name}: {value}")
