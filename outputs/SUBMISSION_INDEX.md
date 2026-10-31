# Submission index

Everything the execution brief asks for, and where it is.

| Artifact | Present | What it is |
| --- | :-: | --- |
| `inputs/organizer_parent_scfv.fasta` | yes | frozen organizer parent, SHA-256 verified |
| `outputs/contract.yaml` | yes | rules, parent, target definition and checksums |
| `outputs/residue_map.csv` | yes | per-residue scFv <-> 1N8Z mapping with contact classes |
| `outputs/internal_50_candidates.csv` | yes | curated 50-proposal pool |
| `outputs/submission_scored.csv` | yes | every design with a genuine external ipSAE |
| `outputs/ranked_winners.csv` | yes | ranked 50 with full statistics (also .xlsx/.fasta) |
| `outputs/top_15_scored.csv` | yes | lab nominations |
| `outputs/boltz_parent/` | yes | parent structure + PAE, representative seed |
| `outputs/boltz_candidates/` | yes | one structure + PAE per submitted design |
| `outputs/ipSAE_provenance.csv` | yes | ipSAE script commit, cutoffs, chain order, paths |
| `outputs/method_walkthrough.md` | yes | the design-method deliverable |
| `outputs/compliance_audit.json` | yes | PASS/FAIL checks computed from real files |
| `outputs/organizer_compliance.json` | yes | the organizer's recap, verified point by point |
| `outputs/run_manifest.json` | yes | commit, weights, counts, claim boundary |
| `outputs/figures/` | yes | nine campaign figures |
| `outputs/gifs/` | yes | rotating 3D animations, parent and winners |
| `outputs/binders/` | yes | per-design package: sequence, structure, PAE, contacts |
| `outputs/reports/` | yes | local, Modal and final-designs reports |
| `outputs/slides_assets/` | yes | presentation bundle incl. the Lovable prompt |

Parent structure: `outputs/boltz_parent/parent.cif` (+ `parent_pae.npz`), representative of its replicate seeds.
Candidate structures: 50 in `outputs/boltz_candidates/`, one per submitted design, each with its PAE and a MANIFEST.csv row.

**Claim boundary.** ipSAE is interface confidence from a structure predictor, not a binding affinity. No K_D is predicted anywhere in this submission.
