from dataclasses import fields
from ast_structures import *


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

LIST_SUPPORT = """template <typename T>
class JavaList {
    std::shared_ptr<std::vector<T>> data;

public:
    JavaList() : data(std::make_shared<std::vector<T>>()) {}

    bool add(const T& item) {
        data->push_back(item);
        return true;
    }

    bool isEmpty() const {
        return data->empty();
    }

    int size() const {
        return static_cast<int>(data->size());
    }

    T& get(int index) const {
        return data->at(index);
    }

    bool remove(const T& item) {
        auto it = std::find(data->begin(), data->end(), item);
        if (it != data->end()) {
            data->erase(it);
            return true;
        }
        return false;
    }

    auto begin() { return data->begin(); }
    auto end() { return data->end(); }
    auto begin() const { return data->begin(); }
    auto end() const { return data->end(); }
};
"""

SCANNER_SUPPORT = """class JavaScanner {
    std::istream* in;

public:
    JavaScanner() : in(&std::cin) {}
    explicit JavaScanner(std::istream& stream) : in(&stream) {}

    int nextInt() {
        int val = 0;
        (*in) >> val;
        return val;
    }

    double nextDouble() {
        double val = 0.0;
        (*in) >> val;
        return val;
    }

    std::string nextLine() {
        std::string s;
        std::getline(*in, s);
        if (!s.empty() && s.back() == '\\r') s.pop_back();
        return s;
    }
};
"""

