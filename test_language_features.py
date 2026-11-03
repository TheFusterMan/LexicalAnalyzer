import io
import re
import shutil
import subprocess
import sys
from contextlib import redirect_stdout

import pytest

from analizer import Analizer
from ast_structures import (
    ArrayAccess, ArrayCreation, ArrayInitializer, Assignment, BinaryOperation,
    BooleanLiteral, BreakStatement, ExpressionStatement, MemberAccess,
    MethodCall, Parameter, SwitchStatement, UnaryOperation,
)
from generator import Generator
from parser import Parser


def parse(code):
    return Parser(Analizer().tokenize(code)).parse()


@pytest.mark.parametrize('expression,operator,side,child_operator', [
    ('2 + 2 * 2', '+', 'right', '*'),
    ('(2 + 2) * 2', '*', 'left', '+'),
    ('10 - 3 - 2', '-', 'left', '-'),
    ('a || b && c', '||', 'right', '&&'),
    ('a & b == c', '&', 'right', '=='),
    ('a << b + c', '<<', 'right', '+'),
    ('a | b ^ c & d', '|', 'right', '^'),
    ('a < b == c > d', '==', 'left', '<'),
    ('a + b >>> c', '>>>', 'left', '+'),
])
def test_expression_precedence(expression, operator, side, child_operator):
    value = parse(f'int result = {expression};').statements[0].value
    assert isinstance(value, BinaryOperation)
    assert value.operator == operator
    child = getattr(value, side)
    assert isinstance(child, BinaryOperation)
    assert child.operator == child_operator


def test_prefix_and_postfix_updates_and_for_header():
    statements = parse('i++; i--; ++i; --i; for (i = 0; i < 3; i++) a[i]--;').statements
    for statement, operator, postfix in zip(statements, ['++', '--', '++', '--'], [True, True, False, False]):
        assert isinstance(statement, ExpressionStatement)
        assert isinstance(statement.expression, UnaryOperation)
        assert statement.expression.operator == operator
        assert statement.expression.postfix is postfix
    assert statements[4].update.expression.postfix is True
    assert isinstance(statements[4].body.expression.operand, ArrayAccess)


def test_switch_ast_fallthrough_default_and_nested_switch():
    statement = parse('''
        switch (x + 1) {
            case 1:
            case 2: x++; break;
            default: switch (y) { case 0: y--; break; }
            case 3:
        }
    ''').statements[0]
    assert isinstance(statement, SwitchStatement)
    assert isinstance(statement.expression, BinaryOperation)
    assert len(statement.cases) == 4
    assert statement.cases[0].statements == []
    assert isinstance(statement.cases[1].statements[1], BreakStatement)
    assert statement.cases[2].value is None
    assert isinstance(statement.cases[2].statements[0], SwitchStatement)
    assert statement.cases[-1].statements == []


def test_array_declarations_access_initializers_and_parameters():
    statements = parse('''
        int[] values = new int[2 + 3];
        int table[][] = {{1, 2}, {3},};
        values[1 + 1] = values[0] * 2;
        values[0]++;
        int count = values.length;
        int[] copy(int input[], boolean enabled) { return input; }
    ''').statements
    assert statements[0].var_type == 'int[]'
    assert isinstance(statements[0].value, ArrayCreation)
    assert statements[1].var_type == 'int[][]'
    assert isinstance(statements[1].value, ArrayInitializer)
    assert isinstance(statements[2], Assignment)
    assert isinstance(statements[2].target, ArrayAccess)
    assert isinstance(statements[4].value, MemberAccess)
    assert statements[5].return_type == 'int[]'
    assert statements[5].params == [Parameter('int[]', 'input'), Parameter('boolean', 'enabled')]


def test_calls_are_expressions_and_accept_multiple_arguments():
    value = parse('int x = sum(1 + 2, values[0]) * 3;').statements[0].value
    assert isinstance(value.left, MethodCall)
    assert value.left.target == 'sum'
    assert len(value.left.args) == 2


def test_boolean_literals_and_unary_operations():
    value = parse('boolean b = !true || false;').statements[0].value
    assert value.left.operator == '!'
    assert isinstance(value.left.operand, BooleanLiteral)
    assert isinstance(value.right, BooleanLiteral)


