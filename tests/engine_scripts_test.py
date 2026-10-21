#!/usr/bin/env python3
"""Smoke tests for the engine parsers and VASP pre-submission checks.

Small synthetic outputs only: they pin exit codes and the key numbers each
script reports, so a regex change cannot silently break them.

Run: python tests/engine_scripts_test.py
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "tools"


def run(script, *args, cwd=None):
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True, cwd=cwd, check=False)


def outcar(*, finished=True, converged=True, nsw=10, nelm=60, scf_steps=(12, 8),
           forces=((0.0, 0.0, 0.0), (0.012, 0.012, 0.012))):
    lines = [f"   NELM   =     {nelm};   NELMIN=  2; NELMDL= -5",
             f"   NSW    =     {nsw}    number of steps for IOM",
             "   EDIFFG = -.2E-01   stopping-criterion for IOM"]
    for ionic, n in enumerate(scf_steps, 1):
        lines += [f"--------------------------------------- Iteration      {ionic}(   {k})  ---"
                  for k in range(1, n + 1)]
    lines += [" POSITION                                       TOTAL-FORCE (eV/Angst)",
              " -----------------------------------------------------------------------------------"]
    for i, (fx, fy, fz) in enumerate(forces):
        lines.append(f"      {i*1.5:.5f}      0.00000      0.00000        {fx:.6f}     {fy:.6f}     {fz:.6f}")
    lines += [" -----------------------------------------------------------------------------------",
              "  free  energy   TOTEN  =       -10.52341234 eV",
              "  energy  without entropy=      -10.51000000  energy(sigma->0) =      -10.51500000"]
    if converged and nsw:
        lines.append(" reached required accuracy - stopping structural energy minimisation")
    if finished:
        lines.append(" General timing and accounting informations for this job:")
    return "\n".join(lines) + "\n"


class VaspParser(unittest.TestCase):
    script = T / "vasp/scripts/parse_vasp.py"

    def check(self, text, *flags):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "OUTCAR").write_text(text)
            return run(self.script, d, *flags)

    def test_converged_relaxation(self):
        r = self.check(outcar())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("-10.515000 eV (E0", r.stdout)

    def test_force_is_per_atom_magnitude(self):
        r = self.check(outcar())
        self.assertIn("max |F|:       0.0208 eV/A", r.stdout)   # sqrt(3)*0.012, not 0.012

    def test_crashed_run(self):
        r = self.check(outcar(finished=False))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no timing footer", r.stdout)

    def test_relaxation_not_converged(self):
        r = self.check(outcar(converged=False))
        self.assertEqual(r.returncode, 1)
        self.assertIn("without reaching required accuracy", r.stdout)

    def test_static_scf_hit_nelm(self):
        r = self.check(outcar(nsw=0, nelm=8, scf_steps=(8,)))
        self.assertEqual(r.returncode, 1)
        self.assertIn("static SCF hit NELM=8", r.stdout)

    def test_missing_outcar(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(run(self.script, d).returncode, 2)


LOCK = textwrap.dedent("""\
    # Locked parameters
    ## pbe
    - ENCUT = 520
    - PREC = Accurate
    - GGA = PE
    - ISMEAR = 0
    - SIGMA = 0.05
    - KSPACING_MAX = 0.30
    - KPOINTS_MODE = Gamma
    - POTCAR = Na_pv S
    - POTCAR_FAMILY = PAW_PBE
    """)
POSCAR = "Na2S\n1.0\n6.5 0 0\n0 6.5 0\n0 0 6.5\nNa S\n8 4\nDirect\n" + "0 0 0\n" * 12
POTCAR = "  TITEL  = PAW_PBE Na_pv 19Sep2006\n  TITEL  = PAW_PBE S 06Sep2000\n"


class LockedParams(unittest.TestCase):
    script = T / "vasp/scripts/check_locked_params.py"

    def rundir(self, d, incar, kpoints="Auto\n0\nGamma\n6 6 6\n"):
        run_dir = Path(d, "run")
        run_dir.mkdir()
        (run_dir / "INCAR").write_text(incar)
        (run_dir / "KPOINTS").write_text(kpoints)
        (run_dir / "POSCAR").write_text(POSCAR)
        (run_dir / "POTCAR").write_text(POTCAR)
        Path(d, "locked_parameters.md").write_text(LOCK)
        return run_dir

    GOOD = "ENCUT = 520\nPREC = Accurate\nGGA = PE\nISMEAR = 0\nSIGMA = 0.05\nIBRION = 2\n"

    def test_matching_run_passes(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(self.script, self.rundir(d, self.GOOD), "--lock", Path(d, "locked_parameters.md"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_changed_smearing_fails(self):
        with tempfile.TemporaryDirectory() as d:
            bad = self.GOOD.replace("SIGMA = 0.05", "SIGMA = 0.2")
            r = run(self.script, self.rundir(d, bad), "--lock", Path(d, "locked_parameters.md"))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("SIGMA", r.stdout)

    def test_unlocked_physics_tag_fails(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(self.script, self.rundir(d, self.GOOD + "LHFCALC = .TRUE.\n"),
                    "--lock", Path(d, "locked_parameters.md"))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("LHFCALC", r.stdout)

    def test_too_coarse_kmesh_fails(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(self.script, self.rundir(d, self.GOOD, "Auto\n0\nGamma\n1 1 1\n"),
                    "--lock", Path(d, "locked_parameters.md"))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


class InputPreflight(unittest.TestCase):
    """check_inputs.py: lock file found automatically, MP POTCAR labels flagged."""
    script = T / "vasp/scripts/check_inputs.py"

    def setup_run(self, d, incar=LockedParams.GOOD, potcar=POTCAR, lock=True):
        run_dir = Path(d, "project", "calc", "run")
        run_dir.mkdir(parents=True)
        (run_dir / "INCAR").write_text(incar)
        (run_dir / "KPOINTS").write_text("Auto\n0\nGamma\n6 6 6\n")
        (run_dir / "POSCAR").write_text(POSCAR)
        (run_dir / "POTCAR").write_text(potcar)
        if lock:
            Path(d, "project", "locked_parameters.md").write_text(LOCK)
        return run_dir

    def test_lock_in_parent_folder_is_used(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(self.script, self.setup_run(d))
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("lock: RESULT: OK", r.stdout)

    def test_lock_mismatch_fails_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            rd = self.setup_run(d, incar=LockedParams.GOOD.replace("ENCUT = 520", "ENCUT = 400"))
            r = run(self.script, rd)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("ENCUT", r.stdout)
            self.assertEqual(run(self.script, rd, "--no-lock").returncode, 0)

    def test_no_lock_is_noted_not_failed(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(self.script, self.setup_run(d, lock=False))
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("no locked_parameters.md found", r.stdout)

    def test_non_mp_potcar_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            rd = self.setup_run(d, potcar=POTCAR.replace("Na_pv", "Na"), lock=False)
            r = run(self.script, rd)
            self.assertEqual(r.returncode, 0, r.stdout)          # a warning, not a failure
            self.assertIn("Na (MP: Na_pv)", r.stdout)


class DistanceCheck(unittest.TestCase):
    script = ROOT / "tools/structure-prep/scripts/check_distances.py"
    LI2S = ("Li2S\n1.0\n5.7 0 0\n0 5.7 0\n0 0 5.7\nLi S\n2 2\nDirect\n"
            "0.25 0.25 0.25\n0.75 0.75 0.75\n0 0 0\n0.5 0.5 0.5\n")

    def write(self, d, name, text):
        p = Path(d, name)
        p.write_text(text)
        return p

    def test_clean_collision_and_reference(self):
        with tempfile.TemporaryDirectory() as d:
            ok = self.write(d, "ok.vasp", self.LI2S)
            r = run(self.script, ok)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("1.652", r.stdout)                     # 0.7 x Pyykko(Li+S)
            bad = self.write(d, "bad.vasp", self.LI2S.replace("0.75 0.75 0.75", "0.05 0.0 0.0"))
            self.assertEqual(run(self.script, bad).returncode, 1)
            squeezed = self.write(d, "sq.vasp", self.LI2S.replace("0.25 0.25 0.25", "0.18 0.18 0.18"))
            r = run(self.script, squeezed, "--reference", ok)
            self.assertEqual(r.returncode, 3, r.stdout)          # yellow: Li-S much shorter than bulk


CP2K_OK = textwrap.dedent("""\
     *** SCF run converged in    14 steps ***
     ENERGY| Total FORCE_EVAL ( QS ) energy [a.u.]:          -34.123456789012
     ATOMIC FORCES in [a.u.]
     # Atom   Kind   Element          X              Y              Z
          1      1      Li          0.00100000     0.00000000     0.00000000
          2      2      S          -0.00100000     0.00000000     0.00000000
     SUM OF ATOMIC FORCES           0.00000000     0.00000000     0.00000000     0.00000000
     The number of warnings for this run is : 0
      PROGRAM ENDED AT                 2026-10-20 12:00:00.000
    """)


class OtherParsers(unittest.TestCase):
    def file(self, d, name, text):
        p = Path(d, name)
        p.write_text(text)
        return p

    def test_cp2k_converged_and_crashed(self):
        script = T / "cp2k/scripts/parse_cp2k.py"
        with tempfile.TemporaryDirectory() as d:
            r = run(script, self.file(d, "ok.out", CP2K_OK))
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("-34.123456789012 hartree", r.stdout)
            r = run(script, self.file(d, "crash.out", CP2K_OK.replace("PROGRAM ENDED AT", "")))
            self.assertEqual(r.returncode, 2, r.stdout)

    def test_gaussian_normal_and_error(self):
        script = T / "gaussian/scripts/parse_gaussian.py"
        log = (" #p B3LYP/6-31G(d) sp\n"
               " SCF Done:  E(RB3LYP) =  -76.4089535     A.U. after   10 cycles\n"
               " Normal termination of Gaussian 16 at Mon Oct 20 12:00:00 2026.\n")
        with tempfile.TemporaryDirectory() as d:
            r = run(script, self.file(d, "ok.log", log))
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("-76.4089535", r.stdout)
            bad = log.replace(" Normal termination of Gaussian 16 at Mon Oct 20 12:00:00 2026.\n",
                              " Error termination via Lnk1e in /g16/l502.exe at Mon Oct 20.\n")
            self.assertEqual(run(script, self.file(d, "bad.log", bad)).returncode, 2)

    def test_orca_normal_termination(self):
        script = T / "orca/scripts/parse_orca.py"
        out = ("                                 Program Version 6.1.0 -  RELEASE  -\n"
               "               *****************************************************\n"
               "               *                     SUCCESS                       *\n"
               "               *           SCF CONVERGED AFTER  12 CYCLES          *\n"
               "               *****************************************************\n"
               "FINAL SINGLE POINT ENERGY       -76.326848000000\n"
               "                             ****ORCA TERMINATED NORMALLY****\n")
        with tempfile.TemporaryDirectory() as d:
            r = run(script, self.file(d, "job.out", out))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("-76.326848", r.stdout)
            r = run(script, self.file(d, "cut.out", out.replace("****ORCA TERMINATED NORMALLY****", "")))
            self.assertEqual(r.returncode, 2, r.stdout)

    def test_lammps_segments_and_lost_atoms(self):
        script = T / "lammps/scripts/parse_lammps.py"
        log = ("Step Temp TotEng Press\n"
               "0 300 -100.0 1.0\n"
               "100 301 -100.001 1.5\n"
               "Loop time of 1.0 on 1 procs for 100 steps with 64 atoms\n")
        with tempfile.TemporaryDirectory() as d:
            r = run(script, self.file(d, "log.lammps", log))
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("steps 0 -> 100", r.stdout)
            r = run(script, self.file(d, "lost.lammps", log + "ERROR: Lost atoms: original 64 current 63\n"))
            self.assertEqual(r.returncode, 2, r.stdout)


if __name__ == "__main__":
    unittest.main()
