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


def test_presets_defined():
    for label in ["미식 자유여행", "캠핑 자연", "가족 휴양", "인생샷 도시", "축제·이벤트", "기차 여유", "직접 설정"]:
        assert label in HTML, f"missing preset: {label}"
    assert 'id="preset-grid"' in HTML
    assert "function applyPreset" in HTML
    assert "function renderPresets" in HTML


def test_radius_token_defined():
    assert "--radius:" in HTML


def test_calm_selection_color_present():
    assert "#f1f5f9" in HTML


def test_no_preset_emoji():
    for emoji in ["🍞", "🏕️", "♨️", "📸", "🎏", "🚄", "⚙️"]:
        assert emoji not in HTML, f"preset emoji still present: {emoji}"


def test_ui_renders_verification_report():
    assert "verification_report" in HTML
    assert "function renderVerificationReport" in HTML


def test_recommend_section_matches_form_style():
    # budget-finder uses the same control-panel layout and chip style as the rest
    assert 'class="control-panel" id="recommend-section"' in HTML
    assert 'id="rec-themes" class="checkbox-grid"' in HTML
    assert 'class="archive-section" id="recommend-section"' not in HTML


def test_local_plans_helper_present():
    assert "onesown_local_plans" in HTML
    assert "const LocalPlans" in HTML
    assert "crypto.randomUUID" in HTML


def test_guest_save_branch_present():
    assert "LocalPlans.save" in HTML
    assert "이 기기에 저장됨" in HTML
