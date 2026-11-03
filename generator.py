from dataclasses import fields

from ast_structures import *


# Общие данные сохраняют ссылочную семантику Java при присваивании и передаче
# массива в метод. Вложенные массивы создаются отдельно для каждой строки.
ARRAY_SUPPORT = """struct JavaArraySizes {
    std::vector<int> values;

    JavaArraySizes(std::initializer_list<int> sizes) : values(sizes) {
        for (int size : values) {
            if (size < 0) throw std::length_error("Negative array size");
        }
    }
};

template <typename T> class JavaArray;
template <typename T> struct IsJavaArray : std::false_type {};
template <typename T> struct IsJavaArray<JavaArray<T>> : std::true_type {};

template <typename T>
class JavaArray {
    std::shared_ptr<std::vector<T>> data;

    void check_data() const {
        if (!data) throw std::runtime_error("Null array reference");
    }

public:
    JavaArray() = default;

    explicit JavaArray(int size) {
        if (size < 0) throw std::length_error("Negative array size");
        data = std::make_shared<std::vector<T>>(size);
    }

    JavaArray(std::initializer_list<T> values)
        : data(std::make_shared<std::vector<T>>(values)) {}

    explicit JavaArray(const JavaArraySizes& sizes, std::size_t dimension = 0)
        : JavaArray(sizes.values.at(dimension)) {
        if constexpr (IsJavaArray<T>::value) {
            if (dimension + 1 < sizes.values.size()) {
                for (auto& item : *data) item = T(sizes, dimension + 1);
            }
        }
    }

    int length() const {
        check_data();
        return static_cast<int>(data->size());
    }

    typename std::vector<T>::reference operator[](int index) const {
        check_data();
        return data->at(index);
    }

    bool operator==(const JavaArray& other) const { return data == other.data; }
    bool operator!=(const JavaArray& other) const { return data != other.data; }
};
"""

