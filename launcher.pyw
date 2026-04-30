# launcher.pyw — GUI-лаунчер для ParserRIba (Windows)
# Запускается двойным кликом, без чёрного окна консоли

import customtkinter as ctk
import subprocess, threading, json, os, sys
from datetime import datetime
import queue

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ParserLauncher:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("🐟 Парсер цен на рыбу — Москва")
        self.app.geometry("800x750")
        self.app.resizable(True, True)
        
        self.log_queue = queue.Queue()
        self.last_report_path = None
        self.app.after(100, self.process_log_queue)
        
        self.config = self.load_config()
        self.setup_ui()
        self.app.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def load_config(self):
        default = {
            "stores": ["pyaterochka", "magnit"],
            "delay": 10,
            "visual_mode": True,
            "output_file": f"fish_{datetime.now().strftime('%Y%m%d')}.xlsx"
        }
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    return {**default, **json.load(f)}
        except: pass
        return default
        
    def save_config(self):
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def process_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_text.configure(state="normal")
                
                # Определение цвета по содержимому сообщения
                color = "#ffffff"  # белый по умолчанию
                
                # Красный для ошибок
                if any(x in message for x in ["❌", "Ошибка", "Error", "💥", "Traceback"]):
                    color = "#ff6b6b"
                # Желтый для предупреждений
                elif any(x in message for x in ["⚠️", "Warning", "⏳", "Внимание"]):
                    color = "#ffd93d"
                # Зеленый для успеха
                elif any(x in message for x in ["✅", "🎉", "🚀", "Успешно", "Готово", "✔️"]):
                    color = "#6bff6b"
                
                # Вставка текста с цветом
                self.log_text.insert("end", f"[{timestamp}] ", "timestamp")
                self.log_text.insert("end", f"{message}\n", ("colored", color))
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
                
                # Настройка тегов для цветов
                self.log_text.tag_config("timestamp", foreground="#888888")
                self.log_text.tag_config("colored", foreground=color)
        except queue.Empty:
            pass
        self.app.after(100, self.process_log_queue)

    def log(self, message: str):
        self.log_queue.put(message)
        
    def setup_ui(self):
        # Основной контейнер с отступами
        main_container = ctk.CTkFrame(self.app, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=30, pady=20)
        main_container.rowconfigure(7, weight=1)  # Логи растягиваются
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.columnconfigure(2, weight=1)
        
        # Заголовок
        title_label = ctk.CTkLabel(main_container, text="🐟 Парсер рыбных товаров", 
                     font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky="ew")
        
        # Выбор магазинов
        stores_label = ctk.CTkLabel(main_container, text="Выберите магазины:", font=ctk.CTkFont(size=16, weight="bold"))
        stores_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        self.store_vars = {}
        stores_list = [
            ("Пятёрочка", "pyaterochka"), ("Магнит", "magnit"), 
            ("Перекрёсток", "perekrestok"), ("Лента", "lenta"), 
            ("Ашан", "auchan"), ("О'Кей", "okey")
        ]
        
        # Сетка 3 колонки
        for i, (text, key) in enumerate(stores_list):
            var = ctk.BooleanVar(value=key in self.config["stores"])
            self.store_vars[key] = var
            cb = ctk.CTkCheckBox(main_container, text=text, variable=var, 
                                 font=ctk.CTkFont(size=14), width=180)
            row = (i // 3) + 2
            col = i % 3
            cb.grid(row=row, column=col, padx=10, pady=8, sticky="w")
        
        # Настройки (задержка и режим)
        settings_label = ctk.CTkLabel(main_container, text="Настройки:", font=ctk.CTkFont(size=16, weight="bold"))
        settings_label.grid(row=3, column=0, columnspan=3, sticky="w", pady=(20, 10))
        
        # Задержка с ползунком
        delay_label = ctk.CTkLabel(main_container, text="Задержка (сек):", font=ctk.CTkFont(size=14))
        delay_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        
        self.delay_value_label = ctk.CTkLabel(main_container, text=f"{self.config['delay']}", 
                                               font=ctk.CTkFont(size=14, weight="bold"), width=40)
        self.delay_value_label.grid(row=4, column=1, padx=5, pady=10, sticky="w")
        
        # Ползунок: 0, 10, 20, 30, 40, 50, 60 (6 шагов)
        self.delay_slider = ctk.CTkSlider(main_container, from_=0, to=60, number_of_steps=6, width=250,
                                          command=self.update_delay_label)
        self.delay_slider.set(self.config["delay"])
        self.delay_slider.grid(row=4, column=2, padx=10, pady=10, sticky="w")
        
        # Режим браузера
        visual_label = ctk.CTkLabel(main_container, text="Режим браузера:", font=ctk.CTkFont(size=14))
        visual_label.grid(row=5, column=0, padx=10, pady=10, sticky="w")
        
        self.visual_switch = ctk.CTkSwitch(main_container, text="Показывать браузер (отладка)",
                                           font=ctk.CTkFont(size=14))
        self.visual_switch.select(self.config["visual_mode"])
        self.visual_switch.grid(row=5, column=1, columnspan=2, padx=10, pady=10, sticky="w")
        
        # Логи
        logs_label = ctk.CTkLabel(main_container, text="Логи работы:", font=ctk.CTkFont(size=16, weight="bold"))
        logs_label.grid(row=6, column=0, columnspan=3, sticky="w", pady=(20, 5))
        
        self.log_text = ctk.CTkTextbox(main_container, font=ctk.CTkFont(size=13, family="Consolas"),
                                       wrap="word")
        self.log_text.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(0, 10))
        self.log_text.configure(state="disabled")
        
        # Кнопки
        btn_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)
        
        self.start_btn = ctk.CTkButton(btn_frame, text="▶️ ЗАПУСТИТЬ", command=self.start_parsing, 
                                        height=50, font=ctk.CTkFont(size=18, weight="bold"), 
                                        fg_color="#2ecc71", hover_color="#27ae60")
        self.start_btn.grid(row=0, column=0, padx=10, sticky="ew")
        
        self.report_btn = ctk.CTkButton(btn_frame, text="📂 ОТЧЁТ", command=self.open_report, 
                                         height=50, font=ctk.CTkFont(size=18, weight="bold"),
                                         fg_color="#3498db", hover_color="#2980b9")
        self.report_btn.grid(row=0, column=1, padx=10, sticky="ew")
        
        self.save_btn = ctk.CTkButton(btn_frame, text="⚙️ СОХРАНИТЬ", command=self.save_settings, 
                                       height=50, font=ctk.CTkFont(size=18, weight="bold"),
                                       fg_color="#9b59b6", hover_color="#8e44ad")
        self.save_btn.grid(row=0, column=2, padx=10, sticky="ew")
        
        # Статус
        self.status_label = ctk.CTkLabel(main_container, text="✅ Готов к запуску", 
                                          text_color="#2ecc71", font=ctk.CTkFont(size=16, weight="bold"))
        self.status_label.grid(row=9, column=0, columnspan=3, pady=(15, 0), sticky="ew")
        
    def update_delay_label(self, value):
        rounded = int(round(value / 10) * 10)
        self.delay_value_label.configure(text=str(rounded))
        self.delay_slider.set(rounded)
        
    def start_parsing(self):
        selected = [k for k, v in self.store_vars.items() if v.get()]
        if not selected:
            self.log("❌ Выберите хотя бы один магазин!")
            return
            
        self.config["stores"] = selected
        self.config["delay"] = int(self.delay_slider.get())
        self.config["visual_mode"] = self.visual_switch.get()
        self.save_config()
        
        self.start_btn.configure(state="disabled", text="⏳ Работает...")
        self.status_label.configure(text="🔄 Парсинг запущен...", text_color="#f39c12")
        self.log(f"🚀 Старт: {', '.join(selected)}")
        self.log(f"⚙️ Задержка: {self.config['delay']} сек, Визуальный режим: {self.config['visual_mode']}")
        
        threading.Thread(target=self._run_parser, daemon=True).start()
        
    def _run_parser(self):
        try:
            env = os.environ.copy()
            env["VISUAL_MODE"] = str(self.config["visual_mode"]).lower()
            
            proc = subprocess.run(
                [sys.executable, "main.py"],
                capture_output=True, text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env,
                timeout=600
            )
            
            output = (proc.stdout + proc.stderr).strip()
            if output:
                for line in output.split('\n'):
                    if line: self.log(line)
            
            if proc.returncode == 0:
                self.status_label.configure(text="✅ Успешно завершено!", text_color="#2ecc71")
                self.log("🎉 Готово! Проверьте отчет.")
            else:
                self.status_label.configure(text="❌ Ошибка выполнения", text_color="#e74c3c")
                self.log(f"⚠️ Код ошибки: {proc.returncode}")
                
        except subprocess.TimeoutExpired:
            self.log("💥 Ошибка: Превышено время ожидания (10 мин)")
            self.status_label.configure(text="❌ Таймаут", text_color="#e74c3c")
        except Exception as e:
            self.log(f"💥 Критическая ошибка: {e}")
            self.status_label.configure(text="❌ Ошибка", text_color="#e74c3c")
        finally:
            self.start_btn.configure(state="normal", text="▶️ ЗАПУСТИТЬ")
            
    def open_report(self):
        export_dir = os.path.join(os.path.dirname(__file__), "data", "export")
        os.makedirs(export_dir, exist_ok=True)
        
        # Проверяем последний сохраненный путь
        if self.last_report_path and os.path.exists(self.last_report_path):
            try:
                os.startfile(self.last_report_path)
                self.log("✅ Открыт последний отчет")
                return
            except:
                pass
        
        try:
            files = [f for f in os.listdir(export_dir) if f.endswith('.xlsx')]
            if files:
                latest = max(files, key=lambda x: os.path.getctime(os.path.join(export_dir, x)))
                report_path = os.path.join(export_dir, latest)
                self.last_report_path = report_path
                os.startfile(report_path)
                self.log(f"✅ Открыт отчет: {latest}")
            else:
                os.startfile(export_dir)
                self.log("⚠️ Файлов нет, открыта папка data/export")
        except Exception as e:
            self.log(f"❌ Ошибка открытия: {e}")
            try:
                os.startfile(export_dir)
            except:
                self.log("⚠️ Не удалось открыть папку")
        
    def save_settings(self):
        self.config["stores"] = [k for k, v in self.store_vars.items() if v.get()]
        self.config["delay"] = int(self.delay_slider.get())
        self.config["visual_mode"] = self.visual_switch.get()
        self.save_config()
        self.log("✅ Настройки сохранены в config.json")
        self.status_label.configure(text="⚙️ Настройки сохранены", text_color="#9b59b6")
        
        # Блокируем кнопку на 1 секунду чтобы не закрыть случайно
        self.save_btn.configure(state="disabled")
        self.app.after(1000, lambda: self.save_btn.configure(state="normal"))
        
    def on_close(self):
        self.save_config()
        self.log("👋 Закрытие лаунчера...")
        self.app.destroy()
        
    def run(self):
        self.app.mainloop()

if __name__ == "__main__":
    ParserLauncher().run()
