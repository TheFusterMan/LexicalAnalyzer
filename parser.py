from dataclasses import fields

from ast_structures import *


class Parser:
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

    def __init__(self, tokens, token_lines=None):
        self.tokens = tokens
        self.token_lines = token_lines
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

    def current_line(self):
        if not self.token_lines:
            return None
        if self.pos < len(self.token_lines):
            return self.token_lines[self.pos]
        return self.token_lines[-1]

    def syntax_error(self, message, line=None):
        err_line = line if line is not None else self.current_line()
        if err_line is not None:
            return SyntaxError(f"Строка {err_line}: {message}")
        return SyntaxError(message)

    def consume(self, expected_type=None, expected_value=None):
        line = self.current_line()
        token = self.current_token()
        if token is None:
            raise self.syntax_error("Неожиданный конец файла (EOF)", line)

        token_type, token_value = token

        if expected_type and token_type != expected_type:
            raise self.syntax_error(
                f"Ожидался тип токена {expected_type}, получено {token_type} ('{token_value}')", line
            )

        if expected_value is not None and token_value != expected_value:
            raise self.syntax_error(
                f"Ожидалось значение '{expected_value}', получено '{token_value}'", line
            )

        self.pos += 1
        return token

    def parse_modifiers(self):
        modifiers = []
        while self.current_token() and self.current_token()[0] == 'MODIFIER':
            modifiers.append(self.consume('MODIFIER')[1])
        return modifiers

    def parse(self):
        statements = []
        try:
            if self.current_token() and self.current_token()[1] == 'package':
                statements.append(self.parse_package())

            while self.current_token() and self.current_token()[1] == 'import':
                statements.append(self.parse_import())

            while self.current_token() is not None:
                statements.append(self.parse_statement())
        except SyntaxError as e:
            msg = str(e)
            if not msg.startswith("Строка "):
                line = self.current_line()
                if line is not None:
                    raise SyntaxError(f"Строка {line}: {msg}") from None
            raise
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

    def skip_type(self, pos):
        if pos >= len(self.tokens) or self.tokens[pos][0] not in ('TYPE', 'IDENTIFIER'):
            return None
        p = pos + 1
        if p < len(self.tokens) and self.tokens[p][1] == '<':
            depth = 1
            p += 1
            while p < len(self.tokens) and depth > 0:
                t_type, t_val = self.tokens[p]
                if t_val == '<':
                    depth += 1
                elif t_val == '>':
                    depth -= 1
                elif t_val not in (',', '[', ']') and t_type not in ('TYPE', 'IDENTIFIER'):
                    return None
                p += 1
            if depth != 0:
                return None
        while p + 1 < len(self.tokens) and self.tokens[p][1] == '[' and self.tokens[p + 1][1] == ']':
            p += 2
        return p

    def is_method_declaration(self):
        end = self.skip_type(self.pos)
        if end is None or end + 1 >= len(self.tokens):
            return False
        return self.tokens[end][0] == 'IDENTIFIER' and self.tokens[end + 1][1] == '('

    def is_constructor_declaration(self):
        return (
            self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos][0] == 'IDENTIFIER'
            and self.tokens[self.pos + 1][1] == '('
        )

    def is_variable_declaration(self):
        end = self.skip_type(self.pos)
        if end is None or end >= len(self.tokens):
            return False
        if self.tokens[end][0] != 'IDENTIFIER':
            return False
        return end + 1 >= len(self.tokens) or self.tokens[end + 1][1] != '('

    def parse_statement(self, in_class=False):
        line = self.current_line()
        node = self._parse_statement_inner(in_class=in_class)
        if node is not None and not hasattr(node, '_line'):
            node._line = line
        return node

    def _parse_statement_inner(self, in_class=False):
        while self.current_token() and self.current_token()[0] == 'ANNOTATION':
            self.consume('ANNOTATION')

        token = self.current_token()
        if token is None:
            raise self.syntax_error("EOF")

        if token[0] == 'MODIFIER' or (token[0] == 'KEYWORD' and token[1] == 'class'):
            modifiers = self.parse_modifiers()
            if self.at('class'):
                return self.parse_class_declaration(modifiers)
            if in_class and self.is_constructor_declaration():
                return self.parse_constructor_declaration(modifiers)
            if self.is_method_declaration():
                return self.parse_method_declaration(modifiers)
            declaration = self.parse_variable_declaration(modifiers)
            if 'final' in modifiers:
                if declaration.value is None:
                    raise self.syntax_error("Для final требуется инициализатор")
                return ConstantDeclaration(declaration.var_type, declaration.name, declaration.value, modifiers)
            return declaration

        if token[0] == 'TYPE' or self.is_method_declaration() or self.is_variable_declaration():
            if self.is_method_declaration():
                return self.parse_method_declaration([])
            return self.parse_variable_declaration()

        if in_class and self.is_constructor_declaration():
            return self.parse_constructor_declaration([])

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
                raise self.syntax_error("break допустим только внутри цикла или switch")
            if keyword == 'continue' and not self.loop_depth:
                raise self.syntax_error("continue допустим только внутри цикла")
            self.consume('DELIMITER', ';')
            return BreakStatement() if keyword == 'break' else ContinueStatement()

        if token[0] == 'KEYWORD' and token[1] == 'return':
            return self.parse_return()

        if token[0] == 'KEYWORD' and token[1] == 'const':
            return self.parse_constant_declaration()

        if token[0] == 'IDENTIFIER' or token[1] in ('++', '--', '(', 'this'):
            return self.parse_assignment_or_method_call()

        raise self.syntax_error(f"Неизвестное начало выражения: {token}")

    def parse_array_suffix(self):
        suffix = ''
        while self.at('['):
            self.consume('DELIMITER', '[')
            self.consume('DELIMITER', ']')
            suffix += '[]'
        return suffix

    def parse_type(self, allow_void=False):
        token = self.current_token()
        if token and token[0] in ('TYPE', 'IDENTIFIER'):
            var_type = self.consume()[1]
        else:
            raise self.syntax_error(f"Ожидался тип данных, получено {token}")

        if self.at('<'):
            self.consume('OPERATOR', '<')
            inner_parts = []
            while not self.at('>'):
                inner_parts.append(self.parse_type())
                if self.at(','):
                    self.consume('DELIMITER', ',')
                else:
                    break
            self.consume('OPERATOR', '>')
            var_type += '<' + ', '.join(inner_parts) + '>'

        suffix = self.parse_array_suffix()
        if var_type == 'void' and (not allow_void or suffix):
            raise self.syntax_error("void допустим только как тип возврата метода")
        return var_type + suffix

    def parse_class_declaration(self, modifiers):
        self.consume('KEYWORD', 'class')
        name = self.consume('IDENTIFIER')[1]
        self.consume('DELIMITER', '{')

        body = []
        while self.current_token() and self.current_token()[1] != '}':
            body.append(self.parse_statement(in_class=True))

        self.consume('DELIMITER', '}')
        return ClassDeclaration(modifiers, name, body)

    def parse_parameters(self):
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
        return params

    def parse_constructor_declaration(self, modifiers):
        line = self.current_line()
        name = self.consume('IDENTIFIER')[1]
        params = self.parse_parameters()
        body = self.parse_block()
        node = ConstructorDeclaration(modifiers, name, params, body)
        node._line = line
        return node

    def parse_method_declaration(self, modifiers):
        line = self.current_line()
        return_type = self.parse_type(allow_void=True)
        name = self.consume('IDENTIFIER')[1]
        params = self.parse_parameters()
        body = self.parse_block()
        node = MethodDeclaration(modifiers, return_type, name, params, body)
        node._line = line
        return node

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

    def is_foreach_header(self):
        end = self.skip_type(self.pos)
        if end is None or end + 1 >= len(self.tokens):
            return False
        return self.tokens[end][0] == 'IDENTIFIER' and self.tokens[end + 1][1] == ':'

    def parse_for(self):
        self.consume('KEYWORD', 'for')
        self.consume('DELIMITER', '(')

        if self.is_foreach_header():
            var_type = self.parse_type()
            var_name = self.consume('IDENTIFIER')[1]
            self.consume('DELIMITER', ':')
            iterable = self.parse_expression()
            self.consume('DELIMITER', ')')
            body = self.parse_loop_body()
            return ForEachStatement(var_type, var_name, iterable, body)

        init = None
        if self.current_token() and self.current_token()[1] != ';':
            if self.current_token()[0] == 'TYPE' or self.is_variable_declaration():
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

    def parse_variable_declaration_no_semi(self, modifiers=None):
        line = self.current_line()
        var_type = self.parse_type()
        var_name = self.consume('IDENTIFIER')[1]
        var_type += self.parse_array_suffix()
        value = None
        if self.current_token() and self.current_token()[1] == '=':
            self.consume('OPERATOR', '=')
            value = self.parse_initializer(var_type)
        node = VariableDeclaration(var_type, var_name, value, modifiers or [])
        node._line = line
        return node

    def parse_assignment_or_expression_no_semi(self):
        line = self.current_line()
        expression = self.parse_expression()
        token = self.current_token()
        if token and token[1] in self.ASSIGNMENT_OPERATORS:
            self.require_assignable(expression)
            operator = self.consume('OPERATOR')[1]
            value = self.parse_expression()
            target = expression.name if isinstance(expression, Identifier) else expression
            node = Assignment(target, value, operator)
            node._line = line
            return node
        if isinstance(expression, MethodCall):
            expression._line = line
            return expression
        if isinstance(expression, UnaryOperation) and expression.operator in ('++', '--'):
            node = ExpressionStatement(expression)
            node._line = line
            return node
        raise self.syntax_error("Ожидалось присваивание, вызов метода или инкремент/декремент", line)

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
                        raise self.syntax_error("Повторная метка case в switch")
                    self.consume('DELIMITER', ':')
                    cases.append(SwitchCase(value, []))
                elif self.at('default'):
                    if has_default:
                        raise self.syntax_error("Повторный default в switch")
                    self.consume('KEYWORD', 'default')
                    self.consume('DELIMITER', ':')
                    has_default = True
                    cases.append(SwitchCase(None, []))
                else:
                    if not cases:
                        raise self.syntax_error("В switch ожидалось case или default")
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

    def parse_variable_declaration(self, modifiers=None):
        declaration = self.parse_variable_declaration_no_semi(modifiers)
        self.consume('DELIMITER', ';')
        return declaration

    def parse_assignment_or_method_call(self):
        statement = self.parse_assignment_or_expression_no_semi()
        self.consume('DELIMITER', ';')
        return statement

    def parse_initializer(self, var_type):
        if self.at('{'):
            if not var_type.endswith('[]'):
                raise self.syntax_error("Инициализатор {...} допустим только для массива")
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

    def parse_new_expression(self):
        self.consume('KEYWORD', 'new')
        token = self.current_token()
        if not token or token[0] not in ('TYPE', 'IDENTIFIER'):
            raise self.syntax_error(f"Ожидался тип после new, получено {token}")

        is_primitive = token[0] == 'TYPE'
        element_type = self.consume()[1]

        type_args = []
        if not is_primitive and self.at('<'):
            self.consume('OPERATOR', '<')
            if not self.at('>'):
                while True:
                    type_args.append(self.parse_type())
                    if not self.at(','):
                        break
                    self.consume('DELIMITER', ',')
            self.consume('OPERATOR', '>')
            if self.at('('):
                return self._parse_object_creation_args(element_type, type_args)
            raise self.syntax_error("Ожидалось '(' после дженерика")

        if not is_primitive and self.at('('):
            return self._parse_object_creation_args(element_type, type_args)

        if element_type == 'void':
            raise self.syntax_error("Массив не может иметь тип void")

        dimensions = []
        empty_dimension = False
        while self.at('['):
            self.consume('DELIMITER', '[')
            if self.at(']'):
                empty_dimension = True
                dimensions.append(None)
            else:
                if empty_dimension:
                    raise self.syntax_error("Размер после пустого измерения массива недопустим")
                dimensions.append(self.parse_expression())
            self.consume('DELIMITER', ']')
        if not dimensions:
            raise self.syntax_error("После new ожидались измерения массива")
        initializer = self.parse_array_initializer() if self.at('{') else None
        if initializer is not None and any(size is not None for size in dimensions):
            raise self.syntax_error("Нельзя одновременно указать размер массива и инициализатор")
        if initializer is None and all(size is None for size in dimensions):
            raise self.syntax_error("Для массива требуется размер или инициализатор")
        return ArrayCreation(element_type, dimensions, initializer)

    def _parse_object_creation_args(self, class_name, type_args):
        self.consume('DELIMITER', '(')
        args = []
        if not self.at(')'):
            while True:
                args.append(self.parse_expression())
                if not self.at(','):
                    break
                self.consume('DELIMITER', ',')
        self.consume('DELIMITER', ')')
        return ObjectCreation(class_name, type_args, args)

    def parse_expression(self, min_precedence=1):
        left = self.parse_unary()
        while self.current_token():
            precedence = self.PRECEDENCE.get(self.current_token()[1], 0)
            if precedence < min_precedence:
                break
            operator = self.consume('OPERATOR')[1]
            right = self.parse_expression(precedence + 1)
            left = BinaryOperation(left, operator, right)
        if min_precedence == 1 and self.at('?'):
            self.consume('OPERATOR', '?')
            true_expr = self.parse_expression(1)
            self.consume('DELIMITER', ':')
            false_expr = self.parse_expression(1)
            left = TernaryOperation(left, true_expr, false_expr)
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
        line = self.current_line()
        if self.at('('):
            self.consume('DELIMITER', '(')
            expression = self.parse_expression()
            self.consume('DELIMITER', ')')
            return expression
        if self.at('new'):
            node = self.parse_new_expression()
            node._line = line
            return node
        if self.at('this'):
            self.consume('KEYWORD', 'this')
            node = ThisExpression()
            node._line = line
            return node

        token = self.consume()
        if token[0] == 'NUMBER':
            node = NumberLiteral(token[1])
        elif token[0] == 'IDENTIFIER':
            node = Identifier(token[1])
        elif token[0] == 'STRING_LITERAL':
            node = StringLiteral(token[1])
        elif token[0] == 'CHAR_LITERAL':
            node = CharLiteral(token[1])
        elif token[0] == 'BOOLEAN_LITERAL':
            node = BooleanLiteral(token[1])
        else:
            raise self.syntax_error(f"Ожидалось число, строка или идентификатор, получено {token}", line)
        node._line = line
        return node

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