UNSIGNED_SHIFT_SUPPORT = """template <typename T, typename U>
auto java_unsigned_shift(T value, U count) -> decltype(+value) {
    using Result = decltype(+value);
    using Unsigned = typename std::make_unsigned<Result>::type;
    constexpr unsigned int mask = sizeof(Result) * CHAR_BIT - 1;
    return static_cast<Result>(static_cast<Unsigned>(value) >> (count & mask));
}

template <typename T, typename U>
T& java_unsigned_shift_assign(T& value, U count) {
    value = static_cast<T>(java_unsigned_shift(value, count));
    return value;
}
"""


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
        self.needs_arrays = False
        self.needs_unsigned_shift = False
        self.in_main = False
        self.reserved_names = set()
        self.temporary_index = 0

    def indent(self) -> str:
        return "    " * self.indent_level

    def map_type(self, java_type: str) -> str:
        """Трансляция типа данных Java в тип C++"""
        if java_type.endswith('[]'):
            self.needs_arrays = True
            return f"JavaArray<{self.map_type(java_type[:-2])}>"
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

    def generate_statement(self, node):
        if isinstance(node, MethodCall):
            return f"{self.indent()}{self.generate(node)};"
        if isinstance(node, Block):
            return self.indent() + self.generate(node)
        return self.generate(node)

    def generate_body(self, node):
        # Скобки также устраняют неоднозначность dangling else при вложенных if.
        return self.generate(node if isinstance(node, Block) else Block([node]))

    def method_signature(self, node):
        params = ', '.join(f"{self.map_type(param.var_type)} {param.name}" for param in node.params)
        return f"{self.map_type(node.return_type)} {node.name}({params})"

    def reserve_names(self, node):
        if isinstance(node, str):
            self.reserved_names.add(node)
        elif isinstance(node, ASTNode):
            for field in fields(node):
                value = getattr(node, field.name)
                for child in value if isinstance(value, list) else [value]:
                    self.reserve_names(child)

    def temporary_name(self, prefix):
        while True:
            name = f'{prefix}_{self.temporary_index}'
            self.temporary_index += 1
            if name not in self.reserved_names:
                self.reserved_names.add(name)
                return name

    def generate_initializer(self, node, java_type):
        if not isinstance(node, ArrayInitializer):
            return self.generate(node)
        if not java_type.endswith('[]'):
            raise SyntaxError("Глубина инициализатора не соответствует размерности массива")
        element_type = java_type[:-2]
        values = ', '.join(self.generate_initializer(element, element_type) for element in node.elements)
        return f"{self.map_type(java_type)}({{{values}}})"

    @staticmethod
    def uses_identifier(node, name):
        if isinstance(node, Identifier):
            return node.name == name
        if isinstance(node, Assignment) and node.target == name:
            return True
        if not isinstance(node, ASTNode):
            return False
        for field in fields(node):
            value = getattr(node, field.name)
            children = value if isinstance(value, list) else [value]
            if any(Generator.uses_identifier(child, name) for child in children):
                return True
        return False

    @staticmethod
    def is_literal_constant(node):
        if isinstance(node, (NumberLiteral, CharLiteral, BooleanLiteral)):
            return True
        if isinstance(node, UnaryOperation) and node.operator not in ('++', '--'):
            return Generator.is_literal_constant(node.operand)
        if isinstance(node, BinaryOperation) and node.operator != '>>>':
            return (Generator.is_literal_constant(node.left)
                    and Generator.is_literal_constant(node.right))
        return False

    # ==================== Программа и объявления ====================

    def gen_Program(self, node: Program) -> str:
        self.reserve_names(node)
        body_lines = []
        methods = [stmt for stmt in node.statements
                   if isinstance(stmt, MethodDeclaration) and stmt.name != 'main']
        if methods:
            body_lines.append('\n'.join(self.method_signature(method) + ';' for method in methods))
        for stmt in node.statements:
            code = self.generate_statement(stmt)
            if code.strip():
                body_lines.append(code)

        headers = []
        if self.needs_iostream:
            headers.append("#include <iostream>")
        if self.needs_string:
            headers.append("#include <string>")
        if self.needs_cmath:
            headers.append("#include <cmath>")
        if self.needs_arrays:
            headers.extend(["#include <vector>", "#include <memory>",
                            "#include <initializer_list>", "#include <stdexcept>"])
        if self.needs_arrays or self.needs_unsigned_shift:
            headers.append("#include <type_traits>")
        if self.needs_unsigned_shift:
            headers.append("#include <climits>")

        header_code = "\n".join(headers)
        if header_code:
            header_code += "\n\nusing namespace std;\n\n"

        support = ARRAY_SUPPORT + '\n' if self.needs_arrays else ''
        if self.needs_unsigned_shift:
            support += UNSIGNED_SHIFT_SUPPORT + '\n'
        return header_code + support + "\n".join(body_lines)

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
        methods = [stmt for stmt in node.body
                   if isinstance(stmt, MethodDeclaration) and stmt.name != 'main']
        if methods:
            lines.append('\n'.join(self.method_signature(method) + ';' for method in methods))
        for stmt in node.body:
            lines.append(self.generate_statement(stmt))
        return "\n".join(lines)

    def gen_MethodDeclaration(self, node: MethodDeclaration) -> str:
        if node.name == "main":
            return self.gen_main_method(node)

        func_header = f"{self.indent()}{self.method_signature(node)} "
        func_body = self.generate(node.body)
        return f"{func_header}{func_body}\n"

    def gen_main_method(self, node: MethodDeclaration) -> str:
        """Генерация функции int main() для C++"""
        self.needs_iostream = True
        header = f"{self.indent()}int main() "

        self.indent_level += 1
        self.in_main = True
        body_lines = []
        if node.params and self.uses_identifier(node.body, node.params[0].name):
            if len(node.params) != 1 or node.params[0].var_type != 'String[]':
                raise SyntaxError("main должен принимать один параметр String[]")
            argc = self.temporary_name('java_argc')
            argv = self.temporary_name('java_argv')
            index = self.temporary_name('java_arg_index')
            header = f'int main(int {argc}, char* {argv}[]) '
            param = node.params[0]
            array_type = self.map_type(param.var_type)
            body_lines.extend([
                f"{self.indent()}{array_type} {param.name}({argc} - 1);",
                f"{self.indent()}for (int {index} = 1; {index} < {argc}; ++{index}) {{",
                f"{self.indent()}    {param.name}[{index} - 1] = {argv}[{index}];",
                f"{self.indent()}}}",
            ])
        has_return = False

        for stmt in node.body.statements:
            if isinstance(stmt, ReturnStatement):
                has_return = True
            body_lines.append(self.generate_statement(stmt))

        if not has_return:
            body_lines.append(f"{self.indent()}return 0;")

        self.indent_level -= 1
        self.in_main = False

        body_str = "{\n" + "\n".join(body_lines) + f"\n{self.indent()}}}"
        return f"{header}{body_str}\n"

    def gen_Block(self, node: Block) -> str:
        lines = ["{"]
        self.indent_level += 1
        for stmt in node.statements:
            lines.append(self.generate_statement(stmt))
        self.indent_level -= 1
        lines.append(f"{self.indent()}}}")
        return "\n".join(lines)

    # ==================== Управляющие конструкции ====================

    def gen_WhileStatement(self, node: WhileStatement) -> str:
        cond = self.generate(node.condition)
        body = self.generate_body(node.body)
        return f"{self.indent()}while ({cond}) {body}"

    def gen_DoWhileStatement(self, node: DoWhileStatement) -> str:
        body = self.generate_body(node.body)
        cond = self.generate(node.condition)
        return f"{self.indent()}do {body} while ({cond});"

    def gen_ForStatement(self, node: ForStatement) -> str:
        init_str = self.generate(node.init).strip().rstrip(";\n ") if node.init else ""
        cond_str = self.generate(node.condition).strip() if node.condition else ""
        upd_str = self.generate(node.update).strip().rstrip(";\n ") if node.update else ""
        body = self.generate_body(node.body)
        return f"{self.indent()}for ({init_str}; {cond_str}; {upd_str}) {body}"

    def gen_IfStatement(self, node: IfStatement) -> str:
        cond = self.generate(node.condition)
        then_part = self.generate_body(node.then_branch)
        result = f"{self.indent()}if ({cond}) {then_part}"
        if node.else_branch:
            else_part = self.generate_body(node.else_branch)
            result += f" else {else_part}"
        return result

    def gen_SwitchStatement(self, node: SwitchStatement) -> str:
        # В Java метки могут перескакивать через объявления переменных. В C++
        # это запрещено, поэтому объявления выносятся перед switch, а присваивания
        # остаются на исходных местах. Область видимости всего switch сохраняется.
        declarations = [stmt for case in node.cases for stmt in case.statements
                        if isinstance(stmt, (VariableDeclaration, ConstantDeclaration))]
        self.reserve_names(node)
        selector = self.temporary_name('java_switch_value')
        match = self.temporary_name('java_switch_case')
        value = self.generate(node.expression)
        if isinstance(node.expression, StringLiteral):
            self.needs_string = True
            value = f'std::string({value})'
        lines = [f"{self.indent()}{{"]
        self.indent_level += 1
        # Селектор вычисляется один раз, до входа в область переменных switch.
        lines.append(f'{self.indent()}const auto {selector} = {value};')
        for declaration in declarations:
            if isinstance(declaration, ConstantDeclaration) and self.is_literal_constant(declaration.value):
                lines.append(self.generate(declaration))
            else:
                lines.append(f"{self.indent()}{self.map_type(declaration.var_type)} {declaration.name};")

        # Выбор индекса позволяет одинаково обрабатывать int, char и String.
        # Последующий switch сохраняет fall-through, break и положение default.
        local_constants = {stmt.name: stmt.value for stmt in declarations
                           if isinstance(stmt, ConstantDeclaration)}
        lines.append(f'{self.indent()}int {match} = -1;')
        first = True
        for index, case in enumerate(node.cases):
            if case.value is not None:
                case_value = self.expand_case_constant(case.value, local_constants)
                keyword = 'if' if first else 'else if'
                lines.append(f'{self.indent()}{keyword} ({selector} == {self.generate(case_value)}) {match} = {index};')
                first = False
        lines.append(f"{self.indent()}switch ({match}) {{")
        self.indent_level += 1
        for index, case in enumerate(node.cases):
            label = 'default' if case.value is None else f'case {index}'
            lines.append(f"{self.indent()}{label}:")
            self.indent_level += 1
            for statement in case.statements:
                if isinstance(statement, (VariableDeclaration, ConstantDeclaration)):
                    hoisted_constant = (isinstance(statement, ConstantDeclaration)
                                        and self.is_literal_constant(statement.value))
                    if statement.value is not None and not hoisted_constant:
                        value = self.generate_initializer(statement.value, statement.var_type)
                        lines.append(f"{self.indent()}{statement.name} = {value};")
                else:
                    lines.append(self.generate_statement(statement))
            # Пустая инструкция делает последнюю пустую метку корректной в C++.
            lines.append(f"{self.indent()};")
            self.indent_level -= 1
        self.indent_level -= 1
        lines.append(f"{self.indent()}}}")
        self.indent_level -= 1
        lines.append(f"{self.indent()}}}")
        return '\n'.join(lines)

    @staticmethod
    def expand_case_constant(node, constants, seen=frozenset()):
        # final-константа из тела switch доступна в метках до выполнения ветки.
        if isinstance(node, Identifier) and node.name in constants:
            if node.name in seen:
                raise SyntaxError('Циклическое определение константы case')
            return Generator.expand_case_constant(constants[node.name], constants, seen | {node.name})
        if isinstance(node, BinaryOperation):
            return BinaryOperation(
                Generator.expand_case_constant(node.left, constants, seen), node.operator,
                Generator.expand_case_constant(node.right, constants, seen),
            )
        if isinstance(node, UnaryOperation):
            return UnaryOperation(node.operator, Generator.expand_case_constant(node.operand, constants, seen), node.postfix)
        return node

    def gen_BreakStatement(self, node: BreakStatement) -> str:
        return f"{self.indent()}break;"

    def gen_ContinueStatement(self, node: ContinueStatement) -> str:
        return f"{self.indent()}continue;"

    # ==================== Инструкции и присваивания ====================

    def gen_VariableDeclaration(self, node: VariableDeclaration) -> str:
        var_type = self.map_type(node.var_type)
        if node.value:
            val = self.generate_initializer(node.value, node.var_type)
            return f"{self.indent()}{var_type} {node.name} = {val};"
        return f"{self.indent()}{var_type} {node.name};"

    def gen_ConstantDeclaration(self, node: ConstantDeclaration) -> str:
        var_type = self.map_type(node.var_type)
        val = self.generate_initializer(node.value, node.var_type)
        return f"{self.indent()}const {var_type} {node.name} = {val};"

    def gen_Assignment(self, node: Assignment) -> str:
        val = self.generate(node.value)
        target = node.target if isinstance(node.target, str) else self.generate(node.target)
        if node.operator == '>>>=':
            self.needs_unsigned_shift = True
            return f"{self.indent()}java_unsigned_shift_assign({target}, {val});"
        return f"{self.indent()}{target} {node.operator} {val};"

    def gen_ExpressionStatement(self, node: ExpressionStatement) -> str:
        return f"{self.indent()}{self.generate(node.expression)};"

    def gen_ReturnStatement(self, node: ReturnStatement) -> str:
        if node.value:
            return f"{self.indent()}return {self.generate(node.value)};"
        return f"{self.indent()}return 0;" if self.in_main else f"{self.indent()}return;"

    def gen_MethodCall(self, node: MethodCall) -> str:
        if node.target in ("System.out.println", "System.out.print"):
            self.needs_iostream = True
            args_code = ''.join(f' << {self.generate(arg)}' for arg in node.args)
            ending = ' << std::endl' if node.target == 'System.out.println' else ''
            return f"(std::cout << std::boolalpha{args_code}{ending})"

        args_code = ", ".join(self.generate(arg) for arg in node.args)
        target = node.target if isinstance(node.target, str) else self.generate(node.target)
        if target.startswith('Math.'):
            self.needs_cmath = True
            target = 'std::' + target[5:]
        return f"{target}({args_code})"

    # ==================== Выражения и литералы ====================

    def gen_BinaryOperation(self, node: BinaryOperation) -> str:
        left = self.generate(node.left)
        right = self.generate(node.right)
        if node.operator == '>>>':
            self.needs_unsigned_shift = True
            return f"java_unsigned_shift({left}, {right})"
        return f"({left} {node.operator} {right})"

    def gen_UnaryOperation(self, node: UnaryOperation) -> str:
        operand = self.generate(node.operand)
        if node.postfix:
            return f"{operand}{node.operator}"
        if node.operator in ('++', '--'):
            return f"{node.operator}{operand}"
        return f"({node.operator}{operand})"

    def gen_ArrayAccess(self, node: ArrayAccess) -> str:
        return f"{self.generate(node.array)}[{self.generate(node.index)}]"

    def gen_MemberAccess(self, node: MemberAccess) -> str:
        target = self.generate(node.target)
        if node.member == 'length':
            return f"{target}.length()"
        return f"{target}.{node.member}"

    def gen_ArrayCreation(self, node: ArrayCreation) -> str:
        java_type = node.element_type + '[]' * len(node.dimensions)
        if node.initializer is not None:
            return self.generate_initializer(node.initializer, java_type)
        mapped = self.map_type(java_type)
        # Список инициализации вычисляет размеры слева направо, как в Java.
        sizes = ', '.join(self.generate(size) for size in node.dimensions if size is not None)
        return f"{mapped}(JavaArraySizes{{{sizes}}})"

    def gen_BooleanLiteral(self, node: BooleanLiteral) -> str:
        return node.value

    def gen_NumberLiteral(self, node: NumberLiteral) -> str:
        return node.value

    def gen_StringLiteral(self, node: StringLiteral) -> str:
        self.needs_string = True
        return node.value

    def gen_CharLiteral(self, node: CharLiteral) -> str:
        return node.value

    def gen_Identifier(self, node: Identifier) -> str:
        return node.name

    def gen_BooleanLiteral(self, node: BooleanLiteral) -> str:
        return node.value
