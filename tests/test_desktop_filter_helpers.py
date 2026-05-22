from launcher.desktop_filter_helpers import build_filter_option_labels, extract_filter_counts


def test_extract_filter_counts_reads_one_supported_filter() -> None:
    launcher_view = {
        "available_filter_counts": {
            "suppliers": {"Море": 7, "Океан": 5},
            "brands": {"Nord": "3"},
        }
    }

    assert extract_filter_counts(launcher_view, "suppliers") == {"Море": 7, "Океан": 5}
    assert extract_filter_counts(launcher_view, "brands") == {"Nord": 3}


def test_build_filter_option_labels_sorts_labels() -> None:
    labels = build_filter_option_labels({"Океан": 5, "Море": 7})

    assert labels == [("Море", "Море (7)"), ("Океан", "Океан (5)")]
