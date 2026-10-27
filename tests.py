import pytest
from analizer import Analizer
from parser import Parser
from ast_structures import (
    Program, PackageDeclaration, ImportDeclaration, ClassDeclaration,
    MethodDeclaration, VariableDeclaration, ConstantDeclaration,
    Assignment, MethodCall, WhileStatement, DoWhileStatement,
    ForStatement, IfStatement, Block, BinaryOperation,
    NumberLiteral, StringLiteral, CharLiteral, Identifier, ReturnStatement
)


# =====================================================================
# ФИКСТУРЫ
# =====================================================================

@pytest.fixture
def lexer():
    return Analizer()


def parse_code(code: str) -> Program:
    """Вспомогательная функция: токенизация + парсинг"""
    analizer = Analizer()
    tokens = analizer.tokenize(code)
    parser = Parser(tokens)
    return parser.parse()


# =====================================================================
# 1. ТЕСТИРОВАНИЕ ЛЕКСИЧЕСКОГО АНАЛИЗАТОРА (Analizer)
# =====================================================================

class TestLexer:
    @pytest.mark.parametrize("source,expected_type,expected_val", [
        ("public", "MODIFIER", "public"),
        ("private", "MODIFIER", "private"),
        ("static", "MODIFIER", "static"),
        ("int", "TYPE", "int"),
        ("boolean", "TYPE", "boolean"),
        ("String", "TYPE", "String"),
        ("while", "KEYWORD", "while"),
        ("for", "KEYWORD", "for"),
        ("if", "KEYWORD", "if"),
        ("else", "KEYWORD", "else"),
        ("const", "KEYWORD", "const"),
        ("myVar_123", "IDENTIFIER", "myVar_123"),
        ("123", "NUMBER", "123"),
        ("3.1415", "NUMBER", "3.1415"),
        ("1e-5", "NUMBER", "1e-5"),
        ("2.5E+10", "NUMBER", "2.5E+10"),
        ('"Hello, World!"', "STRING_LITERAL", '"Hello, World!"'),
        ('"Escaped \\" quote"', "STRING_LITERAL", '"Escaped \\" quote"'),
        ("'a'", "CHAR_LITERAL", "'a'"),
        ("'\\n'", "CHAR_LITERAL", "'\\n'"),
        ("+", "OPERATOR", "+"),
        ("==", "OPERATOR", "=="),
        ("!=", "OPERATOR", "!="),
        ("&&", "OPERATOR", "&&"),
        ("||", "OPERATOR", "||"),
        (";", "DELIMITER", ";"),
        ("{", "DELIMITER", "{"),
        ("}", "DELIMITER", "}"),
    ])
    def test_single_tokens(self, lexer, source, expected_type, expected_val):
        tokens = lexer.tokenize(source)
        assert len(tokens) == 1
        assert tokens[0] == (expected_type, expected_val)

    def test_comments_removal(self, lexer):
        code = """
        // Однострочный комментарий
        int x = 5; /* Многострочный
        комментарий */
        // Еще один комментарий
        x = x + 1;
        """
        tokens = lexer.tokenize(code)
        # Ожидаем только токены без комментариев
        values = [t[1] for t in tokens]
        assert "//" not in "".join(values)
        assert "Многострочный" not in "".join(values)
        assert values == ["int", "x", "=", "5", ";", "x", "=", "x", "+", "1", ";"]

    def test_whitespace_handling(self, lexer):
        code = "   int   \t\n  a   =   10  ;  \n "
        tokens = lexer.tokenize(code)
        assert [t[1] for t in tokens] == ["int", "a", "=", "10", ";"]

    def test_illegal_character(self, lexer):
        code = "int a = @;"
        with pytest.raises(SyntaxError, match="Illegal character '@'"):
            lexer.tokenize(code)


# =====================================================================
# 2. ПОЗИТИВНОЕ ТЕСТИРОВАНИЕ СИНТАКСИСА И AST (Parser)
# =====================================================================

