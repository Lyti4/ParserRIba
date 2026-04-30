import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import sys
import os
import threading
import json
from datetime import datetime
import pyperclip

# Настройка внешнего вида
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ParserLauncher:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("🐟 ParserRIba Launcher")
        self.root.geometry("900x850")
        self.root.resizable(True, True)
        
        self.shop_vars = {}
        self.is_running = False
        self.last_report_path = None
        self.process = None
        
        self.config = {
            "delay": 10,
            "visual_mode": False,
            "shops": ["Пятерочка", "Магнит", "Перекресток", "Лента", "Ашан", "Окей"]
        }
        self.load_config()
        self.setup_ui()
        
    def load_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except: pass

    def save_config(self):
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
        self.log_message("💾 Настройки сохранены", "info")

    def setup_ui(self):
        # Основной скролл-фрейм
        self.main_frame = ctk.CTkScrollableFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Заголовок
        title = ctk.CTkLabel(self.main_frame, text="🚀 Парсер цен на рыбу", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, columnspan=4, pady=(0, 20), sticky="w")
        
        # --- Секция магазинов ---
        lbl_shops = ctk.CTkLabel(self.main_frame, text="Выберите магазины:", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_shops.grid(row=1, column=0, columnspan=4, pady=(10, 10), sticky="w")
        
        shops = ["Пятерочка", "Магнит", "Перекресток", "Лента", "Ашан", "Окей"]
        for i, shop in enumerate(shops):
            var = tk.BooleanVar(value=True)
            self.shop_vars[shop] = var
            cb = ctk.CTkCheckBox(self.main_frame, text=shop, variable=var, font=ctk.CTkFont(size=14))
            row = 2 + (i // 3)
            col = i % 3
            cb.grid(row=row, column=col, padx=20, pady=10, sticky="w")
        
        # --- Секция настроек ---
        start_row = 5 # Увеличено, чтобы не наезжать
        lbl_settings = ctk.CTkLabel(self.main_frame, text="⚙️ Настройки запуска", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_settings.grid(row=start_row, column=0, columnspan=4, pady=(30, 10), sticky="w")
        
        # Задержка
        lbl_delay = ctk.CTkLabel(self.main_frame, text="Задержка (сек):", font=ctk.CTkFont(size=14))
        lbl_delay.grid(row=start_row+1, column=0, padx=20, pady=5, sticky="w")
        
        self.delay_val_label = ctk.CTkLabel(self.main_frame, text=str(self.config.get("delay", 10)), font=ctk.CTkFont(size=14, weight="bold"), text_color="#4CAF50")
        self.delay_val_label.grid(row=start_row+1, column=1, padx=10, pady=5, sticky="w")
        
        self.delay_slider = ctk.CTkSlider(self.main_frame, from_=0, to=60, number_of_steps=6, command=self.update_delay_label, width=300)
        self.delay_slider.set(self.config.get("delay", 10))
        self.delay_slider.grid(row=start_row+1, column=2, padx=20, pady=5, sticky="w")
        
        # Визуальный режим
        self.visual_var = tk.BooleanVar(value=self.config.get("visual_mode", False))
        cb_visual = ctk.CTkCheckBox(self.main_frame, text="Визуальный режим (показывать браузер)", variable=self.visual_var, font=ctk.CTkFont(size=14))
        cb_visual.grid(row=start_row+2, column=0, columnspan=3, padx=20, pady=10, sticky="w")
        
        # --- Кнопки управления ---
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.grid(row=start_row+3, column=0, columnspan=4, pady=30)
        
        self.btn_start = ctk.CTkButton(btn_frame, text="▶️ СТАРТ", command=self.start_parsing, height=50, font=ctk.CTkFont(size=18, weight="bold"), fg_color="#2196F3", hover_color="#1976D2")
        self.btn_start.pack(side="left", padx=20)
        
        self.btn_report = ctk.CTkButton(btn_frame, text="📊 ОТЧЁТ", command=self.open_report, height=50, font=ctk.CTkFont(size=18), fg_color="#FF9800", hover_color="#F57C00")
        self.btn_report.pack(side="left", padx=20)
        
        self.btn_save = ctk.CTkButton(btn_frame, text="💾 СОХРАНИТЬ", command=self.save_and_close_settings, height=50, font=ctk.CTkFont(size=18), fg_color="#9C27B0", hover_color="#7B1FA2")
        self.btn_save.pack(side="left", padx=20)

        # Кнопка копирования логов
        self.btn_copy_log = ctk.CTkButton(btn_frame, text="📋 Копировать лог", command=self.copy_log, height=30, font=ctk.CTkFont(size=14), fg_color="#555555", hover_color="#777777")
        self.btn_copy_log.pack(side="left", padx=20)
        
        # --- Логгер ---
        lbl_log = ctk.CTkLabel(self.main_frame, text="📜 Логи работы:", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_log.grid(row=start_row+4, column=0, columnspan=4, pady=(20, 5), sticky="w")
        
        # Используем стандартный tk.Text для поддержки тегов и копирования
        self.log_text = tk.Text(self.main_frame, font=("Consolas", 13), wrap="word", bg="#2b2b2b", fg="#ffffff", insertbackground="white", relief="flat", bd=2, state="disabled")
        self.log_text.grid(row=start_row+5, column=0, columnspan=4, padx=20, pady=(0, 20), sticky="nsew")
        
        # Конфигурация тегов
        self.log_text.tag_configure("error", foreground="#ff6b6b")
        self.log_text.tag_configure("warning", foreground="#ffd93d")
        self.log_text.tag_configure("success", foreground="#6bff6b")
        self.log_text.tag_configure("info", foreground="#ffffff")
        
        self.log_message("👋 Лаунчер готов к работе!", "info")
        self.log_message(f"⚙️ Текущая задержка: {self.config.get('delay', 10)} сек", "info")

    def update_delay_label(self, value):
        val = int(round(float(value) / 10) * 10)
        self.delay_slider.set(val)
        self.delay_val_label.configure(text=str(val))

    def copy_log(self):
        full_text = self.log_text.get("1.0", "end-1c")
        pyperclip.copy(full_text)
        self.log_message("📋 Лог скопирован в буфер обмена", "success")

    def log_message(self, message, level="info"):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        full_msg = f"{timestamp} {message}\n"
        
        self.log_text.configure(state="normal")
        self.log_text.insert("end", full_msg)
        
        tag = level
        if level not in ["error", "warning", "success", "info"]:
            tag = "info"
            
        self.log_text.tag_add(tag, "end-2c linestart", "end-1c lineend")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def start_parsing(self):
        if self.is_running:
            messagebox.showwarning("Внимание", "Парсер уже запущен!")
            return
            
        selected_shops = [name for name, var in self.shop_vars.items() if var.get()]
        if not selected_shops:
            messagebox.showerror("Ошибка", "Выберите хотя бы один магазин!")
            return
            
        self.is_running = True
        self.btn_start.configure(state="disabled", text="⏳ РАБОТАЕТ...")
        
        delay = int(self.delay_slider.get())
        visual = self.visual_var.get()
        
        self.log_message(f"🚀 Старт: {', '.join(selected_shops)}", "success")
        self.log_message(f"⚙️ Задержка: {delay} сек, Визуальный режим: {'ВКЛ' if visual else 'ВЫКЛ'}", "info")
        
        thread = threading.Thread(target=self.run_parser_process, args=(selected_shops, delay, visual))
        thread.daemon = True
        thread.start()

    def run_parser_process(self, shops, delay, visual):
        try:
            env = os.environ.copy()
            env["PARSER_SHOPS"] = ",".join([s.lower() for s in shops])
            env["PARSER_DELAY"] = str(delay)
            env["VISUAL_MODE"] = "true" if visual else "false"
            
            # Явно указываем путь к main.py в текущей директории
            script_path = os.path.join(os.getcwd(), "main.py")
            
            if not os.path.exists(script_path):
                self.root.after(0, lambda: self.log_message(f"❌ Файл main.py не найден по пути: {script_path}", "error"))
                self.root.after(0, self.parsing_finished)
                return

            self.process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            
            for line in self.process.stdout:
                self.root.after(0, self.log_message, line.strip(), "info")
                
            self.process.wait()
            
            if self.process.returncode == 0:
                self.root.after(0, lambda: self.log_message("🎉 Готово! Проверьте отчет.", "success"))
                self.last_report_path = os.path.join("data", "export")
            else:
                self.root.after(0, lambda: self.log_message("❌ Процесс завершен с ошибкой.", "error"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Ошибка запуска: {str(e)}", "error"))
        finally:
            self.root.after(0, self.parsing_finished)

    def parsing_finished(self):
        self.is_running = False
        self.btn_start.configure(state="normal", text="▶️ СТАРТ")
        self.process = None

    def open_report(self):
        export_dir = os.path.join("data", "export")
        if os.path.exists(export_dir):
            files = [f for f in os.listdir(export_dir) if f.endswith(".xlsx")]
            if files:
                latest = max(files, key=lambda f: os.path.getctime(os.path.join(export_dir, f)))
                os.startfile(os.path.join(export_dir, latest))
                self.log_message(f"📂 Открыт файл: {latest}", "success")
                return
        
        self.log_message("⚠️ Файлов отчетов не найдено. Сначала запустите парсер.", "warning")
        os.makedirs(export_dir, exist_ok=True)
        os.startfile(export_dir)

    def save_and_close_settings(self):
        self.save_config()
        messagebox.showinfo("Успех", "Настройки сохранены!\nОкно не закрывается для удобства.")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    try:
        ParserLauncher().run()
    except Exception as e:
        print(f"Critical Error: {e}")
        input("Press Enter to exit...")