@pytest.mark.parametrize('source,message', [
    ('break;', 'break допустим'),
    ('continue;', 'continue допустим'),
    ('switch (x) { case 1: continue; }', 'continue допустим'),
    ('switch (x) { default: default: }', 'Повторный default'),
    ('switch (x) { case 1: case 1: }', 'Повторная метка case'),
    ('switch (x) { x++; }', 'ожидалось case или default'),
    ('switch (x) { case 1 x++; }', 'Ожидался тип токена DELIMITER'),
    ('switch (x) { case 1:', 'Неожиданный конец файла'),
    ('++1;', 'Левая часть'),
    ('(i + 1)++;', 'Левая часть'),
    ('f()++;', 'Левая часть'),
    ('a.length++;', 'Левая часть'),
    ('a.length = 1;', 'Левая часть'),
    ('i + 1;', 'Ожидалось присваивание'),
    ('int[] a = new int[];', 'размер или инициализатор'),
    ('int[] a = new int[2] {1, 2};', 'одновременно'),
    ('int[][] a = new int[][2];', 'после пустого измерения'),
    ('int[] a = new int;', 'ожидались измерения'),
    ('int[] a = new void[2];', 'тип void'),
    ('void[] a;', 'void допустим'),
    ('int a = {1};', 'только для массива'),
    ('int[] a = new int[2;', "Ожидалось значение ']'"),
    ('int[] a = {1,', 'Неожиданный конец файла'),
])
def test_invalid_feature_syntax(source, message):
    with pytest.raises(SyntaxError, match=re.escape(message)):
        parse(source)


def test_lexer_keeps_comment_markers_in_array_strings():
    tokens = Analizer().tokenize('String[] urls = {"https://example.org", "/* text */"}; // comment')
    assert [value for kind, value in tokens if kind == 'STRING_LITERAL'] == [
        '"https://example.org"', '"/* text */"',
    ]
    assert Analizer().tokenize(': ~') == [('DELIMITER', ':'), ('OPERATOR', '~')]
    with pytest.raises(SyntaxError, match='Незакрытый многострочный комментарий'):
        Analizer().tokenize('int x; /* missing end')


def test_ast_printer_includes_new_nodes():
    ast = parse('''
        void demo(int[] input) {
            int[] a = new int[]{1, 2};
            boolean flag = true;
            for (int i = 0; i < a.length; i++) {
                switch (a[i]) { case 1: a[i]++; break; default: continue; }
            }
        }
    ''')
    output = io.StringIO()
    with redirect_stdout(output):
        Parser.print_ast(ast)
    for name in ['Parameter', 'ArrayCreation', 'ArrayInitializer', 'BooleanLiteral',
                 'SwitchStatement', 'SwitchCase', 'ArrayAccess', 'UnaryOperation',
                 'ExpressionStatement', 'BreakStatement', 'ContinueStatement']:
        assert name in output.getvalue()


def test_generator_rejects_initializer_with_excess_rank():
    with pytest.raises(SyntaxError, match='Глубина инициализатора'):
        Generator().generate(parse('int[] a = {{1}};'))


