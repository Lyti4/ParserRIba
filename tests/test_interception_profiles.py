from utils.interception import build_interception_event, classify_route
from utils.interception_profiles import get_interception_profile


def test_pyaterochka_profile_classifies_allowed_product_api() -> None:
    profile = get_interception_profile("pyaterochka")

    route = classify_route("https://5d.5ka.ru/api/catalog/v3/products", profile=profile)

    assert route == "product_api"


def test_pyaterochka_profile_marks_external_hosts() -> None:
    profile = get_interception_profile("pyaterochka")

    route = classify_route("https://api.ipify.org/?format=json", profile=profile)

    assert route == "external"


def test_interception_event_uses_store_profile() -> None:
    event = build_interception_event(
        method="GET",
        status=200,
        url="https://api.ipify.org/?format=json",
        content_type="application/json",
        payload_text='{"ip":"203.0.113.10"}',
        profile=get_interception_profile("pyaterochka"),
    )

    assert event.route_type == "external"
    assert event.replay_candidate is False
