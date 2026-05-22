from utils.catalog_discovery import summarize_catalog_discovery


def test_catalog_discovery_extracts_region_and_pagination_evidence() -> None:
    html = """
    <html>
      <head>
        <meta name="csrf-token" content="token">
      </head>
      <body>
        <p>Выберите ваш регион</p>
        <a href="https://www.verno-info.ru/products">Каталог</a>
        <a href="https://www.verno-info.ru/products?page=2">2</a>
      </body>
    </html>
    """

    summary = summarize_catalog_discovery(
        site_url="https://www.verno-info.ru/products",
        final_url="https://www.verno-info.ru/products",
        status_code=200,
        html=html,
    )

    assert summary.reachable is True
    assert summary.products_path_seen is True
    assert summary.pagination_hint is True
    assert summary.region_hint is True
    assert summary.csrf_meta_detected is True
    assert summary.surface_type == "region_gate"


def test_catalog_discovery_separates_category_and_product_links() -> None:
    html = """
    <html>
      <body>
        <a href="https://shop.example/catalog/fish">Рыба</a>
        <a href="https://shop.example/products/salmon-123">Лосось</a>
        <a href="https://shop.example/products/tuna-456">Тунец</a>
      </body>
    </html>
    """

    summary = summarize_catalog_discovery(
        site_url="https://shop.example/",
        final_url="https://shop.example/",
        status_code=200,
        html=html,
    )

    assert summary.surface_type == "category_tree"
    assert len(summary.category_links) == 1
    assert len(summary.product_links) == 2


def test_catalog_discovery_detects_pdf_flipbook_surface() -> None:
    html = """
    <html>
      <body>
        <div data-path="https://www.verno-info.ru/storage/catalog.pdf"></div>
        <script src="/assets/verniy-flip/pdf.min.js"></script>
        <script src="/assets/verniy-flip/3dflipbook.min.js"></script>
      </body>
    </html>
    """

    summary = summarize_catalog_discovery(
        site_url="https://www.verno-info.ru/products",
        final_url="https://www.verno-info.ru/products",
        status_code=200,
        html=html,
    )

    assert summary.surface_type == "pdf_flipbook"
    assert len(summary.documents) == 1
    assert summary.documents[0].kind == "pdf"


def test_catalog_discovery_detects_blocked_surface() -> None:
    summary = summarize_catalog_discovery(
        site_url="https://www.auchan.ru/catalog",
        final_url="https://www.auchan.ru/catalog",
        status_code=401,
        html="<html><body>Unauthorized</body></html>",
    )

    assert summary.surface_type == "blocked"
    assert summary.blocked_hint is True


def test_catalog_discovery_detects_challenge_surface() -> None:
    summary = summarize_catalog_discovery(
        site_url="https://shop.example/catalog",
        final_url="https://shop.example/catalog",
        status_code=403,
        html="<html><body>Cloudflare challenge captcha</body></html>",
    )

    assert summary.surface_type == "challenge"
    assert summary.challenge_hint is True


def test_catalog_discovery_deduplicates_mixed_evidence() -> None:
    html = """
    <html>
      <body>
        <a href="/category/fish">Рыба</a>
        <a href="/category/fish">Рыба</a>
        <a href="/products/salmon-123">Лосось</a>
        <a href="/products/salmon-123">Лосось</a>
        <script>fetch('/api/catalog')</script>
      </body>
    </html>
    """

    summary = summarize_catalog_discovery(
        site_url="https://shop.example/",
        final_url="https://shop.example/",
        status_code=200,
        html=html,
    )

    assert len(summary.category_links) == 1
    assert len(summary.product_links) == 1
    assert len(summary.api_hints) >= 1


def test_catalog_discovery_excludes_promo_and_account_category_noise() -> None:
    html = """
    <html>
      <body>
        <a href="/category/fish">Рыба</a>
        <a href="/category/seafood">Морепродукты</a>
        <a href="/category/skidki">Скидки</a>
        <a href="/catalog/brands">Бренды</a>
        <a href="/catalog/novinki">Новинки</a>
        <a href="/account/profile">Профиль</a>
      </body>
    </html>
    """

    summary = summarize_catalog_discovery(
        site_url="https://shop.example/",
        final_url="https://shop.example/",
        status_code=200,
        html=html,
    )

    assert [item.url for item in summary.category_links] == [
        "https://shop.example/category/fish",
        "https://shop.example/category/seafood",
    ]


def test_catalog_discovery_excludes_external_ad_and_under_search_category_noise() -> None:
    html = """
    <html>
      <body>
        <a href="/category/rybnye">Рыба, икра, морепродукты</a>
        <a href="/category/fruit?from=under_search">Фрукты</a>
        <a href="/category/promo?erid=123">Реклама special</a>
        <a href="https://www.rustore.ru/catalog/app/www.metro.com"></a>
      </body>
    </html>
    """

    summary = summarize_catalog_discovery(
        site_url="https://online.metro-cc.ru/",
        final_url="https://online.metro-cc.ru/",
        status_code=200,
        html=html,
    )

    assert [item.url for item in summary.category_links] == [
        "https://online.metro-cc.ru/category/rybnye",
    ]
