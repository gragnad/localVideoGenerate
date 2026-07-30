from __future__ import annotations

import unittest

from regenerate_director_image_prompts import (
    STYLE_PREFIX,
    audit_prompt,
    reference_paths_for,
    regenerate_prompt,
)


class RegenerateDirectorImagePromptTests(unittest.TestCase):
    def test_removes_internal_and_static_boilerplate(self) -> None:
        before = (
            "High-quality stylized feature-film animation still, 16:9, "
            "1280x704. Medium static shot. Lua (CHAR_LUA) watches "
            "Young Mir (CHAR_YOUNG_MIR)."
        )
        after = regenerate_prompt(before)
        self.assertTrue(after.startswith(STYLE_PREFIX))
        self.assertNotIn("static", after)
        self.assertNotIn("CHAR_", after)
        self.assertIn("Lua watches Young Mir", after)
        self.assertEqual(audit_prompt(after), [])

        self.assertEqual(regenerate_prompt(after), after)

    def test_extracts_reference_paths_from_natural_prompt(self) -> None:
        paths = reference_paths_for(
            "Lua holds her fishing spear while Young Mir watches."
        )
        self.assertIn("RaisingaDragonSeason01/Lua.png", paths)
        self.assertIn("RaisingaDragonSeason01/YoungMir.png", paths)
        self.assertIn("RaisingaDragonSeason01/spear.png", paths)


if __name__ == "__main__":
    unittest.main()