STRING_CONCAT_SUPPORT = """template <typename T>
std::string java_to_str(const T& val) {
    if constexpr (std::is_same_v<T, std::string>) return val;
    else if constexpr (std::is_same_v<T, bool>) return val ? "true" : "false";
    else if constexpr (std::is_same_v<T, char>) return std::string(1, val);
    else {
        std::ostringstream oss;
        oss << val;
        return oss.str();
    }
}

inline std::string java_to_str(const char* val) {
    return std::string(val);
}
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
        'void': 'void',
        'Scanner': 'JavaScanner',
    }

    def __init__(self):
        self.indent_level = 0
        self.includes = set()
        self.needs_iostream = False
        self.needs_string = False
        self.needs_cmath = False
        self.needs_arrays = False
        self.needs_list = False
        self.needs_scanner = False
        self.needs_string_concat = False
        self.needs_cstdlib = False
        self.needs_unsigned_shift = False
        self.in_main = False
        self.reserved_names = set()
        self.temporary_index = 0
        self.user_classes = set()
        self.var_types = {}
        self.method_return_types = {}

    def indent(self) -> str:
        return "    " * self.indent_level

    def map_type(self, java_type: str) -> str:
        if java_type.endswith('[]'):
            self.needs_arrays = True
            return f"JavaArray<{self.map_type(java_type[:-2])}>"
        if java_type.startswith('ArrayList<') and java_type.endswith('>'):
            self.needs_list = True
            inner = java_type[10:-1].strip()
            return f"JavaList<{self.map_type(inner)}>"
        if java_type == 'Scanner':
            self.needs_scanner = True
            self.needs_iostream = True
            self.needs_string = True
            return 'JavaScanner'
        if java_type in self.user_classes:
            self.needs_arrays = True  # для <memory>
            return f"std::shared_ptr<{java_type}>"
        mapped = self.TYPE_MAP.get(java_type, java_type)
        if mapped == 'string':
            self.needs_string = True
        return mapped

    def generate(self, node: ASTNode) -> str:
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
        if isinstance(node, ObjectCreation) and node.class_name == 'ArrayList' and not node.type_args:
            return f"{self.map_type(java_type)}()"
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

    @staticmethod
    def has_main_method(cls: ClassDeclaration) -> bool:
        return any(isinstance(s, MethodDeclaration) and s.name == 'main' for s in cls.body)

    def collect_type_info(self, node: Program):
        for stmt in node.statements:
            if isinstance(stmt, ClassDeclaration):
                for member in stmt.body:
                    if isinstance(member, (VariableDeclaration, ConstantDeclaration)):
                        self.var_types[member.name] = member.var_type
                    elif isinstance(member, MethodDeclaration):
                        self.method_return_types[member.name] = member.return_type
                        for p in member.params:
                            self.var_types[p.name] = p.var_type
                    elif isinstance(member, ConstructorDeclaration):
                        for p in member.params:
                            self.var_types[p.name] = p.var_type
            elif isinstance(stmt, MethodDeclaration):
                self.method_return_types[stmt.name] = stmt.return_type

    def is_user_class_expr(self, node) -> bool:
        if isinstance(node, ThisExpression):
            return True
        if isinstance(node, Identifier):
            return self.var_types.get(node.name) in self.user_classes
        if isinstance(node, ObjectCreation):
            return node.class_name in self.user_classes
        if isinstance(node, MethodCall) and isinstance(node.target, str):
            return self.method_return_types.get(node.target) in self.user_classes
        if isinstance(node, ArrayAccess) and isinstance(node.array, Identifier):
            t = self.var_types.get(node.array.name, "")
            return t.endswith("[]") and t[:-2] in self.user_classes
        return False

    # ==================== Программа и объявления ====================

    def gen_Program(self, node: Program) -> str:
        self.reserve_names(node)
        self.collect_type_info(node)

        all_classes = [stmt for stmt in node.statements if isinstance(stmt, ClassDeclaration)]
        main_classes = [c for c in all_classes if self.has_main_method(c)]
        if main_classes:
            helper_classes = [c for c in all_classes if not self.has_main_method(c)]
        elif len(all_classes) > 1:
            helper_classes = all_classes[1:]
        else:
            helper_classes = []

        self.user_classes = {c.name for c in helper_classes}

        body_lines = []
        if helper_classes:
            body_lines.append('\n'.join(f"class {c.name};" for c in helper_classes))
            for helper in helper_classes:
                body_lines.append(self.gen_oop_class(helper))

        methods = [stmt for stmt in node.statements
                   if isinstance(stmt, MethodDeclaration) and stmt.name != 'main']
        if methods:
            body_lines.append('\n'.join(self.method_signature(method) + ';' for method in methods))

        for stmt in node.statements:
            if isinstance(stmt, ClassDeclaration) and stmt.name in self.user_classes:
                continue
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
        if self.needs_cstdlib:
            headers.append("#include <cstdlib>")
        if self.needs_string_concat:
            headers.append("#include <sstream>")
        if self.needs_arrays or self.needs_list:
            headers.extend(["#include <vector>", "#include <memory>"])
        if self.needs_arrays:
            headers.extend(["#include <initializer_list>", "#include <stdexcept>"])
        if self.needs_list:
            headers.append("#include <algorithm>")
        if self.needs_arrays or self.needs_unsigned_shift or self.needs_string_concat:
            headers.append("#include <type_traits>")
        if self.needs_unsigned_shift:
            headers.append("#include <climits>")

        # Дедупликация заголовков с сохранением порядка
        unique_headers = list(dict.fromkeys(headers))
        header_code = "\n".join(unique_headers)
        if header_code:
            header_code += "\n\nusing namespace std;\n\n"

        support = ""
        if self.needs_string_concat:
            support += STRING_CONCAT_SUPPORT + "\n"
        if self.needs_arrays:
            support += ARRAY_SUPPORT + "\n"
        if self.needs_list:
            support += LIST_SUPPORT + "\n"
        if self.needs_scanner:
            support += SCANNER_SUPPORT + "\n"
        if self.needs_unsigned_shift:
            support += UNSIGNED_SHIFT_SUPPORT + "\n"

        return header_code + support + "\n".join(body_lines)

    def gen_oop_class(self, node: ClassDeclaration) -> str:
        lines = [f"class {node.name} {{"]
        private_members = []
        public_members = []

        for member in node.body:
            mods = getattr(member, 'modifiers', [])
            if 'private' in mods:
                private_members.append(member)
            else:
                public_members.append(member)

        self.indent_level += 1
        if private_members:
            lines.append("private:")
            for m in private_members:
                lines.append(self.generate_statement(m))
            lines.append("")

        if public_members:
            lines.append("public:")
            for m in public_members:
                lines.append(self.generate_statement(m))
        self.indent_level -= 1

        lines.append("};")

        has_to_string = any(isinstance(m, MethodDeclaration) and m.name == 'toString' for m in node.body)
        if has_to_string:
            self.needs_iostream = True
            self.needs_arrays = True
            lines.append(
                f"\ninline std::ostream& operator<<(std::ostream& os, const std::shared_ptr<{node.name}>& obj) {{\n"
                f"    if (!obj) return os << \"null\";\n"
                f"    return os << obj->toString();\n"
                f"}}"
            )
        return "\n".join(lines) + "\n"

    def gen_PackageDeclaration(self, node: PackageDeclaration) -> str:
        return f"// Package: {node.name}\n"

    def gen_ImportDeclaration(self, node: ImportDeclaration) -> str:
        if "Math" in node.path:
            self.needs_cmath = True
            return ""
        if node.path == "java.util.ArrayList":
            self.needs_list = True
            return ""
        if node.path == "java.util.Scanner":
            self.needs_scanner = True
            return ""
        return f"// Import: {node.path}\n"

    def gen_ClassDeclaration(self, node: ClassDeclaration) -> str:
        sections = []

        methods = [stmt for stmt in node.body
                   if isinstance(stmt, MethodDeclaration) and stmt.name != 'main']
        if methods:
            prototypes = '\n'.join(self.method_signature(m) + ';' for m in methods)
            sections.append(f"// --- Прототипы функций ---\n{prototypes}")

        variables = [stmt for stmt in node.body
                     if isinstance(stmt, (VariableDeclaration, ConstantDeclaration))]
        if variables:
            vars_code = '\n'.join(self.generate_statement(v) for v in variables)
            sections.append(f"// --- Состояние (переменные) ---\n{vars_code}")

        other_stmts = [stmt for stmt in node.body
                       if not isinstance(stmt, (VariableDeclaration, ConstantDeclaration))]
        for stmt in other_stmts:
            sections.append(self.generate_statement(stmt))

        return "\n\n".join(sections)

    def gen_ConstructorDeclaration(self, node: ConstructorDeclaration) -> str:
        for p in node.params:
            self.var_types[p.name] = p.var_type
        params = ', '.join(f"{self.map_type(param.var_type)} {param.name}" for param in node.params)
        body = self.generate(node.body)
        return f"{self.indent()}{node.name}({params}) {body}\n"

    def gen_MethodDeclaration(self, node: MethodDeclaration) -> str:
        for p in node.params:
            self.var_types[p.name] = p.var_type
        if node.name == "main":
            return self.gen_main_method(node)

        func_header = f"{self.indent()}{self.method_signature(node)} "
        func_body = self.generate(node.body)
        return f"{func_header}{func_body}\n"

    def gen_main_method(self, node: MethodDeclaration) -> str:
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

    def gen_ForEachStatement(self, node: ForEachStatement) -> str:
        self.var_types[node.var_name] = node.var_type
        cpp_type = self.map_type(node.var_type)
        iterable_code = self.generate(node.iterable)
        body = self.generate_body(node.body)
        return f"{self.indent()}for ({cpp_type} {node.var_name} : {iterable_code}) {body}"

    def gen_IfStatement(self, node: IfStatement) -> str:
        cond = self.generate(node.condition)
        then_part = self.generate_body(node.then_branch)
        result = f"{self.indent()}if ({cond}) {then_part}"
        if node.else_branch:
            else_part = self.generate_body(node.else_branch)
            result += f" else {else_part}"
        return result

    def gen_SwitchStatement(self, node: SwitchStatement) -> str:
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
        lines.append(f'{self.indent()}const auto {selector} = {value};')
        for declaration in declarations:
            self.var_types[declaration.name] = declaration.var_type
            if isinstance(declaration, ConstantDeclaration) and self.is_literal_constant(declaration.value):
                lines.append(self.generate(declaration))
            else:
                lines.append(f"{self.indent()}{self.map_type(declaration.var_type)} {declaration.name};")

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
            lines.append(f"{self.indent()};")
            self.indent_level -= 1
        self.indent_level -= 1
        lines.append(f"{self.indent()}}}")
        self.indent_level -= 1
        lines.append(f"{self.indent()}}}")
        return '\n'.join(lines)

    @staticmethod
    def expand_case_constant(node, constants, seen=frozenset()):
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
        self.var_types[node.name] = node.var_type
        var_type = self.map_type(node.var_type)
        if node.value:
            val = self.generate_initializer(node.value, node.var_type)
            return f"{self.indent()}{var_type} {node.name} = {val};"
        return f"{self.indent()}{var_type} {node.name};"

    def gen_ConstantDeclaration(self, node: ConstantDeclaration) -> str:
        self.var_types[node.name] = node.var_type
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

    def _is_string_op(self, node):
        if isinstance(node, StringLiteral):
            return True
        if isinstance(node, Identifier) and self.var_types.get(node.name) == 'String':
            return True
        if isinstance(node, MethodCall) and isinstance(node.target, str):
            ret = self.method_return_types.get(node.target)
            if ret == 'String' or node.target.endswith('.toString') or node.target.endswith('.nextLine'):
                return True
        if isinstance(node, BinaryOperation) and node.operator == '+':
            return self._is_string_op(node.left) or self._is_string_op(node.right)
        return False

    def _flatten_cout_args(self, node):
        if isinstance(node, BinaryOperation) and node.operator == '+' and self._is_string_op(node):
            return self._flatten_cout_args(node.left) + self._flatten_cout_args(node.right)
        return [self.generate(node)]

    def _flatten_str_concat(self, node):
        if isinstance(node, BinaryOperation) and node.operator == '+' and self._is_string_op(node):
            return self._flatten_str_concat(node.left) + self._flatten_str_concat(node.right)
        return [node]

    def gen_MethodCall(self, node: MethodCall):
        if node.target in ("System.out.println", "System.out.print"):
            self.needs_iostream = True
            all_parts = []
            for arg in node.args:
                all_parts.extend(self._flatten_cout_args(arg))
            args_code = ''.join(f' << {part}' for part in all_parts)
            ending = ' << std::endl' if node.target == 'System.out.println' else ''
            return f"(std::cout << std::boolalpha{args_code}{ending})"

        if node.target == "System.exit":
            self.needs_cstdlib = True
            args_code = ", ".join(self.generate(arg) for arg in node.args)
            return f"std::exit({args_code})"

        args_code = ", ".join(self.generate(arg) for arg in node.args)
        if isinstance(node.target, str):
            if node.target.startswith('Math.'):
                self.needs_cmath = True
                return f"std::{node.target[5:]}({args_code})"
            if '.' in node.target:
                obj_name, method_name = node.target.rsplit('.', 1)
                if self.var_types.get(obj_name) in self.user_classes:
                    return f"{obj_name}->{method_name}({args_code})"
                return f"{obj_name}.{method_name}({args_code})"
            return f"{node.target}({args_code})"

        target = self.generate(node.target)
        return f"{target}({args_code})"

    # ==================== Выражения и литералы ====================

    def gen_ObjectCreation(self, node: ObjectCreation) -> str:
        if node.class_name == 'Scanner':
            self.needs_scanner = True
            self.needs_iostream = True
            self.needs_string = True
            args_code = ", ".join(
                "std::cin" if (isinstance(a, MemberAccess) and isinstance(a.target, Identifier)
                               and a.target.name == "System" and a.member == "in")
                else self.generate(a)
                for a in node.args
            )
            return f"JavaScanner({args_code})"

        if node.class_name == 'ArrayList':
            self.needs_list = True
            inner = ', '.join(self.map_type(t) for t in node.type_args)
            return f"JavaList<{inner}>()"

        args_code = ", ".join(self.generate(arg) for arg in node.args)
        if node.class_name in self.user_classes:
            self.needs_arrays = True
            return f"std::make_shared<{node.class_name}>({args_code})"
        return f"{node.class_name}({args_code})"

    def gen_ThisExpression(self, node: ThisExpression) -> str:
        return "this"

    def gen_TernaryOperation(self, node: TernaryOperation) -> str:
        cond = self.generate(node.condition)
        t_expr = self.generate(node.true_expr)
        f_expr = self.generate(node.false_expr)
        return f"({cond} ? {t_expr} : {f_expr})"

    def gen_BinaryOperation(self, node: BinaryOperation) -> str:
        if node.operator == '+' and self._is_string_op(node):
            self.needs_string_concat = True
            self.needs_string = True
            parts = self._flatten_str_concat(node)
            converted = [f"java_to_str({self.generate(p)})" for p in parts]
            return f"({' + '.join(converted)})"

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
        if isinstance(node.target, Identifier) and node.target.name == 'System' and node.member == 'in':
            return 'std::cin'
        target = self.generate(node.target)
        if node.member == 'length':
            return f"{target}.length()"
        op = '->' if self.is_user_class_expr(node.target) else '.'
        return f"{target}{op}{node.member}"

    def gen_ArrayCreation(self, node: ArrayCreation) -> str:
        java_type = node.element_type + '[]' * len(node.dimensions)
        if node.initializer is not None:
            return self.generate_initializer(node.initializer, java_type)
        mapped = self.map_type(java_type)
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