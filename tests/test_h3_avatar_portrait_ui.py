"""E-P2 — 세로 FL2V 선택 UI 최소 연결 검사.

web/public/index.html의 I2V 단일/씬 해상도 select(i2vResolution,
i2vSceneResolution)에 576x1024 옵션 1개씩이 추가되었는지, 기존 가로
3규격과 selected 1280x704가 보존되는지, R2V h3Resolution select의 기존
5개 목록이 불변인지를 실제 HTMLParser로 확인한다. node/form·JS·CSS·
backend 재구성은 하지 않는다.
"""

import html.parser
import os
import unittest

WEB_PUBLIC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "web", "public")
)
INDEX_HTML = os.path.join(WEB_PUBLIC, "index.html")

# I2V 해상도 select — 576x1024 추가 후 expected 4개 값
I2V_SELECTIONS = ("i2vResolution", "i2vSceneResolution")
I2V_EXPECTED_VALUES = {
    "1376x768",
    "1280x704",
    "832x480",
    "576x1024",
}
I2V_EXPECTED_SELECTED = {"1280x704"}

# R2V 해상도 select — 기존 5개 목록 불변 (변경 0)
R2V_SELECTION = "h3Resolution"
R2V_EXPECTED_VALUES = {
    "1280x736",
    "1280x704",
    "960x544",
    "832x480",
    "608x352",
}
R2V_EXPECTED_SELECTED = {"608x352"}


class _SelectOptionParser(html.parser.HTMLParser):
    """select/option을 수집하는 HTMLParser.

    select 시작 시 id/name을 기록하고 내부 option의 value/selected를
    수집한다. 수집한 dict를 self.selects에 id->{"options":...}로 저장한다.
    """

    def __init__(self):
        super().__init__()
        # id -> {"values": [..], "selected": [..]}
        self.selects = {}
        self._current_id = None
        self._current_name = None
        # 옵션 속성을 pending으로 모아 option 태그가 완전히 끝나면 저장
        self._pending = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select":
            self._current_id = attrs.get("id")
            self._current_name = attrs.get("name")
            self.selects[self._current_id] = {"values": [], "selected": []}
        elif tag == "option" and self._current_id is not None:
            self._pending = {
                "value": attrs.get("value"),
                "selected": "selected" in attrs,
            }

    def handle_endtag(self, tag):
        if tag == "option" and self._pending is not None:
            entry = self.selects[self._current_id]
            entry["values"].append(self._pending["value"])
            if self._pending["selected"]:
                entry["selected"].append(self._pending["value"])
            self._pending = None
        elif tag == "select":
            self._current_id = None
            self._current_name = None

    def handle_startendtag(self, tag, attrs):
        # self-closing option/select 처리 (HTML에서는 드묾)
        self.handle_starttag(tag, attrs)
        if tag == "option":
            self.handle_endtag("option")
        elif tag == "select":
            self.handle_endtag("select")


def parse_selects(html_text):
    parser = _SelectOptionParser()
    parser.feed(html_text)
    parser.close()
    return parser.selects


def load_index_html():
    with open(INDEX_HTML, encoding="utf-8") as f:
        return f.read()


class H3AvatarPortraitUiTest(unittest.TestCase):
    """E-P2 T7 — I2V 해상도 select에 세로 576x1024 옵션 연결."""

    def test_index_html_exists(self):
        self.assertTrue(
            os.path.isfile(INDEX_HTML),
            f"index.html not found at {INDEX_HTML}",
        )

    def _selects(self):
        return parse_selects(load_index_html())

    def test_i2v_selects_present(self):
        selects = self._selects()
        for sel in I2V_SELECTIONS:
            self.assertIn(
                sel,
                selects,
                f"I2V select id={sel} not found in index.html",
            )

    def test_i2v_scene_resolution_has_portrait_option(self):
        """i2vSceneResolution에 576x1024 옵션 1개 존재 (RED 핵심)."""
        selects = self._selects()
        self.assertIn("i2vSceneResolution", selects)
        values = selects["i2vSceneResolution"]["values"]
        self.assertEqual(
            values.count("576x1024"),
            1,
            f"i2vSceneResolution must contain 576x1024 exactly once, got values={values}",
        )

    def test_i2v_single_resolution_has_portrait_option(self):
        """i2vResolution에 576x1024 옵션 1개 존재."""
        selects = self._selects()
        self.assertIn("i2vResolution", selects)
        values = selects["i2vResolution"]["values"]
        self.assertEqual(
            values.count("576x1024"),
            1,
            f"i2vResolution must contain 576x1024 exactly once, got values={values}",
        )

    def test_i2v_exact_value_set_preserved(self):
        """I2V 양쪽 select의 값 집합이 expected 4개와 정확히 일치."""
        selects = self._selects()
        for sel in I2V_SELECTIONS:
            values = set(selects[sel]["values"])
            self.assertEqual(
                values,
                I2V_EXPECTED_VALUES,
                f"{sel} value set changed: got={values} expected={I2V_EXPECTED_VALUES}",
            )

    def test_i2v_selected_preserved(self):
        """I2V 양쪽 select의 selected가 1280x704 1개로 보존됨."""
        selects = self._selects()
        for sel in I2V_SELECTIONS:
            selected = selects[sel]["selected"]
            self.assertEqual(
                selected,
                list(I2V_EXPECTED_SELECTED),
                f"{sel} selected changed: got={selected} expected=1280x704",
            )
            self.assertEqual(len(selected), 1)

    def test_r2v_resolution_unchanged(self):
        """R2V h3Resolution 기존 5개 목록·selected 608x352 불변."""
        selects = self._selects()
        self.assertIn(R2V_SELECTION, selects)
        entry = selects[R2V_SELECTION]
        self.assertEqual(
            set(entry["values"]),
            R2V_EXPECTED_VALUES,
            f"R2V {R2V_SELECTION} value set changed: got={entry['values']} expected={R2V_EXPECTED_VALUES}",
        )
        self.assertEqual(len(entry["values"]), 5)
        self.assertEqual(
            set(entry["selected"]),
            R2V_EXPECTED_SELECTED,
            f"R2V {R2V_SELECTION} selected changed: got={entry['selected']}",
        )
        self.assertNotIn("576x1024", entry["values"])


if __name__ == "__main__":
    unittest.main()
