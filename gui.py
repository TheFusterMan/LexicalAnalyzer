import io
import sys
from contextlib import redirect_stdout
import customtkinter as ctk
from tkinter import filedialog, messagebox

from analizer import Analizer
from parser import Parser
from generator import Generator

DEFAULT_JAVA_CODE = """public class Main {
    public static void main(String[] args) {
        int x = 5;
        while (x > 0) {
            System.out.println(x);
            x = x - 1;
        }
    }
}"""


class TranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Транслятор Java -> C++ | Курсовой проект")
        self.geometry("1100, 750")
        self.minsize(900, 600)

        # Настройка цветовой палитры (Dark / Light)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.init_ui()

    def init_ui(self):
        # 1. Верхняя панель инструментов (Toolbar)
        self.top_frame = ctk.CTkFrame(self, corner_radius=10)
        self.top_frame.pack(fill="x", padx=15, pady=(15, 10))

        self.btn_open = ctk.CTkButton(
            self.top_frame, text="📂 Открыть .java", command=self.load_file, width=130
        )
        self.btn_open.pack(side="left", padx=10, pady=10)

        self.btn_sample = ctk.CTkButton(
            self.top_frame, text="✨ Пример", command=self.load_sample, width=100, fg_color="gray"
        )
        self.btn_sample.pack(side="left", padx=5, pady=10)

        self.btn_clear = ctk.CTkButton(
            self.top_frame, text="🗑 Очистить", command=self.clear_all, width=100, fg_color="#c0392b", hover_color="#962d22"
        )
        self.btn_clear.pack(side="left", padx=5, pady=10)

        # Главная кнопка трансляции
        self.btn_translate = ctk.CTkButton(
            self.top_frame,
            text="▶ Транслировать в C++",
            command=self.translate_code,
            width=200,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#27ae60",
            hover_color="#1e8449"
        )
        self.btn_translate.pack(side="left", padx=20, pady=10)

        # Переключатель темы
        self.theme_switch = ctk.CTkSwitch(
            self.top_frame, text="Темная тема", command=self.toggle_theme
        )
        self.theme_switch.select()
        self.theme_switch.pack(side="right", padx=15, pady=10)

        # 2. Центральная область редакторов кода (Split View)
        self.editors_frame = ctk.CTkFrame(self)
        self.editors_frame.pack(fill="both", expand=True, padx=15, pady=5)
        self.editors_frame.grid_columnconfigure((0, 1), weight=1)
        self.editors_frame.grid_rowconfigure(1, weight=1)

        # Левая колонка: Входной Java код
        self.lbl_java = ctk.CTkLabel(
            self.editors_frame, text="Исходный код (Java)", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_java.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.txt_java = ctk.CTkTextbox(
            self.editors_frame, font=ctk.CTkFont(family="Consolas", size=13), wrap="none"
        )
        self.txt_java.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Правая колонка: Выходной C++ код
        right_header_frame = ctk.CTkFrame(self.editors_frame, fg_color="transparent")
        right_header_frame.grid(row=0, column=1, padx=5, pady=(5, 0), sticky="ew")

        self.lbl_cpp = ctk.CTkLabel(
            right_header_frame, text="Целевой код (C++)", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_cpp.pack(side="left")

        self.btn_copy = ctk.CTkButton(
            right_header_frame, text="📋 Копировать", command=self.copy_cpp, width=90, height=24
        )
        self.btn_copy.pack(side="right")

        self.txt_cpp = ctk.CTkTextbox(
            self.editors_frame, font=ctk.CTkFont(family="Consolas", size=13), wrap="none"
        )
        self.txt_cpp.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        # 3. Нижняя панель: Вкладки инспектора (Лог/Ошибки, Токены, AST)
        self.tabview = ctk.CTkTabview(self, height=180)
        self.tabview.pack(fill="x", padx=15, pady=(5, 15))

        self.tab_status = self.tabview.add("Диагностика и ошибки")
        self.tab_tokens = self.tabview.add("Таблица лексем (Токены)")
        self.tab_ast = self.tabview.add("Дерево разбора (AST)")

        # Виджеты для вкладок
        self.txt_status = ctk.CTkTextbox(
            self.tab_status, font=ctk.CTkFont(family="Consolas", size=12), wrap="word"
        )
        self.txt_status.pack(fill="both", expand=True)

        self.txt_tokens = ctk.CTkTextbox(
            self.tab_tokens, font=ctk.CTkFont(family="Consolas", size=12), wrap="none"
        )
        self.txt_tokens.pack(fill="both", expand=True)

        self.txt_ast = ctk.CTkTextbox(
            self.tab_ast, font=ctk.CTkFont(family="Consolas", size=12), wrap="none"
        )
        self.txt_ast.pack(fill="both", expand=True)

        # Загружаем стартовый пример
        self.load_sample()

    # ==================== Функционал и логика ====================

    def translate_code(self):
        """Основной пайплайн: Лексер -> Парсер -> Генератор"""
        java_code = self.txt_java.get("1.0", "end-1c").strip()
        if not java_code:
            messagebox.showwarning("Внимание", "Поле ввода пусто. Введите код на Java.")
            return

        self.txt_cpp.delete("1.0", "end")
        self.txt_status.delete("1.0", "end")
        self.txt_tokens.delete("1.0", "end")
        self.txt_ast.delete("1.0", "end")

        try:
            # 1. Лексический анализ
            analizer = Analizer()
            tokens = analizer.tokenize(java_code)

            # Вывод токенов во вкладку
            tokens_str = "\n".join([f"[{token[0]:<15}] -> '{token[1]}'" for token in tokens])
            self.txt_tokens.insert("1.0", tokens_str)

            # 2. Синтаксический анализ
            parser = Parser(tokens)
            ast = parser.parse()

            ast_buffer = io.StringIO()
            with redirect_stdout(ast_buffer):
                Parser.print_ast(ast)
            self.txt_ast.insert("1.0", ast_buffer.getvalue())

            # 3. Генерация целевого C++ кода
            generator = Generator()
            cpp_code = generator.generate(ast)
            self.txt_cpp.insert("1.0", cpp_code)

            self.txt_status.insert(
                "1.0",
                "✔ Трансляция успешно выполнена!\n"
                f"- Распознано токенов: {len(tokens)}\n"
                "- Синтаксическое дерево (AST) построено корректно.\n"
                "- Целевой код C++ успешно сгенерирован."
            )
            self.tabview.set("Диагностика и ошибки")

        except SyntaxError as e:
            err_msg = f"❌ ОШИБКА АНАЛИЗА:\n{str(e)}"
            self.txt_status.insert("1.0", err_msg)
            self.tabview.set("Диагностика и ошибки")
        except Exception as e:
            err_msg = f"❌ НЕПРЕДВИДЕННАЯ ОШИБКА:\n{str(e)}"
            self.txt_status.insert("1.0", err_msg)
            self.tabview.set("Диагностика и ошибки")

    def load_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Java files", "*.java"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.txt_java.delete("1.0", "end")
                self.txt_java.insert("1.0", content)

    def load_sample(self):
        self.txt_java.delete("1.0", "end")
        self.txt_java.insert("1.0", DEFAULT_JAVA_CODE)

    def clear_all(self):
        self.txt_java.delete("1.0", "end")
        self.txt_cpp.delete("1.0", "end")
        self.txt_status.delete("1.0", "end")
        self.txt_tokens.delete("1.0", "end")
        self.txt_ast.delete("1.0", "end")

    def copy_cpp(self):
        cpp_code = self.txt_cpp.get("1.0", "end-1c")
        if cpp_code:
            self.clipboard_clear()
            self.clipboard_append(cpp_code)
            messagebox.showinfo("Успех", "C++ код скопирован в буфер обмена!")

    def toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")


if __name__ == "__main__":
    app = TranslatorApp()
    app.mainloop()