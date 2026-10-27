from ast_structures import *

class Generator:
    TYPE_MAP = {
        'int': 'int',
        'boolean': 'bool',
        'byte': 'signed char',
        'short': 'short',
        'long': 'long',
        'float': 'float',
        'double': 'double',
        'char': 'char',
        'String': 'string',
        'void': 'void'
    }

    def __init__(self):
        self.indent_level = 0
        self.includes = set()
        self.needs_iostream = False
        self.needs_string = False
        self.needs_cmath = False

    def indent(self) -> str:
        return "    " * self.indent_level

    def map_type(self, java_type: str) -> str:
        """Трансляция типа данных Java в тип C++"""
        mapped = self.TYPE_MAP.get(java_type, java_type)
        if mapped == 'string':
            self.needs_string = True
        return mapped

    def generate(self, node: ASTNode) -> str:
        """Главный диспетчер обхода AST-узлов"""
        method_name = f"gen_{node.__class__.__name__}"
        generator_method = getattr(self, method_name, self.generic_gen)
        return generator_method(node)

    def generic_gen(self, node: ASTNode):
        raise NotImplementedError(f"Генерация для узла {node.__class__.__name__} не реализована")

    # ==================== Программа и объявления ====================

    def gen_Program(self, node: Program) -> str:
        body_lines = []
        for stmt in node.statements:
            code = self.generate(stmt)
            if code.strip():
                body_lines.append(code)

        headers = []
        if self.needs_iostream:
            headers.append("#include <iostream>")
        if self.needs_string:
            headers.append("#include <string>")
        if self.needs_cmath:
            headers.append("#include <cmath>")

        header_code = "\n".join(headers)
        if header_code:
            header_code += "\n\nusing namespace std;\n\n"

        return header_code + "\n".join(body_lines)

    def gen_PackageDeclaration(self, node: PackageDeclaration) -> str:
        return f"// Package: {node.name}\n"

    def gen_ImportDeclaration(self, node: ImportDeclaration) -> str:
        if "Math" in node.path:
            self.needs_cmath = True
            return ""
        return f"// Import: {node.path}\n"

    def gen_ClassDeclaration(self, node: ClassDeclaration) -> str:
        """
        В учебном подмножестве Java главный класс 'раскрывается',
        а его методы становятся глобальными функциями C++ (п. 8.3)
        """
        lines = []
        for stmt in node.body:
            lines.append(self.generate(stmt))
        return "\n".join(lines)

    def gen_MethodDeclaration(self, node: MethodDeclaration) -> str:
        if node.name == "main":
            return self.gen_main_method(node)

        ret_type = self.map_type(node.return_type)
        params_str = ", ".join(node.params) if node.params else ""

        func_header = f"{self.indent()}{ret_type} {node.name}({params_str}) "
        func_body = self.generate(node.body)
        return f"{func_header}{func_body}\n"

    def gen_main_method(self, node: MethodDeclaration) -> str:
        """Генерация функции int main() для C++"""
        self.needs_iostream = True
        header = f"{self.indent()}int main() "

        self.indent_level += 1
        body_lines = []
        has_return = False

        for stmt in node.body.statements:
            if isinstance(stmt, ReturnStatement):
                has_return = True
            body_lines.append(self.generate(stmt))

        if not has_return:
            body_lines.append(f"{self.indent()}return 0;")

        self.indent_level -= 1

        body_str = "{\n" + "\n".join(body_lines) + f"\n{self.indent()}}}"
        return f"{header}{body_str}\n"

    def gen_Block(self, node: Block) -> str:
        lines = ["{"]
        self.indent_level += 1
        for stmt in node.statements:
            lines.append(self.generate(stmt))
        self.indent_level -= 1
        lines.append(f"{self.indent()}}}")
        return "\n".join(lines)

    # ==================== Управляющие конструкции ====================

    def gen_WhileStatement(self, node: WhileStatement) -> str:
        cond = self.generate(node.condition)
        body = self.generate(node.body)
        return f"{self.indent()}while ({cond}) {body}"

    def gen_DoWhileStatement(self, node: DoWhileStatement) -> str:
        body = self.generate(node.body)
        cond = self.generate(node.condition)
        return f"{self.indent()}do {body} while ({cond});"

    def gen_ForStatement(self, node: ForStatement) -> str:
        init_str = self.generate(node.init).strip().rstrip(";\n ") if node.init else ""
        cond_str = self.generate(node.condition).strip() if node.condition else ""
        upd_str = self.generate(node.update).strip().rstrip(";\n ") if node.update else ""
        body = self.generate(node.body)
        return f"{self.indent()}for ({init_str}; {cond_str}; {upd_str}) {body}"

    def gen_IfStatement(self, node: IfStatement) -> str:
        cond = self.generate(node.condition)
        then_part = self.generate(node.then_branch)
        result = f"{self.indent()}if ({cond}) {then_part}"
        if node.else_branch:
            else_part = self.generate(node.else_branch)
            result += f" else {else_part}"
        return result

    # ==================== Инструкции и присваивания ====================

    def gen_VariableDeclaration(self, node: VariableDeclaration) -> str:
        var_type = self.map_type(node.var_type)
        if node.value:
            val = self.generate(node.value)
            return f"{self.indent()}{var_type} {node.name} = {val};"
        return f"{self.indent()}{var_type} {node.name};"

    def gen_ConstantDeclaration(self, node: ConstantDeclaration) -> str:
        var_type = self.map_type(node.var_type)
        val = self.generate(node.value)
        return f"{self.indent()}const {var_type} {node.name} = {val};"

    def gen_Assignment(self, node: Assignment) -> str:
        val = self.generate(node.value)
        return f"{self.indent()}{node.target} = {val};"

    def gen_ReturnStatement(self, node: ReturnStatement) -> str:
        if node.value:
            return f"{self.indent()}return {self.generate(node.value)};"
        return f"{self.indent()}return;"

    def gen_MethodCall(self, node: MethodCall) -> str:
        if node.target == "System.out.println":
            self.needs_iostream = True
            if not node.args:
                return f"{self.indent()}cout << endl;"
            args_code = " << ".join(self.generate(arg) for arg in node.args)
            return f"{self.indent()}cout << {args_code} << endl;"

        args_code = ", ".join(self.generate(arg) for arg in node.args)
        return f"{self.indent()}{node.target}({args_code});"

    # ==================== Выражения и литералы ====================

    def gen_BinaryOperation(self, node: BinaryOperation) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        return f"{left} {node.operator} {right}"

    def gen_NumberLiteral(self, node: NumberLiteral) -> str:
        return node.value

    def gen_StringLiteral(self, node: StringLiteral) -> str:
        self.needs_string = True
        return node.value

    def gen_CharLiteral(self, node: CharLiteral) -> str:
        return node.value

    def gen_Identifier(self, node: Identifier) -> str:
        return node.name