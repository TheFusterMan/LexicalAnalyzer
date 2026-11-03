# test_semantic.py
import unittest
from analizer import Analizer
from parser import Parser
from semantic_analyzer import SemanticAnalyzer, SemanticError


def run_semantic_check(code: str):
    """Вспомогательная функция: прогон цепочки Лексер -> Парсер -> Семантика"""
    tokens = Analizer().tokenize(code)
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)


class TestSemanticAnalyzer(unittest.TestCase):

    # 1. Позитивный тест: корректный код
    def test_valid_program(self):
        code = """
        public class Main {
            public static void main(String[] args) {
                int x = 5;
                int y = x + 10;
                while (x > 0) {
                    x = x - 1;
                }
            }
        }
        """
        try:
            run_semantic_check(code)
        except SemanticError:
            self.fail("Семантический анализатор выдал ошибку на корректном коде!")

    # 2. Использование необъявленной переменной
    def test_undeclared_variable(self):
        code = """
        public class Main {
            public static void main(String[] args) {
                x = 10;
            }
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            run_semantic_check(code)
        self.assertIn("необъявленн", str(ctx.exception))

    # 3. Повторное объявление переменной в одной области видимости
    def test_duplicate_variable_declaration(self):
        code = """
        public class Main {
            public static void main(String[] args) {
                int a = 10;
                int a = 20;
            }
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            run_semantic_check(code)
        self.assertIn("Повторное объявление", str(ctx.exception))

    # 4. Несовместимость типов при инициализации (String в int)
    def test_type_mismatch_init(self):
        code = """
        public class Main {
            public static void main(String[] args) {
                int a = "строка";
            }
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            run_semantic_check(code)
        self.assertIn("Несовместимость типов", str(ctx.exception))

    # 5. Попытка изменения константы
    def test_reassign_constant(self):
        code = """
        public class Main {
            public static void main(String[] args) {
                const int MAX = 100;
                MAX = 200;
            }
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            run_semantic_check(code)
        self.assertIn("константам запрещено", str(ctx.exception))

    # 6. Небулево условие в цикле (число вместо boolean)
    def test_non_boolean_condition_in_while(self):
        code = """
        public class Main {
            public static void main(String[] args) {
                int x = 5;
                while (x + 1) {
                    x = x - 1;
                }
            }
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            run_semantic_check(code)
        self.assertIn("должно быть boolean", str(ctx.exception))

    # 7. Недопустимая операция над типами (вычитание из строки)
    def test_invalid_binary_operation(self):
        code = """
        public class Main {
            public static void main(String[] args) {
                int res = "тест" - 5;
            }
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            run_semantic_check(code)
        self.assertIn("недопустима для типов", str(ctx.exception))

    # 8. Изоляция областей видимости (переменная из блока {} не видна снаружи)
    def test_scope_isolation(self):
        code = """
        public class Main {
            public static void main(String[] args) {
                if (true) {
                    int innerVar = 42;
                }
                innerVar = 10;
            }
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            run_semantic_check(code)
        self.assertIn("необъявленн", str(ctx.exception))

    # 9. Void-метод пытается вернуть значение
    def test_void_method_returns_value(self):
        code = """
        public class Main {
            void doSomething() {
                return 100;
            }
        }
        """
        with self.assertRaises(SemanticError) as ctx:
            run_semantic_check(code)
        self.assertIn("типом void не может возвращать значение", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()