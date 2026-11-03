# semantic_analyzer.py
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from ast_structures import *


class SemanticError(Exception):
    """Исключение при нарушении контекстных условий (семантическая ошибка)"""
    pass


@dataclass
class Symbol:
    name: str
    type_name: str
    kind: str  # 'variable', 'constant', 'method', 'class'
    param_types: Optional[List[str]] = None  # Для методов


class SymbolTable:
    """Иерархическая таблица символов (стек областей видимости)"""
    def __init__(self):
        self.scopes: List[Dict[str, Symbol]] = [{}]  # Начинаем с глобальной области

    def enter_scope(self):
        """Открытие новой локальной области видимости (блок {})"""
        self.scopes.append({})

    def exit_scope(self):
        """Закрытие локальной области видимости"""
        if len(self.scopes) > 1:
            self.scopes.pop()

    def define(self, symbol: Symbol):
        """Регистрация идентификатора в текущей области видимости"""
        current_scope = self.scopes[-1]
        if symbol.name in current_scope:
            raise SemanticError(
                f"Повторное объявление идентификатора '{symbol.name}' в текущей области видимости."
            )
        current_scope[symbol.name] = symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        """Поиск идентификатора от текущей области видимости к глобальной"""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None


class SemanticAnalyzer:
    NUMERIC_TYPES: Set[str] = {'byte', 'short', 'int', 'long', 'float', 'double'}

    def __init__(self):
        self.symbols = SymbolTable()
        self.current_function_return_type: Optional[str] = None
        self.loop_depth = 0

        # Регистрируем встроенные функции Java
        self._init_builtins()

    def _init_builtins(self):
        """Регистрация стандартных функций (System.out.println)"""
        self.symbols.define(
            Symbol(
                name="System.out.println",
                type_name="void",
                kind="method",
                param_types=["ANY"]
            )
        )

    def analyze(self, ast: Program):
        """Точка входа для запуска семантического анализа"""
        self.visit(ast)

    def visit(self, node: ASTNode):
        """Диспетчер посещения узлов AST"""
        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode):
        # Если для узла нет специальной проверки, ничего не делаем
        pass

    # ==================== Программа и структуры ====================

    def visit_Program(self, node: Program):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_ClassDeclaration(self, node: ClassDeclaration):
        # Регистрация класса
        self.symbols.define(Symbol(name=node.name, type_name=node.name, kind="class"))
        self.symbols.enter_scope()

        for stmt in node.body:
            self.visit(stmt)

        self.symbols.exit_scope()

    def visit_MethodDeclaration(self, node: MethodDeclaration):
        # 1. Регистрация сигнатуры метода во внешней области
        self.symbols.define(
            Symbol(
                name=node.name,
                type_name=node.return_type,
                kind="method"
            )
        )

        # 2. Входим в область видимости тела метода
        self.symbols.enter_scope()
        previous_return_type = self.current_function_return_type
        self.current_function_return_type = node.return_type

        # Если переданы параметры (например, int a, double b)
        # В учебном парсере параметры идут строками [type, name]
        i = 0
        while i < len(node.params):
            param_type = node.params[i]
            if i + 1 < len(node.params):
                param_name = node.params[i + 1]
                self.symbols.define(Symbol(name=param_name, type_name=param_type, kind="variable"))
                i += 2
            else:
                break

        # Разбор тела метода
        self.visit(node.body)

        self.current_function_return_type = previous_return_type
        self.symbols.exit_scope()

    def visit_Block(self, node: Block):
        self.symbols.enter_scope()
        for stmt in node.statements:
            self.visit(stmt)
        self.symbols.exit_scope()

    # ==================== Объявления и Присваивания ====================

    def visit_VariableDeclaration(self, node: VariableDeclaration):
        val_type = None
        if node.value:
            val_type = self.visit(node.value)
            if not self._is_type_compatible(node.var_type, val_type):
                raise SemanticError(
                    f"Несовместимость типов: переменная '{node.name}' типа '{node.var_type}' "
                    f"не может быть инициализирована значением типа '{val_type}'."
                )

        self.symbols.define(
            Symbol(name=node.name, type_name=node.var_type, kind="variable")
        )

    def visit_ConstantDeclaration(self, node: ConstantDeclaration):
        val_type = self.visit(node.value)
        if not self._is_type_compatible(node.var_type, val_type):
            raise SemanticError(
                f"Несовместимость типов: константа '{node.name}' типа '{node.var_type}' "
                f"не может быть инициализирована значением типа '{val_type}'."
            )

        self.symbols.define(
            Symbol(name=node.name, type_name=node.var_type, kind="constant")
        )

    def visit_Assignment(self, node: Assignment):
        symbol = self.symbols.resolve(node.target)
        if not symbol:
            raise SemanticError(f"Использование необъявленной переменной '{node.target}'.")

        if symbol.kind == "constant":
            raise SemanticError(
                f"Попытка изменения значения константы '{node.target}'. "
                f"Присваивание константам запрещено."
            )

        val_type = self.visit(node.value)
        if not self._is_type_compatible(symbol.type_name, val_type):
            raise SemanticError(
                f"Несовместимость типов при присваивании: переменной '{node.target}' типа '{symbol.type_name}' "
                f"нельзя присвоить значение типа '{val_type}'."
            )

    # ==================== Управляющие конструкции ====================

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

    def visit_MethodCall(self, node: MethodCall):
        symbol = self.symbols.resolve(node.target)
        if not symbol:
            raise SemanticError(f"Вызов необъявленного метода '{node.target}'.")

        # Проверяем аргументы
        for arg in node.args:
            self.visit(arg)

        return symbol.type_name

    # ==================== Проверка выражений и типов ====================

    def visit_BinaryOperation(self, node: BinaryOperation) -> str:
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        op = node.operator

        # Арифметические операторы (+, -, *, /, %)
        if op in {'+', '-', '*', '/', '%'}:
            # Особенность: конкатенация строк в Java
            if op == '+' and (left_type == 'String' or right_type == 'String'):
                return 'String'

            if left_type in self.NUMERIC_TYPES and right_type in self.NUMERIC_TYPES:
                # Повышение типов (если один double, результат double)
                if 'double' in (left_type, right_type):
                    return 'double'
                if 'float' in (left_type, right_type):
                    return 'float'
                return 'int'

            raise SemanticError(
                f"Операция '{op}' недопустима для типов '{left_type}' и '{right_type}'."
            )

        # Операторы сравнения (==, !=, >, <, >=, <=)
        if op in {'>', '<', '>=', '<='}:
            if left_type in self.NUMERIC_TYPES and right_type in self.NUMERIC_TYPES:
                return "boolean"
            raise SemanticError(f"Сравнение '{op}' применимо только к числовым типам.")

        if op in {'==', '!='}:
            if self._is_type_compatible(left_type, right_type) or self._is_type_compatible(right_type, left_type):
                return "boolean"
            raise SemanticError(f"Нельзя сравнивать несовместимые типы '{left_type}' и '{right_type}'.")

        # Логические операторы (&&, ||)
        if op in {'&&', '||'}:
            if left_type == 'boolean' and right_type == 'boolean':
                return "boolean"
            raise SemanticError(f"Логический оператор '{op}' требует операнды типа boolean.")

        return "int"

    def visit_NumberLiteral(self, node: NumberLiteral) -> str:
        if '.' in node.value:
            return "double"
        return "int"

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

    def _is_type_compatible(self, target: str, source: str) -> bool:
        """Проверка совместимости типов (с учетом неявного приведения)"""
        if target == source:
            return True
        # Автоматическое расширение чисел (например, int -> double)
        if target in self.NUMERIC_TYPES and source in self.NUMERIC_TYPES:
            type_order = ['byte', 'short', 'int', 'long', 'float', 'double']
            if type_order.index(source) <= type_order.index(target):
                return True
        return False