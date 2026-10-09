#!/usr/bin/env python3
"""AICC integration smoke for the vendored Stormy-drawing plotting skill.

All generated test plots live in a disposable temp folder; no Arial fonts
are distributed. The source snapshots are checked against pinned Git blobs.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "tools" / "plotting"
INIT = SKILL / "scripts" / "init_figure.py"
SOURCE_BLOBS = {
    "SKILL.md": "cb1a406dc24c2e772077ca506ca108e3750ba9f7",
    "examples/demo_all_types.py": "56ee1dac7fa9e593c76626baf019b2e61dfab605",
    "references/figure-types.md": "1df9b851cc98214681169892cd2ca44eaf0a3730",
    "references/setup.md": "ed3e221d18001700193b454ccfc9c180dd94be66",
    "references/structures.md": "1a19fc486f47281acf1ac1daa388da3279d053a0",
    "scripts/init_figure.py": "d9ea41dbc67941ba66e6ac7156c69af5a0df61af",
    "scripts/pubstyle.py": "f9199c874278ba444cc47af2325b675c973493d8",
    "templates/README_template.md": "212c54fd5e1bd66d98b066940470b7f2f897dd5e",
    "templates/plot_template.py": "dd0350a6c1eeda0c65773786abf66900feafdaaa",
    "UPSTREAM_LICENSE": "95b385987e08a14126b6ef5f4f36c4a108418187",
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class VendoredPlottingSkill(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        self.project.mkdir()

    def run_init(self, *args):
        return subprocess.run([sys.executable, str(INIT), *map(str, args)],
                              capture_output=True, text=True, check=False)

    def test_copy_is_exact_pinned_upstream(self):
        for file, sha in SOURCE_BLOBS.items():
            with self.subTest(file=file):
                self.assertEqual(git_blob_sha((SKILL / file).read_bytes()), sha)
        self.assertIn("MIT License", (SKILL / "UPSTREAM_LICENSE").read_text())
        self.assertIn('STYLE_VERSION = "0.5.0"', (SKILL / "scripts/pubstyle.py").read_text())

    def test_creation_stages_reproducible_figure_recipe(self):
        p = self.run_init(self.project, "Li2S_NEB_Barrier")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        folder = self.project / "figures/001_Li2S_NEB_Barrier"
        for name in ("plot.py", "README.md"):
            self.assertTrue((folder/name).is_file(), name)
        self.assertTrue((folder/"archive").is_dir())
        self.assertTrue((self.project/"figures/_style/pubstyle.py").is_file())
        self.assertEqual((self.project/"figures/_style/colors.json").read_text().strip(), "{}")
        second = self.run_init(self.project, "Li2S_DOS")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertTrue((self.project/"figures/002_Li2S_DOS/plot.py").is_file())

    def test_style_upgrade_archives_without_resetting_colors(self):
        self.assertEqual(self.run_init(self.project, "Temporary").returncode, 0)
        style = self.project / "figures/_style"
        (style/"pubstyle.py").write_text("# old style\n")
        (style/"colors.json").write_text('{"element": {"Li": "#111111"}}\n')
        run = self.run_init("--update-style", self.project)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("UPDATED", run.stdout)
        self.assertIn('STYLE_VERSION = "0.5.0"', (style/"pubstyle.py").read_text())
        self.assertEqual((style/"colors.json").read_text().strip(),
                         '{"element": {"Li": "#111111"}}')
        self.assertEqual(len(list((style/"archive").glob("pubstyle_unversioned_*.py"))), 1)
        repeat = self.run_init("--update-style", self.project)
        self.assertEqual(repeat.returncode, 0, repeat.stderr)
        self.assertIn("up to date", repeat.stdout)

    def test_one_reproducible_figure_exports_and_checks(self):
        try:
            from matplotlib import font_manager
            import PIL.Image  # noqa: F401
        except ImportError:
            self.skipTest("plotting dependencies absent")
        names = {entry.name for entry in font_manager.fontManager.ttflist}
        if not names.intersection({"Arial", "Liberation Sans"}):
            self.skipTest("neither final Arial nor draft stand-in installed")
        self.assertEqual(self.run_init(self.project, "Test_Curve").returncode, 0)
        folder = self.project / "figures/001_Test_Curve"
        script = (folder/"plot.py")
        script.write_text(
            "import sys\nfrom pathlib import Path\n"
            "HERE=Path(__file__).resolve().parent\n"
            "sys.path.insert(0,str(HERE.parent/'_style'))\n"
            "import pubstyle as ps\n"
            "ps.apply()\n"
            "fig,ax=ps.new_figure('standard')\n"
            "ax.plot([0,1,2],[0.1,0.4,0.7], color=ps.CATEGORICAL[0])\n"
            "ax.set_xlabel('Time (ps)')\nax.set_ylabel('MSD (angstrom squared)')\n"
            "ps.nice_limits(ax,0.7)\n"
            "ps.save(fig,HERE.name,HERE)\n"
        )
        env = os.environ.copy()
        env.update({"PUBSTYLE_ALLOW_STANDIN": "1", "MPLBACKEND": "Agg"})
        result = subprocess.run([sys.executable, str(script)], cwd=folder, env=env,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        outputs = [".png","_transparent.png",".pdf",".svg",".tif","_checks.txt"]
        for extension in outputs:
            file = folder / ("001_Test_Curve" + extension)
            self.assertTrue(file.is_file() and file.stat().st_size>0, str(file))
        from PIL import Image
        with Image.open(folder/"001_Test_Curve.tif") as img:
            self.assertEqual(img.mode, "RGB")
            self.assertEqual(img.info["compression"], "tiff_lzw")
            self.assertEqual(round(img.info["dpi"][0]), 1200)
        result_text = (folder/"001_Test_Curve_checks.txt").read_text()
        self.assertNotIn("FAIL", result_text)
        self.assertIn("0.5.0", result_text)


if __name__ == "__main__":
    unittest.main()
