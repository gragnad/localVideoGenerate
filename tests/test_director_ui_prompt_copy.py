import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DirectorPromptUiContractTests(unittest.TestCase):
    def test_saved_prompt_ui_is_grouped_and_copyable(self):
        app = (ROOT / "web" / "public" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "public" / "director-prompts.css").read_text(
            encoding="utf-8"
        )
        css += (ROOT / "web" / "public" / "director-background-accordion.css").read_text(
            encoding="utf-8"
        )

        for marker in (
            "directorPromptBlock",
            "data-director-copy",
            "bindDirectorCopyButtons",
            "복사됨",
            "director-background-accordion",
            "data-director-background-row",
            "director-segment-card",
            "/director-prompts.css",
        ):
            self.assertIn(marker, app)

        for selector in (
            ".director-copy-block",
            ".director-background-accordion",
            ".director-background-row",
            ".director-segment-body",
            ".director-segment-media",
            "#directorPromptClips",
        ):
            self.assertIn(selector, css)


if __name__ == "__main__":
    unittest.main()
