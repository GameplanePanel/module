"""Keep the audited x86 game images on compatible workers."""

from pathlib import Path
import unittest

import yaml


class GamePlacementTest(unittest.TestCase):
    def test_amd64_only_games_require_amd64_workers(self):
        for game in ("ark-survival-evolved", "mount-and-blade-2-bannerlord",
                     "nuclear-option", "squad", "the-isle"):
            with self.subTest(game=game):
                path = Path(__file__).parent / game / "template.yaml"
                spec = yaml.safe_load(path.read_text(encoding="utf-8"))["spec"]
                self.assertEqual(spec.get("requiredNodeArchitecture"), "amd64")


if __name__ == "__main__":
    unittest.main()
