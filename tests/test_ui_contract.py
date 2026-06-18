from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")

TEN_THEMES = ["healing", "activity", "foodie", "photo", "culture",
              "nature", "wellness", "festival", "family_kids", "gourmet"]

def test_theme_tab_has_ten_themes():
    for val in TEN_THEMES:
        assert f'name="theme" value="{val}"' in HTML, f"missing theme: {val}"
