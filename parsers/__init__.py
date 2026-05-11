"""Parser package.

Store parsers are imported lazily by main.ParserFactory, so importing this
package should not import every store parser and fail on unrelated modules.
"""

__all__: list[str] = []
