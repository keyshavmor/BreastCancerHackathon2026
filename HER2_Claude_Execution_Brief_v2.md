# CLAUDE CODE - EXECUTION BRIEF (v2.0, HER2 scFv)

Read `HER2_Revised_Scientific_Report.md` in full. Independently check the contract, evaluate evidence from the organizer's four linked resources, and audit the existing repository https://github.com/keyshavmor/Catalyst2026Hackathon before editing code. Critique the report rather than accepting unsupported claims.

## Verbatim immutable parent sequence

```text
EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVKGRFTISADTSKNTAYLQMNSLRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSSGGGGSGGGGSGGGGSDIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSRSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK
```

Length 242; V_H 1-120, linker 121-135 (GGGGS)x3, V_L 136-242; native cysteines **22, 96, 158, 223** (one-based). SHA-256 (sequence only) `0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64`. This replaces any previous wrong claim of 244 aa.

## Organizer non-negotiables

1. Only modify this parent; >=5 amino-acid mutations vs the exact starting sequence; max length 260; preserve scFv VH-linker-VL format. Our operational choice: 242 aa, 5-8 substitutions, no linker edits, no edits to 4 native cysteines, no new cysteines.
2. Deliver **designed sequences**, **actual ipSAE score for EVERY submitted designed sequence**, and **walkthrough of methods**. Treat 50 as the requested INTERNAL proposal pool, not a guarantee of 50 fully scored submissions; aim to submit 50 only if 50 Boltz/ipSAE calculations truly complete. Prioritize a fully scored and diverse 15 if throughput is limited. Older slide says 15 team candidates tested in lab.
3. NEVER use RFdiffusion, BindCraft, BoltzGen or other de novo binders. Use Boltz-2 for complex prediction ONLY after sequence screening. NEVER cofold full HER2 ~630aa; cofold **HER2 domain IV only**, mapped and cropped from 1N8Z/P04626.
4. Do not rank solely by ipSAE, confuse ipTM or PAE proxies with ipSAE, claim an in-silico K_D, or mutate the fixed linker/disulfide cysteines. Contact organizers promptly if local GPU or Modal setup prevents scoring.

## Actions in execution order

1. Freeze parent FASTA and SHA, create strict validator, map the 1N8Z PDB chains A(light), B(heavy), C(HER2). Derive defensible domain-IV crop and confirm epitope; do NOT reuse Cetuximab/EGFR inputs or the old 241aa checks.
2. Run small smoke checks on local environments, then one HER2-domain-IV parent Boltz-2 cofold WITH full PAE and structure and external ipSAE (DunbrackLab/IPSAE: https://github.com/DunbrackLab/IPSAE). Benchmark cold load, GPU peak, per-candidate time, and MSA server overhead.
3. Implement fast candidate generation: AbLang2-guided site scan, 5-8 substitutions, structure/literature priors, diverse branches **20 H3 / 12 interface-adjacent / 10 mixed / 8 framework**. Generate at least 50 valid unique proposals by T+100 minutes. Write `internal_50_candidates.csv` / `.fasta`; ipSAE must remain null until computed.
4. ESM2-3B rerank a bounded shortlist, freeze a diverse 15 candidates as the first cofold queue. From ~T+135 to T+265 run Boltz-2 on domain IV only, completing all 15 and extending toward 50 if time allows. Apply SAME input construction, seed protocol, MSA policy, cutoffs to parent and candidates. Every scored design must have saved `.cif` and full PAE, external ipSAE and logs.
5. Export `submission_scored.csv` / `.fasta` that contain ONLY real ipSAE-complete candidates. Select and rank up to 15 lab nominees, preferably exactly 15. Independently validate mutation count, linker/cys, uniqueness, SHA, structure/PAE file existence, ipSAE finiteness and score-metric provenance. Provide `method_walkthrough.md`, runtime log, and explicit limitations.

## Time gates (300 min hard limit)

- 00-20: immutable inputs + target mapping; 20-50: smoke / parent baseline benchmark; 50-100: generation and strict QC; 100-135: ESM shortlist; 135-265: domain-IV cofold + ipSAE, 15 first then expand; 265-285: select and audit; 285-300: deliver.
- If the initial parent cannot give a valid structure/PAE/ipSAE, escalate early rather than filling fake values. If 50 scored sequences cannot fit, only submit score-complete subset. Keep 50 internal proposals separate and identify unscored ones.

## Required file tree

```text
inputs/organizer_parent_scfv.fasta
outputs/contract.yaml
outputs/residue_map.csv
outputs/internal_50_candidates.csv
outputs/internal_50_candidates.fasta
outputs/submission_scored.csv
outputs/submission_scored.fasta
outputs/top_15_scored.csv
outputs/top_15_scored.fasta
outputs/boltz_parent/
outputs/boltz_candidates/
outputs/ipSAE_provenance.csv
outputs/method_walkthrough.md
outputs/compliance_audit.json
outputs/run_manifest.json
```

Audit outputs PASS/FAIL/NOT_EVALUATED from real files. Don't claim the report has already generated 50 sequences or any ipSAE.