class TestParserValid:
    def test_package_and_imports(self):
        code = """
        package com.example.project;
        import java.util.Scanner;
        import java.lang.Math;
        """
        ast = parse_code(code)
        assert len(ast.statements) == 3
        assert isinstance(ast.statements[0], PackageDeclaration)
        assert ast.statements[0].name == "com.example.project"
        assert isinstance(ast.statements[1], ImportDeclaration)
        assert ast.statements[1].path == "java.util.Scanner"
        assert isinstance(ast.statements[2], ImportDeclaration)
        assert ast.statements[2].path == "java.lang.Math"

    def test_variable_declarations(self):
        code = """
        int a;
        double b = 3.14;
        String s = "hello";
        const int MAX = 100;
        """
        ast = parse_code(code)
        assert len(ast.statements) == 4

        # int a;
        assert isinstance(ast.statements[0], VariableDeclaration)
        assert ast.statements[0].var_type == "int"
        assert ast.statements[0].name == "a"
        assert ast.statements[0].value is None

        # double b = 3.14;
        assert isinstance(ast.statements[1], VariableDeclaration)
        assert ast.statements[1].var_type == "double"
        assert ast.statements[1].name == "b"
        assert isinstance(ast.statements[1].value, NumberLiteral)

        # const int MAX = 100;
        assert isinstance(ast.statements[3], ConstantDeclaration)
        assert ast.statements[3].var_type == "int"
        assert ast.statements[3].name == "MAX"
        assert isinstance(ast.statements[3].value, NumberLiteral)

    def test_assignment_and_method_call(self):
        code = """
        x = 42;
        System.out.println(x);
        obj.doSomething();
        """
        ast = parse_code(code)
        assert len(ast.statements) == 3

        assert isinstance(ast.statements[0], Assignment)
        assert ast.statements[0].target == "x"

        assert isinstance(ast.statements[1], MethodCall)
        assert ast.statements[1].target == "System.out.println"
        assert len(ast.statements[1].args) == 1

        assert isinstance(ast.statements[2], MethodCall)
        assert ast.statements[2].target == "obj.doSomething"
        assert len(ast.statements[2].args) == 0

    def test_while_loop(self):
        code = """
        while (count > 0) {
            count = count - 1;
        }
        """
        ast = parse_code(code)
        stmt = ast.statements[0]
        assert isinstance(stmt, WhileStatement)
        assert isinstance(stmt.condition, BinaryOperation)
        assert stmt.condition.operator == ">"
        assert len(stmt.body.statements) == 1

    def test_do_while_loop(self):
        code = """
        do {
            x = x + 1;
        } while (x < 10);
        """
        ast = parse_code(code)
        stmt = ast.statements[0]
        assert isinstance(stmt, DoWhileStatement)
        assert isinstance(stmt.condition, BinaryOperation)
        assert stmt.condition.operator == "<"
        assert len(stmt.body.statements) == 1

    def test_for_loop(self):
        code = """
        for (int i = 0; i < 5; i = i + 1) {
            System.out.println(i);
        }
        """
        ast = parse_code(code)
        stmt = ast.statements[0]
        assert isinstance(stmt, ForStatement)
        assert isinstance(stmt.init, VariableDeclaration)
        assert stmt.init.name == "i"
        assert isinstance(stmt.condition, BinaryOperation)
        assert isinstance(stmt.update, Assignment)
        assert len(stmt.body.statements) == 1

    def test_if_else(self):
        code = """
        if (x == 0) {
            return 0;
        } else {
            return 1;
        }
        """
        ast = parse_code(code)
        stmt = ast.statements[0]
        assert isinstance(stmt, IfStatement)
        assert isinstance(stmt.condition, BinaryOperation)
        assert isinstance(stmt.then_branch, Block)
        assert isinstance(stmt.else_branch, Block)

    def test_nested_blocks(self):
        code = """
        {
            int inside = 1;
            {
                inside = 2;
            }
        }
        """
        ast = parse_code(code)
        assert len(ast.statements) == 1
        outer_block = ast.statements[0]
        assert isinstance(outer_block, Block)
        assert len(outer_block.statements) == 2
        assert isinstance(outer_block.statements[1], Block)


# =====================================================================
# 3. НЕГАТИВНОЕ ТЕСТИРОВАНИЕ: ПРОВЕРКА ОШИБОК СИНТАКСИСА (Parser)
# =====================================================================

class TestParserErrors:
    def test_unexpected_eof(self):
        code = "public class Main {"
        with pytest.raises(SyntaxError, match="Неожиданный конец файла"):
            parse_code(code)

    def test_missing_semicolon(self):
        code = "int x = 5"
        with pytest.raises(SyntaxError, match="Ожидалось значение ';'"):
            parse_code(code)

    def test_invalid_start_of_statement(self):
        code = "+ 123;"
        with pytest.raises(SyntaxError, match="Неизвестное начало выражения"):
            parse_code(code)

    def test_invalid_primary_expression(self):
        code = "int x = class;"
        with pytest.raises(SyntaxError, match="Ожидалось число, строка или идентификатор"):
            parse_code(code)

    def test_invalid_package_syntax(self):
        code = "package ;"
        with pytest.raises(SyntaxError, match="Ожидался тип токена IDENTIFIER"):
            parse_code(code)

    def test_broken_while_condition(self):
        code = "while x > 0) { }"
        with pytest.raises(SyntaxError, match="Ожидалось значение '\\('"):
            parse_code(code)

    def test_missing_while_in_do_while(self):
        code = "do { x = 1; } (x > 0);"
        with pytest.raises(SyntaxError, match="Ожидалось значение 'while'"):
            parse_code(code)


# =====================================================================
# 4. ИНТЕГРАЦИОННЫЕ ТЕСТЫ (ПОЛНЫЕ ПРОГРАММЫ)
# =====================================================================

class TestEndToEnd:
    def test_coursework_sample_program(self):
        """Тест программы из отчета курсового проекта (стр. 32)"""
        code = """
        public class Main {
            public static void main(String[] args) {
                int x = 5;
                while (x > 0) {
                    System.out.println(x);
                    x = x - 1;
                }
            }
        }
        """
        ast = parse_code(code)
        assert len(ast.statements) == 1
        cls = ast.statements[0]
        assert isinstance(cls, ClassDeclaration)
        assert cls.name == "Main"
        assert cls.modifiers == ["public"]

        # Метод main
        assert len(cls.body) == 1
        method = cls.body[0]
        assert isinstance(method, MethodDeclaration)
        assert method.name == "main"
        assert method.return_type == "void"
        assert method.modifiers == ["public", "static"]

        # Внутри main
        body = method.body.statements
        assert len(body) == 2
        assert isinstance(body[0], VariableDeclaration)
        assert isinstance(body[1], WhileStatement)

    def test_multiple_methods_and_complex_flow(self):
        code = """
        class MathUtils {
            public int calculate(int a) {
                int result = 0;
                for (int i = 0; i < a; i = i + 1) {
                    if (i == 2) {
                        result = result + 10;
                    }
                }
                return result;
            }
        }
        """
        ast = parse_code(code)
        assert len(ast.statements) == 1
        cls = ast.statements[0]
        assert cls.name == "MathUtils"
        method = cls.body[0]
        assert method.name == "calculate"
        assert method.return_type == "int"
        assert len(method.body.statements) == 3  # result decl, for loop, return
        assert isinstance(method.body.statements[2], ReturnStatement)