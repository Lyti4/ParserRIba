"""
Модуль для загрузки и валидации конфигурации из Knowledge Base.
Парсит Markdown файлы, извлекает селекторы, заголовки и стратегии обхода защит.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator, ConfigDict
from loguru import logger

from utils.kb_interception import InterceptionConfig, parse_interception_section


class SelectorConfig(BaseModel):
    """Конфигурация селекторов для одного элемента."""
    css: Optional[str] = None
    xpath: Optional[str] = None
    regex: Optional[str] = None
    fallback: Optional[List[str]] = None
    priority: int = 1
    description: str = ""


class HeadersConfig(BaseModel):
    """Конфигурация HTTP заголовков."""
    standard: Dict[str, str] = Field(default_factory=dict)
    custom: Dict[str, str] = Field(default_factory=dict)
    notes: str = ""


class AntiBotConfig(BaseModel):
    """Конфигурация анти-бот защиты."""
    triggers: List[str] = Field(default_factory=list)
    strategies: List[str] = Field(default_factory=list)
    captcha_types: List[str] = Field(default_factory=list)
    recommended_tool: str = "curl-cffi"  # или playwright


class ShopKnowledge(BaseModel):
    """Полная модель знаний о магазине."""
    name: str
    slug: str
    base_url: str
    categories: Dict[str, str] = Field(default_factory=dict)
    selectors: Dict[str, SelectorConfig] = Field(default_factory=dict)
    headers: HeadersConfig = Field(default_factory=HeadersConfig)
    anti_bot: AntiBotConfig = Field(default_factory=AntiBotConfig)
    interception: InterceptionConfig = Field(default_factory=InterceptionConfig)
    notes: List[str] = Field(default_factory=list)
    technical_details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class KBLoader:
    """Загрузчик базы знаний из Markdown файлов."""

    def __init__(self, kb_path: str = "knowledge_base"):
        self.kb_path = Path(kb_path)
        if not self.kb_path.exists():
            raise FileNotFoundError(f"Папка knowledge_base не найдена по пути: {self.kb_path}")

    def load_shop(self, shop_slug: str) -> ShopKnowledge:
        """
        Загружает знания для конкретного магазина.
        
        :param shop_slug: Имя файла без расширения (например, 'pyaterochka')
        :return: Объект ShopKnowledge
        """
        file_path = self.kb_path / f"{shop_slug}.md"
        if not file_path.exists():
            raise FileNotFoundError(f"Файл знаний не найден: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        return self._parse_markdown(content, shop_slug)

    def _parse_markdown(self, content: str, slug: str) -> ShopKnowledge:
        """Парсит содержимое Markdown файла в модель Pydantic."""
        
        # Базовые поля
        name_match = re.search(r"#\s+📘\s*Knowledge Base:\s*(.+)", content)
        name = name_match.group(1).strip() if name_match else slug.title()

        # URLs - ищем базовый URL в общей информации или таблице
        base_url = ""
        categories = {}
        
        # Поиск базового URL в секции "Общая информация"
        base_url_match = re.search(r"\*\*Базовый URL\*\*:\s*`([^`]+)`", content)
        if base_url_match:
            base_url = base_url_match.group(1)
        
        # Парсинг таблицы категорий
        url_section = self._extract_section(content, "🔗")
        if url_section:
            lines = url_section.split("\n")
            for line in lines:
                if "|" in line and "http" in line:
                    parts = [p.strip().strip("`") for p in line.split("|")]
                    if len(parts) >= 3:
                        cat_name = parts[1].strip()
                        url = parts[2].strip()
                        if cat_name and cat_name != "Категория" and not cat_name.startswith("-"):
                            categories[cat_name] = url

        # Селекторы - парсим code blocks с CSS
        selectors = {}
        sel_section = self._extract_section(content, "🎯")
        if sel_section:
            # Ищем все заголовки ### и CSS блоки после них
            lines = sel_section.split('\n')
            current_field = None
            current_selectors = []
            
            field_mapping = {
                "карточк": "product_card",
                "названи": "product_name", 
                "старая цена": "price_old",  # Проверяем ДО "цена"
                "цена": "price_current",
                "ссылк": "product_link",
                "вес": "weight_volume",
                "бренд": "brand",
                "изображени": "image_url",
                "скидк": "discount_badge",
                "пагинац": "pagination_next",
                "единиц": "unit_price"
            }
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Проверяем заголовок ###
                if line.startswith('###'):
                    # Сохраняем предыдущие селекторы если были
                    if current_field and current_selectors:
                        selectors[current_field] = SelectorConfig(
                            css=" | ".join(current_selectors),
                            priority=1,
                            description=f"Селекторы для: {current_field}"
                        )
                    
                    # Определяем новое поле по заголовку
                    current_field = None
                    current_selectors = []
                    header_lower = line.lower()
                    for key, field_name in field_mapping.items():
                        if key in header_lower:
                            current_field = field_name
                            break
                
                # Проверяем начало CSS блока
                elif line.strip().startswith('```css'):
                    i += 1
                    # Собираем селекторы до конца блока
                    while i < len(lines) and not lines[i].strip().startswith('```'):
                        sel_line = lines[i].strip()
                        # Пропускаем комментарии и пустые строки
                        if sel_line and not sel_line.startswith('/*') and not sel_line.startswith('*'):
                            # Убираем inline комментарии
                            selector = sel_line.split('/*')[0].strip()
                            if selector:
                                # Если селектор содержит запятую (несколько CSS селекторов), разделяем их
                                if ',' in selector:
                                    # Разделяем по запятой и добавляем каждый отдельно
                                    for sub_sel in [s.strip() for s in selector.split(',')]:
                                        if sub_sel:
                                            current_selectors.append(sub_sel)
                                else:
                                    current_selectors.append(selector)
                        i += 1
                
                i += 1
            
            # Сохраняем последние селекторы
            if current_field and current_selectors:
                selectors[current_field] = SelectorConfig(
                    css=" | ".join(current_selectors),
                    priority=1,
                    description=f"Селекторы для: {current_field}"
                )

        # Headers - ищем в секции с глобусом
        headers = HeadersConfig()
        head_section = self._extract_section(content, "🌐")
        if head_section:
            # Ищем X-заголовки в любом месте текста секции
            x_headers = re.findall(r"'(X-[A-Za-z-]+)':\s*'([^']+)'", head_section)
            for key, val in x_headers:
                headers.custom[key.strip()] = val.strip()
            
            # Проверка на критичность
            if "критично" in head_section.lower() or "обязателен" in head_section.lower():
                headers.notes = "Внимание: Некоторые заголовки критичны для работы"

        # Anti-Bot
        anti_bot = AntiBotConfig()
        ab_section = self._extract_section(content, "🛡")
        if ab_section:
            if "cloudflare" in ab_section.lower():
                anti_bot.captcha_types.append("Cloudflare Turnstile")
                anti_bot.recommended_tool = "playwright"
            if "recaptcha" in ab_section.lower():
                anti_bot.captcha_types.append("reCAPTCHA v2")
            
            # Стратегии
            if "скроллинг" in ab_section.lower() or "scroll" in ab_section.lower():
                anti_bot.strategies.append("scrolling")
            if "задержк" in ab_section.lower() or "delay" in ab_section.lower():
                anti_bot.strategies.append("random_delay")
            if "только playwright" in ab_section.lower() or "only playwright" in ab_section.lower():
                anti_bot.recommended_tool = "playwright"

        interception = parse_interception_section(content)

        # Заметки - ищем списки в секции 📝
        notes = []
        note_section = self._extract_section(content, "📝")
        if note_section:
            # Ищем пункты списков
            note_lines = re.findall(r"^[-*]\s*(.+)$", note_section, re.MULTILINE)
            notes = [line.strip() for line in note_lines]

        return ShopKnowledge(
            name=name,
            slug=slug,
            base_url=base_url,
            categories=categories,
            selectors=selectors,
            headers=headers,
            anti_bot=anti_bot,
            interception=interception,
            notes=notes
        )

    def _extract_section(self, content: str, emoji: str) -> str:
        """Извлекает секцию контента по эмодзи-маркеру."""
        # Более надежный подход - посимвольный поиск по строкам
        lines = content.split('\n')
        in_section = False
        section_lines = []
        
        for line in lines:
            # Проверяем начало секции (заголовок ## с эмодзи)
            if line.startswith('## ') and emoji in line:
                in_section = True
                continue
            # Проверяем конец секции (следующий заголовок ##)
            elif line.startswith('## ') and in_section:
                break
            # Собираем строки секции
            elif in_section:
                section_lines.append(line)
        
        return '\n'.join(section_lines)

    def list_available_shops(self) -> List[str]:
        """Возвращает список доступных магазинов."""
        shops = []
        for f in self.kb_path.glob("*.md"):
            if f.name != "template.md":
                shops.append(f.stem)
        return sorted(shops)


# Пример использования и тестирования
if __name__ == "__main__":
    loader = KBLoader()

    logger.info("Available stores: {}", loader.list_available_shops())
    
    # Тест загрузки Пятерочки
    try:
        pya = loader.load_shop("pyaterochka")
        logger.info(
            "Loaded {}: url={}, selectors={}, custom_headers={}, tool={}",
            pya.name,
            pya.base_url,
            len(pya.selectors),
            pya.headers.custom,
            pya.anti_bot.recommended_tool,
        )
    except Exception as e:
        logger.error("Failed to load pyaterochka KB: {}", e)

    # Тест загрузки Перекрестка (сложный случай)
    try:
        per = loader.load_shop("perekrestok")
        logger.info(
            "Loaded {}: tool={}, captcha_types={}",
            per.name,
            per.anti_bot.recommended_tool,
            per.anti_bot.captcha_types,
        )
    except Exception as e:
        logger.error("Failed to load perekrestok KB: {}", e)
