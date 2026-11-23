from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from ast_structures import *


class SemanticError(Exception):
    pass


@dataclass
class Symbol:
    name: str
    type_name: str
    kind: str  # 'variable', 'constant', 'method', 'class'
    param_types: Optional[List[str]] = None


@dataclass
class ClassInfo:
    name: str
    fields: Dict[str, Symbol] = field(default_factory=dict)
    methods: Dict[str, Symbol] = field(default_factory=dict)


class SymbolTable:
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = [{}]

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def define(self, symbol: Symbol):
        current_scope = self.scopes[-1]
        if symbol.name in current_scope:
            raise SemanticError(
                f"Повторное объявление идентификатора '{symbol.name}' в текущей области видимости."
            )
        current_scope[symbol.name] = symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None


class SemanticAnalyzer:
    NUMERIC_TYPES: Set[str] = {'byte', 'short', 'int', 'long', 'float', 'double'}

    def __init__(self):
        self.symbols = SymbolTable()
        self.classes: Dict[str, ClassInfo] = {}
        self.current_class: Optional[str] = None
        self.current_function_return_type: Optional[str] = None
        self.current_line: Optional[int] = None
        self.loop_depth = 0
        self._init_builtins()

    def _init_builtins(self):
        for name in ("System.out.println", "System.out.print", "System.exit"):
            self.symbols.define(Symbol(name=name, type_name="void", kind="method", param_types=["ANY"]))

    def analyze(self, ast: Program):
        self.visit(ast)

    def visit(self, node: ASTNode):
        prev_line = self.current_line
        node_line = getattr(node, '_line', None)
        if node_line is not None:
            self.current_line = node_line
        try:
            method_name = f"visit_{node.__class__.__name__}"
            visitor = getattr(self, method_name, self.generic_visit)
            return visitor(node)
        except SemanticError as e:
            msg = str(e)
            if self.current_line is not None and not msg.startswith("Строка "):
                raise SemanticError(f"Строка {self.current_line}: {msg}") from None
            raise
        finally:
            self.current_line = prev_line

    def generic_visit(self, node: ASTNode):
        pass

    def _pre_register_classes(self, statements: List[ASTNode]):
        for stmt in statements:
            if isinstance(stmt, ClassDeclaration):
                if stmt.name in self.classes:
                    raise SemanticError(f"Повторное объявление класса '{stmt.name}'.")
                info = ClassInfo(name=stmt.name)
                for member in stmt.body:
                    if isinstance(member, VariableDeclaration):
                        info.fields[member.name] = Symbol(member.name, member.var_type, "variable")
                    elif isinstance(member, ConstantDeclaration):
                        info.fields[member.name] = Symbol(member.name, member.var_type, "constant")
                    elif isinstance(member, MethodDeclaration):
                        info.methods[member.name] = Symbol(member.name, member.return_type, "method")
                self.classes[stmt.name] = info

    def visit_Program(self, node: Program):
        self._pre_register_classes(node.statements)
        for stmt in node.statements:
            if isinstance(stmt, MethodDeclaration):
                if stmt.name not in self.symbols.scopes[-1]:
                    self.symbols.define(Symbol(name=stmt.name, type_name=stmt.return_type, kind="method"))
        for stmt in node.statements:
            self.visit(stmt)

    def visit_ClassDeclaration(self, node: ClassDeclaration):
        if not self.symbols.resolve(node.name):
            self.symbols.define(Symbol(name=node.name, type_name=node.name, kind="class"))

        prev_class = self.current_class
        self.current_class = node.name
        self.symbols.enter_scope()

        for stmt in node.body:
            if isinstance(stmt, MethodDeclaration):
                if stmt.name not in self.symbols.scopes[-1]:
                    self.symbols.define(Symbol(name=stmt.name, type_name=stmt.return_type, kind="method"))

        for stmt in node.body:
            self.visit(stmt)

        self.symbols.exit_scope()
        self.current_class = prev_class

    def visit_ConstructorDeclaration(self, node: ConstructorDeclaration):
        if self.current_class and node.name != self.current_class:
            raise SemanticError(f"Имя конструктора '{node.name}' должно совпадать с именем класса '{self.current_class}'.")
        self.symbols.enter_scope()
        prev_return = self.current_function_return_type
        self.current_function_return_type = "void"

        for param in node.params:
            self.symbols.define(Symbol(name=param.name, type_name=param.var_type, kind="variable"))

        self.visit(node.body)
        self.current_function_return_type = prev_return
        self.symbols.exit_scope()

    def visit_MethodDeclaration(self, node: MethodDeclaration):
        if node.name not in self.symbols.scopes[-1]:
            self.symbols.define(Symbol(name=node.name, type_name=node.return_type, kind="method"))

        self.symbols.enter_scope()
        previous_return_type = self.current_function_return_type
        self.current_function_return_type = node.return_type

        for param in node.params:
            self.symbols.define(Symbol(name=param.name, type_name=param.var_type, kind="variable"))

        self.visit(node.body)

        self.current_function_return_type = previous_return_type
        self.symbols.exit_scope()

    def visit_Block(self, node: Block):
        self.symbols.enter_scope()
        for stmt in node.statements:
            self.visit(stmt)
        self.symbols.exit_scope()

    def visit_VariableDeclaration(self, node: VariableDeclaration):
        if node.value:
            val_type = self.visit(node.value)
            if not self._is_type_compatible(node.var_type, val_type):
                raise SemanticError(
                    f"Несовместимость типов: переменная '{node.name}' типа '{node.var_type}' "
                    f"не может быть инициализирована значением типа '{val_type}'."
                )

        self.symbols.define(Symbol(name=node.name, type_name=node.var_type, kind="variable"))

    def visit_ConstantDeclaration(self, node: ConstantDeclaration):
        val_type = self.visit(node.value)
        if not self._is_type_compatible(node.var_type, val_type):
            raise SemanticError(
                f"Несовместимость типов: константа '{node.name}' типа '{node.var_type}' "
                f"не может быть инициализирована значением типа '{val_type}'."
            )

        self.symbols.define(Symbol(name=node.name, type_name=node.var_type, kind="constant"))

    def visit_Assignment(self, node: Assignment):
        if isinstance(node.target, str):
            symbol = self.symbols.resolve(node.target)
            if not symbol:
                raise SemanticError(f"Использование необъявленной переменной '{node.target}'.")
            if symbol.kind == "constant":
                raise SemanticError(
                    f"Попытка изменения значения константы '{node.target}'. "
                    f"Присваивание константам запрещено."
                )
            target_type = symbol.type_name
            target_name = node.target
        else:
            target_type = self.visit(node.target)
            target_name = "элемент"

        val_type = self.visit(node.value)
        if not self._is_type_compatible(target_type, val_type):
            raise SemanticError(
                f"Несовместимость типов при присваивании: для '{target_name}' типа '{target_type}' "
                f"нельзя присвоить значение типа '{val_type}'."
            )

    def visit_WhileStatement(self, node: WhileStatement):
        cond_type = self.visit(node.condition)
        if cond_type != "boolean":
            raise SemanticError(f"Условие в цикле 'while' должно быть boolean, получено '{cond_type}'.")

        self.loop_depth += 1
        self.visit(node.body)
        self.loop_depth -= 1

    def visit_DoWhileStatement(self, node: DoWhileStatement):
        cond_type = self.visit(node.condition)
        if cond_type != "boolean":
            raise SemanticError(f"Условие в цикле 'do-while' должно быть boolean, получено '{cond_type}'.")

        self.loop_depth += 1
        self.visit(node.body)
        self.loop_depth -= 1

    def visit_ForStatement(self, node: ForStatement):
        self.symbols.enter_scope()
        if node.init:
            self.visit(node.init)

        if node.condition:
            cond_type = self.visit(node.condition)
            if cond_type != "boolean":
                raise SemanticError(f"Условие в цикле 'for' должно быть boolean, получено '{cond_type}'.")

        if node.update:
            self.visit(node.update)

        self.loop_depth += 1
        self.visit(node.body)
        self.loop_depth -= 1
        self.symbols.exit_scope()

    def visit_ForEachStatement(self, node: ForEachStatement):
        iter_type = self.visit(node.iterable)
        if iter_type.startswith("ArrayList<") and iter_type.endswith(">"):
            elem_type = iter_type[10:-1].strip()
        elif iter_type.endswith("[]"):
            elem_type = iter_type[:-2]
        else:
            raise SemanticError(f"Цикл for-each неприменим к типу '{iter_type}'.")

        if not self._is_type_compatible(node.var_type, elem_type):
            raise SemanticError(
                f"Несовместимый тип элемента '{node.var_type}' в for-each для коллекции типа '{iter_type}'."
            )

        self.symbols.enter_scope()
        self.symbols.define(Symbol(name=node.var_name, type_name=node.var_type, kind="variable"))
        self.loop_depth += 1
        self.visit(node.body)
        self.loop_depth -= 1
        self.symbols.exit_scope()

    def visit_IfStatement(self, node: IfStatement):
        cond_type = self.visit(node.condition)
        if cond_type != "boolean":
            raise SemanticError(f"Условие оператора 'if' должно быть boolean, получено '{cond_type}'.")

        self.visit(node.then_branch)
        if node.else_branch:
            self.visit(node.else_branch)

    def visit_ReturnStatement(self, node: ReturnStatement):
        if self.current_function_return_type == "void" and node.value is not None:
            raise SemanticError("Функция с типом void не может возвращать значение.")

        if self.current_function_return_type != "void":
            if node.value is None:
                raise SemanticError(
                    f"Функция должна возвращать значение типа '{self.current_function_return_type}'."
                )
            val_type = self.visit(node.value)
            if not self._is_type_compatible(self.current_function_return_type, val_type):
                raise SemanticError(
                    f"Возвращаемое значение типа '{val_type}' не соответствует "
                    f"типу функции '{self.current_function_return_type}'."
                )

    def _resolve_method_return(self, obj_type: str, method_name: str) -> Optional[str]:
        if obj_type == "Scanner":
            return {"nextInt": "int", "nextDouble": "double", "nextLine": "String", "next": "String"}.get(method_name)
        if obj_type.startswith("ArrayList<") and obj_type.endswith(">"):
            elem = obj_type[10:-1].strip()
            return {"add": "boolean", "isEmpty": "boolean", "remove": "boolean", "size": "int", "get": elem}.get(method_name)
        if obj_type in self.classes:
            if method_name == "toString":
                return "String"
            m = self.classes[obj_type].methods.get(method_name)
            return m.type_name if m else None
        return None

    def visit_MethodCall(self, node: MethodCall):
        if isinstance(node.target, str):
            if node.target.startswith("Math."):
                for arg in node.args:
                    self.visit(arg)
                return "double"

            if node.target in ("System.out.println", "System.out.print", "System.exit"):
                for arg in node.args:
                    self.visit(arg)
                return "void"

            symbol = self.symbols.resolve(node.target)
            if symbol:
                for arg in node.args:
                    self.visit(arg)
                return symbol.type_name

            if "." in node.target:
                obj_name, method_name = node.target.rsplit(".", 1)
                obj_sym = self.symbols.resolve(obj_name)
                if obj_sym:
                    ret = self._resolve_method_return(obj_sym.type_name, method_name)
                    if ret is not None:
                        for arg in node.args:
                            self.visit(arg)
                        return ret

            raise SemanticError(f"Вызов необъявленного метода '{node.target}'.")

        for arg in node.args:
            self.visit(arg)
        return "void"

    def visit_ObjectCreation(self, node: ObjectCreation) -> str:
        for arg in node.args:
            self.visit(arg)
        if node.class_name == "ArrayList":
            if node.type_args:
                return f"ArrayList<{', '.join(node.type_args)}>"
            return "ArrayList<>"
        if node.class_name == "Scanner":
            return "Scanner"
        if node.class_name in self.classes:
            return node.class_name
        raise SemanticError(f"Неизвестный класс '{node.class_name}'.")

    def visit_ThisExpression(self, node: ThisExpression) -> str:
        if not self.current_class:
            raise SemanticError("Ключевое слово 'this' допустимо только внутри класса.")
        return self.current_class

    def visit_TernaryOperation(self, node: TernaryOperation) -> str:
        cond_type = self.visit(node.condition)
        if cond_type != "boolean":
            raise SemanticError(f"Условие тернарного оператора должно быть boolean, получено '{cond_type}'.")
        t_type = self.visit(node.true_expr)
        f_type = self.visit(node.false_expr)
        if self._is_type_compatible(t_type, f_type):
            return t_type
        if self._is_type_compatible(f_type, t_type):
            return f_type
        raise SemanticError(f"Несовместимые типы ветвей тернарного оператора: '{t_type}' и '{f_type}'.")

    def visit_BinaryOperation(self, node: BinaryOperation) -> str:
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        op = node.operator

        if op in {'+', '-', '*', '/', '%', '<<', '>>', '>>>', '&', '|', '^'}:
            if op == '+' and (left_type == 'String' or right_type == 'String'):
                return 'String'

            if left_type in self.NUMERIC_TYPES and right_type in self.NUMERIC_TYPES:
                if 'double' in (left_type, right_type):
                    return 'double'
                if 'float' in (left_type, right_type):
                    return 'float'
                return 'int'

            raise SemanticError(
                f"Операция '{op}' недопустима для типов '{left_type}' и '{right_type}'."
            )

        if op in {'>', '<', '>=', '<='}:
            if left_type in self.NUMERIC_TYPES and right_type in self.NUMERIC_TYPES:
                return "boolean"
            raise SemanticError(f"Сравнение '{op}' применимо только к числовым типам.")

        if op in {'==', '!='}:
            if self._is_type_compatible(left_type, right_type) or self._is_type_compatible(right_type, left_type):
                return "boolean"
            raise SemanticError(f"Нельзя сравнивать несовместимые типы '{left_type}' и '{right_type}'.")

        if op in {'&&', '||'}:
            if left_type == 'boolean' and right_type == 'boolean':
                return "boolean"
            raise SemanticError(f"Логический оператор '{op}' требует операнды типа boolean.")

        return "int"

    def visit_NumberLiteral(self, node: NumberLiteral) -> str:
        return "double" if '.' in node.value else "int"

    def visit_StringLiteral(self, node: StringLiteral) -> str:
        return "String"

    def visit_CharLiteral(self, node: CharLiteral) -> str:
        return "char"

    def visit_Identifier(self, node: Identifier) -> str:
        symbol = self.symbols.resolve(node.name)
        if not symbol:
            raise SemanticError(f"Переменная '{node.name}' не объявлена перед использованием.")
        return symbol.type_name

    def visit_BooleanLiteral(self, node: BooleanLiteral) -> str:
        return "boolean"

    def visit_ArrayInitializer(self, node: ArrayInitializer) -> str:
        elem_types = [self.visit(elem) for elem in node.elements]
        elem_type = elem_types[0] if elem_types else "int"
        return f"{elem_type}[]"

    def visit_ArrayCreation(self, node: ArrayCreation) -> str:
        for dim in node.dimensions:
            if dim is not None:
                dim_type = self.visit(dim)
                if dim_type not in self.NUMERIC_TYPES:
                    raise SemanticError("Размерность массива должна быть целым числом.")
        if node.initializer:
            return self.visit(node.initializer)
        return node.element_type + "[]" * len(node.dimensions)

    def visit_ArrayAccess(self, node: ArrayAccess) -> str:
        arr_type = self.visit(node.array)
        idx_type = self.visit(node.index)
        if idx_type not in self.NUMERIC_TYPES:
            raise SemanticError("Индекс массива должен быть числом.")
        if not arr_type.endswith("[]"):
            raise SemanticError(f"Попытка индексации переменной не-массива типа '{arr_type}'.")
        return arr_type[:-2]

    def visit_MemberAccess(self, node: MemberAccess) -> str:
        if isinstance(node.target, Identifier) and node.target.name == "System" and node.member == "in":
            return "InputStream"
        target_type = self.visit(node.target)
        if node.member == "length" and target_type.endswith("[]"):
            return "int"
        if target_type in self.classes and node.member in self.classes[target_type].fields:
            return self.classes[target_type].fields[node.member].type_name
        raise SemanticError(f"Поле '{node.member}' не найдено у типа '{target_type}'.")

    def visit_UnaryOperation(self, node: UnaryOperation) -> str:
        op_type = self.visit(node.operand)
        if node.operator in ('++', '--', '+', '-', '~'):
            if op_type not in self.NUMERIC_TYPES:
                raise SemanticError(f"Оператор '{node.operator}' применим только к числам.")
            return op_type
        if node.operator == '!':
            if op_type != 'boolean':
                raise SemanticError("Оператор '!' применим только к типу boolean.")
            return 'boolean'
        return op_type

    def visit_ExpressionStatement(self, node: ExpressionStatement):
        self.visit(node.expression)

    def visit_SwitchStatement(self, node: SwitchStatement):
        expr_type = self.visit(node.expression)
        self.symbols.enter_scope()
        for case in node.cases:
            if case.value is not None:
                case_type = self.visit(case.value)
                if not self._is_type_compatible(expr_type, case_type):
                    raise SemanticError(f"Тип метки case '{case_type}' не совпадает с типом switch '{expr_type}'.")
            for stmt in case.statements:
                self.visit(stmt)
        self.symbols.exit_scope()

    def visit_BreakStatement(self, node: BreakStatement):
        pass

    def visit_ContinueStatement(self, node: ContinueStatement):
        pass

    def _is_type_compatible(self, target: str, source: str) -> bool:
        if target == source:
            return True
        if target.startswith("ArrayList<") and source == "ArrayList<>":
            return True
        if target in self.NUMERIC_TYPES and source in self.NUMERIC_TYPES:
            type_order = ['byte', 'short', 'int', 'long', 'float', 'double']
            if type_order.index(source) <= type_order.index(target):
                return True
        return False