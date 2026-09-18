"""Derive conservative supplier/brand labels from product names."""

from __future__ import annotations

import re

LEADING_PRODUCT_WORDS = {
    "вино",
    "пиво",
    "напиток",
    "энергетический",
    "энергетик",
    "пивной",
}
DESCRIPTOR_WORDS = {
    "безалкогольное",
    "безалкогольный",
    "безалкогольная",
    "газированное",
    "газированный",
    "игристое",
    "светлое",
    "темное",
    "тёмное",
    "белое",
    "красное",
    "розовое",
    "сладкое",
    "полусладкое",
    "сухое",
    "полусухое",
    "тонизирующий",
    "тонизирующее",
    "марочное",
    "без",
}
STOP_WORDS = DESCRIPTOR_WORDS | {
    "chardonnay",
    "riesling",
    "merlot",
    "pinot",
    "noir",
    "blanc",
    "cabernet",
    "tempranillo",
    "sauvignon",
    "bianco",
    "rose",
    "white",
    "red",
    "veneto",
    "0",
    "л",
    "мл",
    "г",
}


def derive_supplier_from_product_name(value: object) -> str:
    """Return a best-effort supplier/brand from a readable product title."""
    words = _name_words(value)
    had_leading_product_word = False
    while words and words[0].casefold() in LEADING_PRODUCT_WORDS:
        had_leading_product_word = True
        words.pop(0)
    if len(words) < 2 and not had_leading_product_word:
        return ""
    while words and words[0].casefold() in DESCRIPTOR_WORDS:
        words.pop(0)
    result: list[str] = []
    for word in words:
        normalized = word.casefold()
        if normalized in STOP_WORDS or any(char.isdigit() for char in word):
            break
        result.append(word)
        if len(result) == 3:
            break
    return " ".join(result).strip()


def _name_words(value: object) -> list[str]:
    return re.findall(r"[A-Za-zА-Яа-яЁё]+(?:-[A-Za-zА-Яа-яЁё]+)?", str(value or ""))