PROGRAMS = [
    pytest.param('''
        System.out.println(2 + 2 * 2);
        System.out.println((2 + 2) * 2);
        System.out.println(10 - 3 - 2);
        System.out.println(20 / (2 + 3));
        System.out.println(2 + 3 * 4 > 10 && !false);
        System.out.println(1 | 2 ^ 3 & 4);
        System.out.println(1 << 2 + 1);
        System.out.println(-2 * (3 + 1));
        System.out.println(~0);
    ''', '6\n8\n5\n4\ntrue\n3\n8\n-8\n-1\n', '', id='precedence-and-parentheses'),
    pytest.param('''
        int i = 2;
        i++; i--; ++i; --i;
        System.out.println(i++);
        System.out.println(++i);
        System.out.println(i--);
        System.out.println(--i);
        int old = i++;
        System.out.println(old);
        System.out.println(i);
        for (int j = 0; j < 3; j++) System.out.println(j);
        while (i > 1) i--;
        do --i; while (i > 0);
        System.out.println(i);
    ''', '2\n4\n4\n2\n2\n3\n0\n1\n2\n0\n', '', id='standalone-and-expression-updates'),
    pytest.param('''
        String word = "two";
        switch (word) {
            case "one": System.out.println(1); break;
            case "two": System.out.println(2);
            default: System.out.println(3);
        }
        switch ("two") { case "two": System.out.println(4); break; }
        switch (word) { default: System.out.println(5); }
        switch ("a") { case "b": System.out.println(99); }
        int java_switch_value_0 = 10;
        switch (java_switch_value_0) { case 10: System.out.println(6); break; }
    ''', '2\n3\n4\n5\n6\n', '', id='string-switch-and-generated-name-collisions'),
    pytest.param('''
        int x = 2;
        switch (x++) {
            case 1: System.out.println(1);
            case 2: System.out.println(2);
            default: System.out.println(9);
            case 3: System.out.println(3); break;
        }
        System.out.println(x);
        switch (100) { case 1: break; default: System.out.println(7); case 5: System.out.println(5); }
        switch (5) { default: System.out.println(99); case 5: System.out.println(8); }
        switch (0) { case 0: case 1: }
        switch (0) {}
    ''', '2\n9\n3\n3\n7\n5\n8\n', '', id='switch-fallthrough-and-default-position'),
    pytest.param('''
        for (int i = 0; i < 4; i++) {
            switch (i) {
                case 0: continue;
                case 1:
                    switch (i + 1) { case 2: System.out.println(20); break; default: break; }
                    break;
                default: System.out.println(i);
            }
            System.out.println(10);
        }
    ''', '20\n10\n2\n10\n3\n10\n', '', id='nested-switch-break-and-continue'),
    pytest.param('''
        switch (1) {
            case 0: int value = 10; System.out.println(value); break;
            case 1: value = 20; System.out.println(value); break;
            default: break;
        }
        switch (2) {
            case 1: final int KEY = 2;
            case KEY: System.out.println(30); break;
        }
        final int BASE = 2;
        switch (3) {
            case 0: final int KEY = BASE + 1;
            case KEY: System.out.println(35); break;
        }
        char letter = 'b';
        switch (letter) { case 'a': break; case 'b': System.out.println(40); break; default: break; }
        switch (1) { case 1: int[] a = {9}; System.out.println(a[0]); break; case 2: break; }
    ''', '20\n30\n35\n40\n9\n', '', id='switch-shared-scope-and-char-labels'),
    pytest.param('''
        int[] a = new int[3];
        System.out.println(a[1]);
        a[0] = 2 + 2 * 2;
        a[0]++;
        ++a[1];
        a[1] += 3;
        int[] alias = a;
        alias[2] = 9;
        System.out.println(a[0]);
        System.out.println(a[1]);
        System.out.println(a[2]);
        System.out.println(a.length);
        System.out.println(a == alias);
        int[] other = new int[]{7, 4, 9,};
        System.out.println(a == other);
        int empty[] = {};
        System.out.println(empty.length);
        int[] another = new int[]{};
        System.out.println(another.length);
    ''', '0\n7\n4\n9\n3\ntrue\nfalse\n0\n0\n', '', id='arrays-initialization-indexing-and-aliases'),
    pytest.param('''
        int[] a = make(3);
        mutate(a, 5);
        System.out.println(a[1]);
        System.out.println(first(a) + 1);
        System.out.println(make(2).length);
        System.out.println(make(2)[1]);
    ''', '15\n1\n2\n10\n', '''
        static int[] make(int size) { int[] a = new int[size]; a[1] = 10; return a; }
        static void mutate(int values[], int amount) { values[1] += amount; }
        static int first(int[] values) { return values[0]; }
    ''', id='array-method-parameters-return-values-and-prototypes'),
    pytest.param('''
        int[][] a = new int[2][3];
        a[0][0] = 7;
        System.out.println(a[1][0]);
        System.out.println(a[0][0]);
        System.out.println(a.length);
        System.out.println(a[1].length);
        int[][] jagged = new int[2][];
        jagged[0] = new int[]{1, 2};
        jagged[1] = new int[0];
        System.out.println(jagged[0][1]);
        System.out.println(jagged[1].length);
        int[][] literal = {{1}, {2, 3}, {}};
        System.out.println(literal[1][1]);
        System.out.println(literal[2].length);
        int[][][] cube = new int[2][2][2];
        cube[1][1][1] = 8;
        System.out.println(cube[0][1][1]);
        System.out.println(cube[1][1][1]);
    ''', '0\n7\n2\n3\n2\n0\n3\n0\n0\n8\n', '', id='multidimensional-and-jagged-arrays'),
    pytest.param('''
        int size = 2;
        int[][] a = new int[size++][size++];
        System.out.println(a.length);
        System.out.println(a[0].length);
        System.out.println(size);
    ''', '2\n3\n4\n', '', id='array-dimensions-evaluated-left-to-right'),
    pytest.param('''
        boolean[] flags = new boolean[2];
        System.out.println(flags[0]);
        flags[0] = true;
        System.out.println(flags[0]);
        boolean[][] grid = new boolean[2][2];
        grid[0][0] = true;
        System.out.println(grid[0][0]);
        System.out.println(grid[1][0]);
        char[] letters = {'x', 'y'};
        System.out.println(letters[1]);
        String[] text = {"https://example.org", "/* literal */"};
        System.out.println(text[0]);
        System.out.println(text[1]);
        final int[] fixed = {1};
        fixed[0]++;
        System.out.println(fixed[0]);
    ''', 'false\ntrue\ntrue\nfalse\ny\nhttps://example.org\n/* literal */\n2\n', '', id='boolean-char-string-and-final-arrays'),
    pytest.param('''
        int x = -1;
        System.out.println(x >>> 1);
        System.out.println(8 >>> 1 + 1);
        x >>>= 31;
        System.out.println(x);
        System.out.println(-1 >>> 32);
        int[] a = {-1, -1};
        int index = 0;
        a[index++] >>>= 31;
        System.out.println(a[0]);
        System.out.println(index);
    ''', '2147483647\n2\n1\n-1\n1\n1\n', '', id='unsigned-shift-precedence-and-assignment'),
    pytest.param('''
        if (true) if (false) System.out.println(1); else System.out.println(2);
        System.out.println(3 < 4);
        System.out.println(3 == 4);
        System.out.println();
        return;
    ''', '2\ntrue\nfalse\n\n', '', id='single-statement-bodies-and-output-grouping'),
]


