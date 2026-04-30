# launcher.pyw — GUI-лаунчер для ParserRIba (Windows)
# Запускается двойным кликом, без чёрного окна консоли
# Исправлена ошибка совместимости pack/grid

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
        self.app.geometry("500x650")
        self.app.minsize(450, 600)
        
        self.log_queue = queue.Queue()
        self.app.after(100, self.process_log_queue)
        
        self.config = self.load_config()
        self.setup_ui()
        self.app.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def load_config(self):
        default = {
            "stores": ["pyaterochka", "magnit"],
            "delay": 5,
            "visual_mode": True,
            "output_file": f"fish_{datetime.now().strftime('%Y%m%d')}.xlsx"
        }
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    return {**default, **loaded}
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
                self.log_text.insert("end", f"[{timestamp}] {message}\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.app.after(100, self.process_log_queue)

    def log(self, message: str):
        self.log_queue.put(message)
        
    def setup_ui(self):
        # --- Заголовок ---
        ctk.CTkLabel(self.app, text="🐟 Парсер рыбных товаров", 
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(15, 5))

        # --- Магазины (ИСПРАВЛЕНО: только grid внутри фрейма) ---
        stores_frame = ctk.CTkFrame(self.app, fg_color=("gray20", "gray10"))
        stores_frame.pack(fill="x", padx=20, pady=10)
        
        # Заголовок внутри фрейма через grid (row=0)
        ctk.CTkLabel(stores_frame, text="Выберите магазины:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
        
        self.store_vars = {}
        stores_list = [
            ("Пятёрочка", "pyaterochka"), 
            ("Магнит", "magnit"), 
            ("Перекрёсток", "perekrestok"), 
            ("Лента", "lenta"), 
            ("Ашан", "auchan"), 
            ("О'Кей", "okey")
        ]
        
        row, col = 1, 0 # Начинаем сетку с 1-й строки
        for text, key in stores_list:
            var = ctk.BooleanVar(value=key in self.config["stores"])
            self.store_vars[key] = var
            cb = ctk.CTkCheckBox(stores_frame, text=text, variable=var, width=150)
            cb.grid(row=row, column=col, padx=10, pady=5, sticky="w")
            col += 1
            if col > 1: 
                col = 0
                row += 1
        
        # --- Настройки ---
        settings_frame = ctk.CTkFrame(self.app, fg_color=("gray20", "gray10"))
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(settings_frame, text="Задержка (сек):").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.delay_slider = ctk.CTkSlider(settings_frame, from_=1, to=30, number_of_steps=29, width=200)
        self.delay_slider.set(self.config["delay"])
        self.delay_slider.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(settings_frame, text="Браузер:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.visual_switch = ctk.CTkSwitch(settings_frame, text="Показывать")
        self.visual_switch.select(self.config["visual_mode"])
        self.visual_switch.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        settings_frame.columnconfigure(1, weight=1)

        # --- Логи ---
        log_container = ctk.CTkFrame(self.app, fg_color="transparent")
        log_container.pack(fill="both", expand=True, padx=20, pady=(10, 5))
        
        ctk.CTkLabel(log_container, text="Логи:", anchor="w").pack(fill="x")
        self.log_text = ctk.CTkTextbox(log_container, width=400, font=ctk.CTkFont(size=11))
        self.log_text.pack(fill="both", expand=True, pady=5)
        self.log_text.configure(state="disabled")
        
        # --- Кнопки ---
        btn_frame = ctk.CTkFrame(self.app, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        self.start_btn = ctk.CTkButton(btn_frame, text="▶️ Запустить парсинг", command=self.start_parsing, height=40, font=ctk.CTkFont(weight="bold"))
        self.start_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(btn_frame, text="📂 Отчёт", command=self.open_report, height=40).pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(btn_frame, text="⚙️ Настройки", command=self.save_and_close, height=40).pack(side="left", padx=5, fill="x", expand=True)
        
        # --- Статус ---
        self.status_label = ctk.CTkLabel(self.app, text="✅ Готов к запуску", text_color="green", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=(0, 10))
        
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
        self.status_label.configure(text="🔄 Парсинг запущен...", text_color="orange")
        self.log(f"🚀 Старт парсинга: {', '.join(selected)}")
        
        threading.Thread(target=self._run_parser, daemon=True).start()
        
    def _run_parser(self):
        try:
            env = os.environ.copy()
            env["VISUAL_MODE"] = str(self.config["visual_mode"]).lower()
            
            proc = subprocess.run(
                [sys.executable, "main.py"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env,
                timeout=300
            )
            
            output = (proc.stdout + proc.stderr).strip()
            if output:
                for line in output.split('\n'):
                    if line: self.log(line)
            
            if proc.returncode == 0:
                self.status_label.configure(text="✅ Завершено успешно!", text_color="#2ecc71")
                self.log("🎉 Парсинг успешно завершен.")
            else:
                self.status_label.configure(text="❌ Ошибка выполнения", text_color="#e74c3c")
                self.log(f"⚠️ Скрипт завершился с кодом {proc.returncode}")
                
        except Exception as e:
            self.log(f"💥 Критическая ошибка: {e}")
            self.status_label.configure(text="❌ Ошибка", text_color="red")
        finally:
            self.start_btn.configure(state="normal", text="▶️ Запустить парсинг")
            
    def open_report(self):
        export_dir = os.path.join(os.path.dirname(__file__), "data", "export")
        os.makedirs(export_dir, exist_ok=True)
        try:
            files = [f for f in os.listdir(export_dir) if f.endswith('.xlsx')]
            if files:
                latest = max(files, key=lambda x: os.path.getctime(os.path.join(export_dir, x)))
                os.startfile(os.path.join(export_dir, latest))
            else:
                os.startfile(export_dir)
                self.log("⚠️ Файлов нет, открыта папка.")
        except Exception as e:
            self.log(f"Ошибка открытия: {e}")
            os.startfile(export_dir)
        
    def save_and_close(self):
        self.save_config()
        self.log("⚙️ Настройки сохранены")
        self.app.destroy()
        
    def on_close(self):
        self.save_config()
        self.app.destroy()
        
    def run(self):
        self.app.mainloop()

if __name__ == "__main__":
    ParserLauncher().run()
