from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")

TEN_THEMES = ["healing", "activity", "foodie", "photo", "culture",
              "nature", "wellness", "festival", "family_kids", "gourmet"]

def test_theme_tab_has_ten_themes():
    for val in TEN_THEMES:
        assert f'name="theme" value="{val}"' in HTML, f"missing theme: {val}"


def test_axis_controls_present():
    for el_id in ["travel-format-select", "transport-mode-select", "pace-select"]:
        assert f'id="{el_id}"' in HTML, f"missing control: {el_id}"


def test_travel_format_options():
    for v in ["자유여행", "당일치기", "캠핑/차박", "기차여행", "패키지"]:
        assert f'value="{v}"' in HTML, f"missing travel_format option: {v}"


def test_transport_mode_options():
    for v in ["자가용", "기차/KTX", "항공", "대중교통", "렌터카"]:
        assert f'value="{v}"' in HTML, f"missing transport_mode option: {v}"


def test_pace_options():
    for v in ["빡빡", "보통", "여유"]:
        assert f'value="{v}"' in HTML, f"missing pace option: {v}"


def test_runworkflow_payload_includes_axes():
    assert "travel_format:" in HTML
    assert "transport_mode:" in HTML
    assert "pace:" in HTML