@pytest.fixture(scope='session')
def cpp_compiler():
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('Для проверки сгенерированного C++ нужен g++ или clang++')
    return compiler


def compile_cpp(cpp_compiler, tmp_path, source):
    cpp_file = tmp_path / 'program.cpp'
    executable = tmp_path / ('program.exe' if sys.platform == 'win32' else 'program')
    cpp_file.write_text(source, encoding='utf-8')
    compilation = subprocess.run(
        [cpp_compiler, '-std=c++17', '-Wall', '-Wextra', '-pedantic', str(cpp_file), '-o', str(executable)],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30,
    )
    assert compilation.returncode == 0, compilation.stderr + '\n' + source
    return executable


@pytest.mark.parametrize('body,expected,methods', PROGRAMS)
def test_generated_cpp_executes(cpp_compiler, tmp_path, body, expected, methods):
    java = f'class Main {{ public static void main(String[] args) {{ {body} }} {methods} }}'
    source = Generator().generate(parse(java))
    executable = compile_cpp(cpp_compiler, tmp_path, source)
    result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected


def test_main_array_arguments(cpp_compiler, tmp_path):
    source = Generator().generate(parse('''
        class Main {
            public static void main(String[] args) {
                System.out.println(args.length);
                System.out.println(args[0]);
                System.out.println(args[1]);
            }
        }
    '''))
    executable = compile_cpp(cpp_compiler, tmp_path, source)
    result = subprocess.run([str(executable), 'one', 'two'], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert result.stdout == '2\none\ntwo\n'
