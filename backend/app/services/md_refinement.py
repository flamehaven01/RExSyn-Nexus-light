"""MD Refinement Fallback Service for RExSyn Nexus v0.2.0

Triggers GROMACS short equilibration when:
- Confidence < 0.75 AND SAXS mismatch > 2σ
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class MDRefinementService:
    """GROMACS-based structure refinement for low-confidence predictions."""

    def __init__(
        self,
        confidence_threshold: float = 0.75,
        saxs_sigma_threshold: float = 2.0,
        gromacs_bin: str = "gmx"
    ):
        self.conf_threshold = confidence_threshold
        self.saxs_threshold = saxs_sigma_threshold
        self.gmx = gromacs_bin

    def should_trigger_md(
        self,
        confidence: float,
        saxs_chi2: float,
        saxs_baseline: float = 1.0
    ) -> bool:
        """
        Determine if MD refinement should be triggered.

        Args:
            confidence: Overall prediction confidence (0-1)
            saxs_chi2: SAXS χ² value
            saxs_baseline: Baseline SAXS χ² for σ calculation

        Returns:
            True if refinement needed
        """
        saxs_sigma = (saxs_chi2 - saxs_baseline) / (saxs_baseline * 0.5)
        
        return (
            confidence < self.conf_threshold
            and saxs_sigma > self.saxs_threshold
        )

    def run_short_equilibration(
        self,
        pdb_path: Path,
        output_dir: Path,
        steps: int = 10000
    ) -> Dict[str, Any]:
        """
        Run GROMACS short equilibration (10k steps).

        Args:
            pdb_path: Input PDB file
            output_dir: Output directory for refined structure
            steps: Number of MD steps (default: 10000)

        Returns:
            Refinement result with refined PDB path and metrics
        """
        logger.info(f"Starting MD refinement for {pdb_path} with {steps} steps")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Generate topology
        top_file = output_dir / "topol.top"
        gro_file = output_dir / "conf.gro"

        logger.info("Step 1: Generating topology with pdb2gmx")
        try:
            subprocess.run(
                [self.gmx, "pdb2gmx", "-f", str(pdb_path), "-o", str(gro_file),
                 "-p", str(top_file), "-ff", "amber99sb-ildn", "-water", "tip3p"],
                check=True,
                capture_output=True,
                timeout=60
            )
            logger.info("Topology generation successful")
        except subprocess.CalledProcessError as e:
            logger.error(f"pdb2gmx failed: {e.stderr.decode()}")
            return {
                "success": False,
                "error": f"pdb2gmx failed: {e.stderr.decode()}",
                "refined_pdb": None
            }
        except subprocess.TimeoutExpired:
            logger.error("pdb2gmx timeout after 60s")
            return {
                "success": False,
                "error": "pdb2gmx timeout after 60s",
                "refined_pdb": None
            }

        # Step 2: Energy minimization
        em_mdp = self._generate_em_mdp(output_dir)
        em_tpr = output_dir / "em.tpr"
        em_gro = output_dir / "em.gro"

        logger.info("Step 2: Running energy minimization")
        try:
            subprocess.run(
                [self.gmx, "grompp", "-f", str(em_mdp), "-c", str(gro_file),
                 "-p", str(top_file), "-o", str(em_tpr)],
                check=True,
                capture_output=True,
                timeout=30
            )
            subprocess.run(
                [self.gmx, "mdrun", "-v", "-deffnm", str(output_dir / "em")],
                check=True,
                capture_output=True,
                timeout=300
            )
            logger.info("Energy minimization completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Energy minimization failed: {e.stderr.decode()}")
            return {
                "success": False,
                "error": f"Energy minimization failed: {e.stderr.decode()}",
                "refined_pdb": None
            }
        except subprocess.TimeoutExpired:
            logger.error("Energy minimization timeout")
            return {
                "success": False,
                "error": "Energy minimization timeout",
                "refined_pdb": None
            }

        # Step 3: Short equilibration (10k steps)
        eq_mdp = self._generate_eq_mdp(output_dir, steps)
        eq_tpr = output_dir / "eq.tpr"
        eq_gro = output_dir / "eq.gro"

        logger.info(f"Step 3: Running equilibration ({steps} steps)")
        try:
            subprocess.run(
                [self.gmx, "grompp", "-f", str(eq_mdp), "-c", str(em_gro),
                 "-p", str(top_file), "-o", str(eq_tpr)],
                check=True,
                capture_output=True,
                timeout=30
            )
            subprocess.run(
                [self.gmx, "mdrun", "-v", "-deffnm", str(output_dir / "eq")],
                check=True,
                capture_output=True,
                timeout=600
            )
            logger.info("Equilibration completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Equilibration failed: {e.stderr.decode()}")
            return {
                "success": False,
                "error": f"Equilibration failed: {e.stderr.decode()}",
                "refined_pdb": None
            }
        except subprocess.TimeoutExpired:
            logger.error("Equilibration timeout")
            return {
                "success": False,
                "error": "Equilibration timeout",
                "refined_pdb": None
            }

        # Step 4: Convert back to PDB
        refined_pdb = output_dir / "refined.pdb"
        logger.info("Step 4: Converting final structure to PDB")
        try:
            subprocess.run(
                [self.gmx, "editconf", "-f", str(eq_gro), "-o", str(refined_pdb)],
                check=True,
                capture_output=True,
                timeout=30
            )
            logger.info(f"MD refinement completed successfully: {refined_pdb}")
        except subprocess.CalledProcessError as e:
            logger.error(f"PDB conversion failed: {e.stderr.decode()}")
            return {
                "success": False,
                "error": f"PDB conversion failed: {e.stderr.decode()}",
                "refined_pdb": None
            }
        except subprocess.TimeoutExpired:
            logger.error("PDB conversion timeout")
            return {
                "success": False,
                "error": "PDB conversion timeout",
                "refined_pdb": None
            }

        return {
            "success": True,
            "refined_pdb": str(refined_pdb),
            "steps_completed": steps,
            "energy_minimized": True,
            "equilibrated": True
        }

    def _generate_em_mdp(self, output_dir: Path) -> Path:
        """Generate GROMACS energy minimization MDP file."""
        mdp_path = output_dir / "em.mdp"
        mdp_content = """
; Energy minimization
integrator  = steep
emtol       = 1000.0
emstep      = 0.01
nsteps      = 5000
nstlist     = 10
cutoff-scheme = Verlet
coulombtype = PME
rcoulomb    = 1.0
rvdw        = 1.0
pbc         = xyz
"""
        mdp_path.write_text(mdp_content)
        return mdp_path

    def _generate_eq_mdp(self, output_dir: Path, steps: int) -> Path:
        """Generate GROMACS equilibration MDP file."""
        mdp_path = output_dir / "eq.mdp"
        mdp_content = f"""
; Short equilibration
integrator  = md
dt          = 0.002
nsteps      = {steps}
nstlist     = 10
cutoff-scheme = Verlet
coulombtype = PME
rcoulomb    = 1.0
rvdw        = 1.0
tcoupl      = V-rescale
tc-grps     = Protein Non-Protein
tau_t       = 0.1 0.1
ref_t       = 300 300
pcoupl      = no
pbc         = xyz
gen_vel     = yes
gen_temp    = 300
gen_seed    = -1
"""
        mdp_path.write_text(mdp_content)
        return mdp_path
