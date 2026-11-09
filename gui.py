import io
import sys
from datetime import datetime
from contextlib import redirect_stdout
import customtkinter as ctk
from tkinter import filedialog, messagebox

from analizer import Analizer
from parser import Parser
from generator import Generator
from semantic_analyzer import SemanticAnalyzer, SemanticError

class ModernTranspilerStudio(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Java to C++ Transpiler Studio | IMCT FEFU")
        self.geometry("1240, 820")
        self.minsize(1000, 700)

        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        self.setup_grid_layout()
        self.build_sidebar()
        self.build_workspace()

    def setup_grid_layout(self):
        # 0 колонка: Сайдбар управления, 1 колонка: Рабочая область редакторов
        self.grid_columnconfigure(0, weight=0, minsize=240)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    # =========================================================================
    # 1. ЛЕВЫЙ САЙДБАР (СВЕТЛАЯ ТЕМА)
    # =========================================================================
    def build_sidebar(self):
        # Светлый фон панели
        self.sidebar_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#F1F5F9")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        # Тёмный текст заголовка
        self.lbl_brand = ctk.CTkLabel(
            self.sidebar_frame,
            text="⚡ J2CPP Studio",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#0F172A"
        )
        self.lbl_brand.grid(row=0, column=0, padx=20, pady=(20, 20), sticky="w")

        # Основная кнопка
        self.btn_run = ctk.CTkButton(
            self.sidebar_frame,
            text="▶  Транслировать",
            command=self.execute_pipeline,
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4F46E5",
            hover_color="#4338CA",
            text_color="#FFFFFF"
        )
        self.btn_run.grid(row=2, column=0, padx=16, pady=(0, 14), sticky="ew")

        # Светлые кнопки-карточки
        self.btn_load = ctk.CTkButton(
            self.sidebar_frame, text="📂  Открыть файл...", command=self.open_file_dialog,
            fg_color="#FFFFFF", hover_color="#E2E8F0", text_color="#0F172A",
            border_width=1, border_color="#CBD5E1", height=34, corner_radius=6
        )
        self.btn_load.grid(row=3, column=0, padx=16, pady=4, sticky="ew")

        self.btn_copy = ctk.CTkButton(
            self.sidebar_frame, text="📋  Скопировать C++", command=self.copy_to_clipboard,
            fg_color="#FFFFFF", hover_color="#E2E8F0", text_color="#0F172A",
            border_width=1, border_color="#CBD5E1", height=34, corner_radius=6
        )
        self.btn_copy.grid(row=4, column=0, padx=16, pady=4, sticky="ew")

        self.btn_clear = ctk.CTkButton(
            self.sidebar_frame, text="🗑  Очистить всё", command=self.reset_all_views,
            fg_color="#FEE2E2", hover_color="#FECACA", text_color="#B91C1C",
            border_width=1, border_color="#FCA5A5", height=34, corner_radius=6
        )
        self.btn_clear.grid(row=5, column=0, padx=16, pady=4, sticky="ew")

        # Белая карточка метрик с рамкой
        self.metrics_card = ctk.CTkFrame(
            self.sidebar_frame, fg_color="#FFFFFF", corner_radius=8,
            border_width=1, border_color="#CBD5E1"
        )
        self.metrics_card.grid(row=6, column=0, padx=16, pady=20, sticky="ew")

        ctk.CTkLabel(
            self.metrics_card, text="МЕТРИКИ РАЗБОРА",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748B"
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.lbl_lines_metric = ctk.CTkLabel(
            self.metrics_card, text="Строк исходника: 0",
            font=ctk.CTkFont(size=12), text_color="#0F172A"
        )
        self.lbl_lines_metric.pack(anchor="w", padx=12, pady=1)

        self.lbl_tokens_metric = ctk.CTkLabel(
            self.metrics_card, text="Токенов: 0",
            font=ctk.CTkFont(size=12), text_color="#0F172A"
        )
        self.lbl_tokens_metric.pack(anchor="w", padx=12, pady=1)

        self.lbl_status_badge = ctk.CTkLabel(
            self.metrics_card, text="● Статус: Готов",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#059669"
        )
        self.lbl_status_badge.pack(anchor="w", padx=12, pady=(4, 10))

    # =========================================================================
    # 2. РАБОЧАЯ ОБЛАСТЬ (DUAL EDITORS + BOTTOM DOCK)
    # =========================================================================
    def build_workspace(self):
        self.workspace_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace_frame.grid(row=0, column=1, sticky="nsew", padx=14, pady=14)
        self.workspace_frame.grid_columnconfigure(0, weight=1)
        self.workspace_frame.grid_rowconfigure(0, weight=3)  # Редакторы кода
        self.workspace_frame.grid_rowconfigure(1, weight=2)  # Нижняя панель анализа

        # Контейнер для двух редакторов
        self.editors_container = ctk.CTkFrame(self.workspace_frame, fg_color="transparent")
        self.editors_container.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.editors_container.grid_columnconfigure((0, 1), weight=1)
        self.editors_container.grid_rowconfigure(1, weight=1)

        # Хедер вкладки Java
        self.hdr_java = ctk.CTkFrame(self.editors_container, height=30, fg_color="#1E293B", corner_radius=6)
        self.hdr_java.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkLabel(
            self.hdr_java, text="●  Source.java  [Java SE]",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#60A5FA"
        ).pack(side="left", padx=10)

        # Хедер вкладки C++
        self.hdr_cpp = ctk.CTkFrame(self.editors_container, height=30, fg_color="#1E293B", corner_radius=6)
        self.hdr_cpp.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        ctk.CTkLabel(
            self.hdr_cpp, text="●  Target.cpp  [C++17 Standalone]",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#34D399"
        ).pack(side="left", padx=10)

        # Текстовые поля редакторов
        self.src_editor = ctk.CTkTextbox(
            self.editors_container, font=ctk.CTkFont(family="Consolas", size=13),
            wrap="none", corner_radius=6, border_width=1, border_color="#334155"
        )
        self.src_editor.grid(row=1, column=0, padx=(0, 5), pady=(4, 0), sticky="nsew")

        self.out_editor = ctk.CTkTextbox(
            self.editors_container, font=ctk.CTkFont(family="Consolas", size=13),
            wrap="none", corner_radius=6, border_width=1, border_color="#334155"
        )
        self.out_editor.grid(row=1, column=1, padx=(5, 0), pady=(4, 0), sticky="nsew")

        # Нижний терминал инспектора (Dock)
        self.dock_panel = ctk.CTkTabview(self.workspace_frame)
        self.dock_panel.grid(row=1, column=0, sticky="nsew")

        self.tab_log = self.dock_panel.add("Терминал транслятора")
        self.tab_ast = self.dock_panel.add("Дерево AST")
        self.tab_lex = self.dock_panel.add("Таблица лексем")

        self.txt_log = ctk.CTkTextbox(self.tab_log, font=ctk.CTkFont(family="Consolas", size=12), wrap="word")
        self.txt_log.pack(fill="both", expand=True)

        self.txt_ast = ctk.CTkTextbox(self.tab_ast, font=ctk.CTkFont(family="Consolas", size=12), wrap="none")
        self.txt_ast.pack(fill="both", expand=True)

        self.txt_lex = ctk.CTkTextbox(self.tab_lex, font=ctk.CTkFont(family="Consolas", size=12), wrap="none")
        self.txt_lex.pack(fill="both", expand=True)

    # =========================================================================
    # ЛОГИКА ТРАНСЛЯЦИИ
    # =========================================================================
    def execute_pipeline(self):
        code = self.src_editor.get("1.0", "end-1c").strip()
        if not code:
            messagebox.showwarning("Предупреждение", "Поле исходного Java-кода пусто.")
            return

        # Очистка панелей вывода
        self.out_editor.delete("1.0", "end")
        self.txt_log.delete("1.0", "end")
        self.txt_lex.delete("1.0", "end")
        self.txt_ast.delete("1.0", "end")

        self.lbl_lines_metric.configure(text=f"Строк исходника: {len(code.splitlines())}")
        now = datetime.now().strftime("%H:%M:%S")

        try:
            # 1. Лексер
            analizer = Analizer()
            tokens = analizer.tokenize(code)
            self.lbl_tokens_metric.configure(text=f"Токенов: {len(tokens)}")

            formatted_tokens = "\n".join([f"[{t[0]:<16}]  '{t[1]}'" for t in tokens])
            self.txt_lex.insert("1.0", formatted_tokens)

            # 2. Синтаксический анализ (AST)
            parser = Parser(tokens)
            ast = parser.parse()

            ast_stream = io.StringIO()
            with redirect_stdout(ast_stream):
                Parser.print_ast(ast)
            self.txt_ast.insert("1.0", ast_stream.getvalue())

            # 3. Семантическая верификация
            checker = SemanticAnalyzer()
            checker.analyze(ast)

            # 4. Кодогенерация C++
            generator = Generator()
            cpp_code = generator.generate(ast)
            self.out_editor.insert("1.0", cpp_code)

            # Обновление статуса
            self.lbl_status_badge.configure(text="● Статус: Успех", text_color="#10B981")
            self.txt_log.insert(
                "1.0",
                f"[{now}] [PIPELINE: SUCCESS] Полный цикл трансляции завершен без ошибок!\n"
                f"├─ [1/4] Лексический анализ: успешно распознано {len(tokens)} лексем.\n"
                f"├─ [2/4] Синтаксический анализ: дерево разбора (AST) сформировано.\n"
                f"├─ [3/4] Семантический анализ: типы, константы и области видимости согласованы.\n"
                f"└─ [4/4] Генерация кода: скомпилирован чистый C++17 код.\n"
            )
            self.dock_panel.set("Терминал транслятора")

        except (SyntaxError, SemanticError) as err:
            self.lbl_status_badge.configure(text="● Статус: Ошибка", text_color="#EF4444")
            self.txt_log.insert("1.0", f"[{now}] [COMPILER ERROR]:\n{str(err)}\n")
            self.dock_panel.set("Терминал транслятора")
        except Exception as err:
            self.lbl_status_badge.configure(text="● Статус: Сбой", text_color="#EF4444")
            self.txt_log.insert("1.0", f"[{now}] [SYSTEM CRITICAL]:\n{str(err)}\n")
            self.dock_panel.set("Терминал транслятора")

    def open_file_dialog(self):
        fpath = filedialog.askopenfilename(
            filetypes=[("Java files", "*.java"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if fpath:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                self.src_editor.delete("1.0", "end")
                self.src_editor.insert("1.0", content)
                self.lbl_lines_metric.configure(text=f"Строк исходника: {len(content.splitlines())}")

    def reset_all_views(self):
        self.src_editor.delete("1.0", "end")
        self.out_editor.delete("1.0", "end")
        self.txt_log.delete("1.0", "end")
        self.txt_lex.delete("1.0", "end")
        self.txt_ast.delete("1.0", "end")
        self.lbl_lines_metric.configure(text="Строк исходника: 0")
        self.lbl_tokens_metric.configure(text="Токенов: 0")
        self.lbl_status_badge.configure(text="● Статус: Очищено", text_color="#9CA3AF")

    def copy_to_clipboard(self):
        code = self.out_editor.get("1.0", "end-1c")
        if code:
            self.clipboard_clear()
            self.clipboard_append(code)
            messagebox.showinfo("Буфер обмена", "Целевой код C++ успешно скопирован!")


if __name__ == "__main__":
    app = ModernTranspilerStudio()
    app.mainloop()