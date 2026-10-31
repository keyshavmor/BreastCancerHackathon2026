"""Shared constants, validators and helpers for the HER2 scFv optimisation pipeline.

Every stage imports from this module so that the organizer's hard constraints are
defined exactly once. Nothing here may be relaxed by a downstream stage: the
validator is deliberately fail-closed, because the organizer rejects a submission
outright if the parent scaffold is altered.

Immutable facts (independently verified against the organizer brief, not copied
from the scientific report):

* parent length 242; SHA-256 of the bare sequence is ``PARENT_SHA256``
* V_H = 1-120, fixed ``(GGGGS)x3`` linker = 121-135, V_L = 136-242 (1-based)
* native cysteines at 22, 96, 158, 223 form the two intradomain disulfides
* 1N8Z chain A = Fab light, chain B = Fab heavy, chain C = HER2 ectodomain
* 1N8Z chain C is numbered in HER2 *mature* numbering: UniProt = mature + 22
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# Immutable parent definition
# --------------------------------------------------------------------------- #

PARENT_SEQ = (
    "EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVKGRFTISADTSKNTAYLQMNS"
    "LRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSSGGGGSGGGGSGGGGSDIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAW"
    "YQQKPGKAPKLLIYSASFLYSGVPSRFSGSRSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK"
)
PARENT_SHA256 = "0b9248c76a2b399791c47dbfa0d252b18284265f1dbca9ae8e66c0dd018c9f64"
PARENT_LEN = 242

VH_RANGE = (1, 120)       # inclusive, 1-based
LINKER_RANGE = (121, 135)
VL_RANGE = (136, 242)
LINKER_SEQ = "GGGGS" * 3
NATIVE_CYS = (22, 96, 158, 223)

CANONICAL_AA = set("ACDEFGHIKLMNPQRSTVWY")

# Organizer hard limits.
MAX_LEN = 260
MIN_MUTATIONS = 5
# Self-imposed policy (documented as *our* choice, not an organizer rule): keep
# length fixed at 242 and stay in the 5-8 substitution band so that every design
# remains a conservative edit of a sub-picomolar parent.
MAX_MUTATIONS_POLICY = 8

# --------------------------------------------------------------------------- #
# CDR definitions (Kabat), located by exact substring match on the parent
# --------------------------------------------------------------------------- #
# Using literal motifs rather than hard-coded indices means a silent change to
# the parent can never leave the CDR table pointing at the wrong residues.
CDR_MOTIFS = {
    "CDR-H1": "DTYIH",
    "CDR-H2": "RIYPTNGYTRYADSVKG",
    "CDR-H3": "WGGDGFYAMDY",
    "CDR-L1": "RASQDVNTAVA",
    "CDR-L2": "SASFLYS",
    "CDR-L3": "QQHYTTPPT",
}

# --------------------------------------------------------------------------- #
# HER2 / 1N8Z target constants
# --------------------------------------------------------------------------- #

MATURE_TO_UNIPROT_OFFSET = 22    # uniprot_pos = mature_pos + 22
HER2_DOMAIN_IV_MATURE = (489, 607)  # standard domain IV module; end = 1N8Z construct end


def sha256_seq(seq: str) -> str:
    """SHA-256 of a bare sequence string (no newline, no FASTA header)."""
    return hashlib.sha256(seq.encode()).hexdigest()


def cdr_spans(seq: str = PARENT_SEQ) -> dict[str, tuple[int, int]]:
    """Return ``{cdr_name: (start, end)}`` 1-based inclusive spans.

    Raises if a motif is absent or ambiguous, which would mean the parent is not
    the sequence this pipeline was built for.
    """
    spans: dict[str, tuple[int, int]] = {}
    for name, motif in CDR_MOTIFS.items():
        hits = [m.start() for m in re.finditer(f"(?={re.escape(motif)})", seq)]
        if len(hits) != 1:
            raise ValueError(f"{name} motif {motif!r} found {len(hits)} times, expected exactly 1")
        spans[name] = (hits[0] + 1, hits[0] + len(motif))
    return spans


def domain_of(pos: int) -> str:
    """Map a 1-based scFv position to ``VH`` / ``linker`` / ``VL``."""
    if VH_RANGE[0] <= pos <= VH_RANGE[1]:
        return "VH"
    if LINKER_RANGE[0] <= pos <= LINKER_RANGE[1]:
        return "linker"
    if VL_RANGE[0] <= pos <= VL_RANGE[1]:
        return "VL"
    raise ValueError(f"position {pos} outside 1..{PARENT_LEN}")


def cdr_of(pos: int, spans: dict[str, tuple[int, int]] | None = None) -> str:
    """Return the CDR name containing ``pos``, or ``"framework"``."""
    spans = spans or cdr_spans()
    for name, (s, e) in spans.items():
        if s <= pos <= e:
            return name
    return "framework"


# --------------------------------------------------------------------------- #
# Liability motif screening
# --------------------------------------------------------------------------- #

def count_nglyc_sequons(seq: str) -> list[int]:
    """1-based positions of N-X-S/T sequons with X != P (N-linked glycosylation)."""
    return [m.start() + 1 for m in re.finditer(r"(?=N[^P][ST])", seq)]


LIABILITY_PATTERNS = {
    # Only motifs we can screen reliably from sequence alone. Each is reported
    # as *newly introduced relative to the parent*, never as an absolute reject,
    # because the parent itself carries native motifs.
    "deamidation_NG": r"(?=NG)",
    "deamidation_NS": r"(?=NS)",
    "isomerisation_DG": r"(?=DG)",
    "isomerisation_DS": r"(?=DS)",
    "hydrolysis_DP": r"(?=DP)",
    "oxidation_free_M": r"(?=M)",
    "polybasic_KKK": r"(?=(?:[KR]{3}))",
}


def liability_counts(seq: str) -> dict[str, int]:
    """Count sequence-level developability liability motifs."""
    out = {k: len(re.findall(p, seq)) for k, p in LIABILITY_PATTERNS.items()}
    out["nglyc_sequon"] = len(count_nglyc_sequons(seq))
    return out


def new_liabilities(seq: str, parent: str = PARENT_SEQ) -> dict[str, int]:
    """Liability motifs introduced by ``seq`` relative to ``parent`` (positive only)."""
    p, c = liability_counts(parent), liability_counts(seq)
    return {k: c[k] - p[k] for k in c if c[k] > p[k]}


# --------------------------------------------------------------------------- #
# Mutation utilities
# --------------------------------------------------------------------------- #

def mutations_vs_parent(seq: str, parent: str = PARENT_SEQ) -> list[str]:
    """Return substitutions as ``['T30S', ...]`` using 1-based scFv positions.

    Only defined for equal-length sequences (our substitution-only policy).
    """
    if len(seq) != len(parent):
        raise ValueError(f"length {len(seq)} != parent {len(parent)}; indels not supported")
    return [f"{p}{i+1}{c}" for i, (p, c) in enumerate(zip(parent, seq)) if p != c]


def apply_mutations(muts: list[str] | str, parent: str = PARENT_SEQ) -> str:
    """Rebuild a sequence by applying ``['T30S', ...]`` to the parent.

    Used by the auditor to prove every submitted sequence is reconstructible from
    its recorded mutation list alone.
    """
    if isinstance(muts, str):
        muts = [m for m in re.split(r"[;,\s]+", muts.strip()) if m]
    chars = list(parent)
    for m in muts:
        mt = re.fullmatch(r"([A-Z])(\d+)([A-Z])", m.strip())
        if not mt:
            raise ValueError(f"malformed mutation token {m!r}")
        wt, pos, mut = mt.group(1), int(mt.group(2)), mt.group(3)
        if not 1 <= pos <= len(chars):
            raise ValueError(f"{m}: position out of range")
        if chars[pos - 1] != wt:
            raise ValueError(f"{m}: parent has {chars[pos-1]} at {pos}, not {wt}")
        chars[pos - 1] = mut
    return "".join(chars)


# --------------------------------------------------------------------------- #
# Fail-closed candidate validator
# --------------------------------------------------------------------------- #

@dataclass
class ValidationResult:
    """Outcome of validating one candidate. ``ok`` is True only if no failures."""
    candidate_id: str
    ok: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mutation_count: int = 0
    mutations: list[str] = field(default_factory=list)


def validate_candidate(
    seq: str,
    candidate_id: str = "?",
    parent: str = PARENT_SEQ,
    min_mut: int = MIN_MUTATIONS,
    max_mut: int = MAX_MUTATIONS_POLICY,
    allow_new_cys: bool = False,
) -> ValidationResult:
    """Check one candidate against every organizer rule and our own policy.

    Checks, in order: alphabet, length bounds, fixed-length policy, linker
    integrity, native cysteine preservation, no new cysteines, mutation-count
    band, no linker edits, and newly introduced N-glycosylation sequons.
    """
    fails: list[str] = []
    warns: list[str] = []

    bad = sorted(set(seq) - CANONICAL_AA)
    if bad:
        fails.append(f"non-canonical residues: {bad}")
    if len(seq) > MAX_LEN:
        fails.append(f"length {len(seq)} exceeds organizer max {MAX_LEN}")
    if len(seq) != len(parent):
        fails.append(f"length {len(seq)} != {len(parent)} (substitution-only policy)")
        # Remaining positional checks are meaningless on a length mismatch.
        return ValidationResult(candidate_id, False, fails, warns)

    # Linker must be byte-identical and in place.
    got_linker = seq[LINKER_RANGE[0] - 1 : LINKER_RANGE[1]]
    if got_linker != LINKER_SEQ:
        fails.append(f"linker altered: {got_linker!r} != {LINKER_SEQ!r}")

    for c in NATIVE_CYS:
        if seq[c - 1] != "C":
            fails.append(f"native cysteine {c} changed to {seq[c-1]}")

    muts = mutations_vs_parent(seq, parent)
    n = len(muts)
    if n < min_mut:
        fails.append(f"only {n} substitutions, organizer requires >= {min_mut}")
    if n > max_mut:
        fails.append(f"{n} substitutions exceeds policy max {max_mut}")

    if not allow_new_cys:
        extra_cys = [m for m in muts if m.endswith("C")]
        if extra_cys:
            fails.append(f"introduces new cysteine(s): {extra_cys}")

    # No edits anywhere in the linker span.
    linker_edits = [m for m in muts
                    if LINKER_RANGE[0] <= int(re.fullmatch(r"[A-Z](\d+)[A-Z]", m).group(1)) <= LINKER_RANGE[1]]
    if linker_edits:
        fails.append(f"linker substitutions forbidden: {linker_edits}")

    newly = new_liabilities(seq, parent)
    if newly.get("nglyc_sequon"):
        fails.append(f"introduces {newly['nglyc_sequon']} new N-X-S/T sequon(s)")
    soft = {k: v for k, v in newly.items() if k != "nglyc_sequon"}
    if soft:
        warns.append(f"new liability motifs: {soft}")

    return ValidationResult(candidate_id, not fails, fails, warns, n, muts)


def assert_parent_integrity(seq: str | None = None) -> None:
    """Abort immediately unless the frozen parent is exactly as contracted."""
    seq = PARENT_SEQ if seq is None else seq
    assert len(seq) == PARENT_LEN, f"parent length {len(seq)} != {PARENT_LEN}"
    assert sha256_seq(seq) == PARENT_SHA256, "parent SHA-256 mismatch"
    assert seq[LINKER_RANGE[0] - 1 : LINKER_RANGE[1]] == LINKER_SEQ, "linker not at 121-135"
    assert tuple(i + 1 for i, a in enumerate(seq) if a == "C") == NATIVE_CYS, "cysteine positions differ"
    assert not (set(seq) - CANONICAL_AA), "parent has non-canonical residues"


def read_fasta(path) -> dict[str, str]:
    """Minimal FASTA reader returning ``{header_id: sequence}``."""
    out, key, buf = {}, None, []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if key is not None:
                    out[key] = "".join(buf)
                key, buf = line[1:].split()[0], []
            else:
                buf.append(line)
    if key is not None:
        out[key] = "".join(buf)
    return out


def write_fasta(path, records: dict[str, str], width: int = 0) -> None:
    """Write ``{id: seq}`` to FASTA; ``width=0`` keeps each sequence on one line."""
    with open(path, "w") as fh:
        for k, v in records.items():
            fh.write(f">{k}\n")
            if width and width > 0:
                for i in range(0, len(v), width):
                    fh.write(v[i : i + width] + "\n")
            else:
                fh.write(v + "\n")


if __name__ == "__main__":
    # Self-check: run `python her2_common.py` to confirm the frozen invariants.
    assert_parent_integrity()
    spans = cdr_spans()
    print(f"parent OK: len={PARENT_LEN} sha256={PARENT_SHA256[:16]}...")
    print(f"native cysteines: {NATIVE_CYS}")
    for name, (s, e) in sorted(spans.items()):
        print(f"  {name:8s} {s:>4}-{e:<4} {PARENT_SEQ[s-1:e]}")
    print(f"parent native liabilities: {liability_counts(PARENT_SEQ)}")
    print(f"parent N-glyc sequons at: {count_nglyc_sequons(PARENT_SEQ)}")
