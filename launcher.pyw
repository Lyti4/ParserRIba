# launcher.pyw — запускается двойным кликом, без чёрного окна
import customtkinter as ctk
import subprocess
import threading
import json
import os
import sys
from datetime import datetime

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ParserLauncher:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("🐟 Парсер цен на рыбу — Москва")
        self.app.geometry("500x600")
        self.app.resizable(False, False)
        
        # Загрузка настроек
        self.config = self.load_config()
        
        self.setup_ui()
        self.app.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def load_config(self):
        """Загрузка настроек из config.json"""
        default = {
            "stores": ["pyaterochka", "magnit", "perekrestok"],
            "delay": 5,
            "visual_mode": True,
            "output_file": f"fish_{datetime.now().strftime('%Y%m%d')}.xlsx"
        }
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    return {**default, **loaded}
        except Exception as e:
            print(f"Ошибка загрузки конфига: {e}")
        return default
        
    def save_config(self):
        """Сохранение настроек"""
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def setup_ui(self):
        # Заголовок
        ctk.CTkLabel(self.app, text="🐟 Парсер рыбных товаров", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)
        
        # Выбор магазинов
        ctk.CTkLabel(self.app, text="Выберите магазины:", anchor="w").pack(pady=(10,5), padx=20, fill="x")
        self.store_vars = {}
        stores = [("Пятёрочка", "pyaterochka"), ("Магнит", "magnit"), ("Перекрёсток", "perekrestok"), 
                  ("Лента", "lenta"), ("Ашан", "auchan"), ("О'Кей", "okey")]
        for text, key in stores:
            var = ctk.BooleanVar(value=key in self.config.get("stores", ["pyaterochka"]))
            self.store_vars[key] = var
            ctk.CTkCheckBox(self.app, text=text, variable=var).pack(pady=2, padx=30, anchor="w")
        
        # Настройки
        frame = ctk.CTkFrame(self.app)
        frame.pack(pady=15, padx=20, fill="x")
        
        ctk.CTkLabel(frame, text="Задержка между запросами (сек):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.delay_slider = ctk.CTkSlider(frame, from_=2, to=30, number_of_steps=28, command=lambda v: self.config.update(delay=int(v)))
        self.delay_slider.set(self.config.get("delay", 5))
        self.delay_slider.grid(row=0, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(frame, text="Визуальный режим:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.visual_switch = ctk.CTkSwitch(frame, text="Показывать браузер", 
                                           command=lambda: self.config.update(visual_mode=self.visual_switch.get()))
        self.visual_switch.select(self.config.get("visual_mode", True))
        self.visual_switch.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # Лог-окно
        ctk.CTkLabel(self.app, text="📋 Логи:", anchor="w").pack(pady=(10,5), padx=20, fill="x")
        self.log_text = ctk.CTkTextbox(self.app, width=450, height=150, font=ctk.CTkFont(size=10))
        self.log_text.pack(pady=5, padx=20)
        
        # Кнопки
        btn_frame = ctk.CTkFrame(self.app, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        self.start_btn = ctk.CTkButton(btn_frame, text="▶️ Запустить парсинг", command=self.start_parsing, width=200)
        self.start_btn.pack(side="left", padx=10)
        
        ctk.CTkButton(btn_frame, text="📂 Открыть отчёт", command=self.open_report, width=150).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="⚙️ Сохранить настройки", command=self.save_and_close, width=150).pack(side="left", padx=10)
        
        # Статус
        self.status_label = ctk.CTkLabel(self.app, text="✅ Готов к запуску", text_color="green")
        self.status_label.pack(pady=10)
        
    def log(self, message: str):
        """Добавление сообщения в лог-окно"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        
    def start_parsing(self):
        """Запуск парсера в отдельном потоке"""
        # Сохраняем выбранные магазины
        selected = [k for k, v in self.store_vars.items() if v.get()]
        if not selected:
            self.log("❌ Выберите хотя бы один магазин!")
            return
            
        self.config["stores"] = selected
        self.save_config()
        
        # Блокируем кнопку
        self.start_btn.configure(state="disabled")
        self.status_label.configure(text="🔄 Парсинг запущен...", text_color="orange")
        self.log(f"🚀 Запуск парсинга: {', '.join(selected)}")
        
        # Запускаем в потоке
        threading.Thread(target=self._run_parser, daemon=True).start()
        
    def _run_parser(self):
        """Запуск main.py в отдельном процессе"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Запускаем с захватом вывода
            proc = subprocess.run(
                [sys.executable, "main.py"],
                capture_output=True,
                text=True,
                cwd=script_dir,
                env={**os.environ, "VISUAL_MODE": str(self.config.get("visual_mode", True)).lower()}
            )
            
            # Показываем логи
            if proc.stdout:
                for line in proc.stdout.strip().split("\n"):
                    if line:
                        self.log(line)
            if proc.stderr:
                for line in proc.stderr.strip().split("\n"):
                    if line:
                        self.log(f"⚠️ {line}")
                    
            # Обновляем статус
            if proc.returncode == 0:
                self.status_label.configure(text="✅ Парсинг завершён!", text_color="green")
                self.log("🎉 Готово! Отчёт сохранён.")
            else:
                self.status_label.configure(text="❌ Ошибка парсинга", text_color="red")
                self.log(f"❌ Код возврата: {proc.returncode}")
                
        except Exception as e:
            self.log(f"❌ Ошибка запуска: {e}")
            self.status_label.configure(text="❌ Ошибка", text_color="red")
        finally:
            self.start_btn.configure(state="normal")
            
    def open_report(self):
        """Открытие папки с отчётами"""
        export_dir = os.path.join(os.path.dirname(__file__), "data", "export")
        os.makedirs(export_dir, exist_ok=True)
        try:
            os.startfile(export_dir)
        except Exception:
            self.log("Не удалось открыть папку экспорта")
        
    def save_and_close(self):
        """Сохранение и закрытие"""
        self.save_config()
        self.log("⚙️ Настройки сохранены")
        self.app.destroy()
        
    def on_close(self):
        """Обработчик закрытия окна"""
        self.save_config()
        self.app.destroy()
        
    def run(self):
        self.app.mainloop()

if __name__ == "__main__":
    ParserLauncher().run()
