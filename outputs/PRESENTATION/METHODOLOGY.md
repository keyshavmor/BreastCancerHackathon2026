# Presentation guide — the science, in plain language

A speaking guide for presenting this work, plus answers to the questions a
sceptical judge is most likely to ask. Numbers refer to `outputs/metrics.json`
and the reports; regenerate those before presenting so your figures match.

---

## Part 1 — The problem, in one minute

Trastuzumab (Herceptin) is an antibody that binds a protein called **HER2**,
which sits on the surface of some breast-cancer cells. It is one of the most
successful cancer drugs ever made, and it binds its target at about
**0.82 picomolar** — an extraordinarily tight grip.

We were asked to **edit** that antibody: change at least 5 of its 242 amino
acids and see whether the result still looks like a good binder.

The single most important thing to understand about this task:

> We were asked to improve something that is already close to optimal. Decades
> of pharmaceutical engineering went into this molecule. The honest prior is
> that most random edits make it **worse**, not better.

A team that reports "we improved Herceptin" from a few hours of computation
should be met with scepticism. Our aim was to produce **a diverse set of
compliant, structurally intact designs with trustworthy scores**, and to be
precise about what we can and cannot claim.

---

## Part 2 — How the pipeline works, step by step

Think of it as a funnel: cheap, fast filters first; expensive, informative ones
last. Nothing expensive runs on a candidate that a cheap test already rejected.

### Step 1 — Freeze the starting material

We wrote down the exact parent sequence and computed its **SHA-256 fingerprint**.
Every stage re-checks that fingerprint before doing anything. If one character
ever changed, the pipeline stops rather than quietly designing against the wrong
molecule.

We also verified the parts: 120 amino acids of heavy chain, a 15-residue
`GGGGS GGGGS GGGGS` linker, 107 of light chain, and four cysteines at positions
22, 96, 158 and 223 that form the internal "staples" holding the shape together.

### Step 2 — Work out where the antibody actually touches HER2

We downloaded the experimental crystal structure (**PDB 1N8Z**), which shows
trastuzumab physically bound to HER2, and measured the distance from every
antibody residue to the target.

Two things came out of this:

- **The binding site is entirely in HER2's "domain IV"**, a 119-amino-acid
  piece near the cell membrane. So we cut HER2 down to just that piece. The full
  protein is ~630 residues; using the small piece is both what the organizers
  asked for and about 5× faster, with no loss of the binding interface.
- **20 antibody residues touch HER2 directly.** Six of them sit closer than
  3.0 Å — these are almost certainly forming hydrogen bonds or salt bridges, and
  are the most likely to carry the binding energy. **We froze those six.** You do
  not casually edit the residues doing the work.

We also checked that the crop doesn't cut through any of the chemical "staples"
(disulfide bonds) that hold domain IV together — all 8 are intact.

### Step 3 — Propose a million candidate designs

We used **AbLang2**, a language model trained on antibody sequences, to ask: at
each position, which amino acid substitutions still look like a plausible
antibody?

We then sampled **1,000,000** candidate designs from four deliberately different
strategies, so the portfolio tests several hypotheses rather than fifteen
variations of one idea:

| Strategy | Idea |
| --- | --- |
| CDR-H3 focused | edit the main binding loop, where published work claims the best results |
| Interface | edit other residues near the contact surface |
| Mixed | a few contact edits plus supporting changes elsewhere |
| Framework | edit the scaffold only, leaving the binding site alone |

Every candidate passes hard rules before it survives: exactly 242 amino acids,
at least 5 changes, linker untouched, cysteines untouched, no new
sugar-attachment sites. Roughly 7% were rejected purely for introducing a new
glycosylation site.

### Step 4 — Second opinion from a different model

We re-scored the survivors with **ESM2-3B**, a language model trained on all
proteins rather than just antibodies. Two models with different training data
fail in different ways, so agreement between them is more informative than
either alone.

**Neither model has ever seen HER2.** They can tell you a sequence still looks
like a protein. They cannot tell you it binds.

### Step 5 — Fold the complex and measure the interface

For the shortlist, we used **Boltz-2** to predict the 3D structure of each
designed antibody *bound to* HER2 domain IV, then computed **ipSAE** — the
metric the organizers asked for — using the original DunbrackLab program, not
our own approximation.

We also computed **epitope recovery**: of the 19 contacts seen in the real
crystal structure, how many does the model reproduce? This catches a design that
scores confidently but binds the *wrong face* of the protein — something ipSAE
alone cannot detect.

### Step 6 — The step that changed everything: run it again

Boltz-2 is not deterministic. Run the same sequence twice with different random
seeds and you get slightly different answers.

We measured how big that wobble is. **A single run carries about 50-60%
reliability** — meaning roughly half of the apparent difference between two
designs in a single-run ranking is just noise.

So we ran everything **many times**. The parent was folded **35 times**; the
ranked designs average **15 runs each**. Only then can you say design A really
scores above design B rather than having had a lucky roll.

### Step 7 — Guard against fooling ourselves

When you test ~250 designs and ask "is this one better than the parent?", pure
chance will hand you about a dozen that look significant. This is the classic
multiple-comparisons trap.

We applied a **Benjamini-Hochberg correction**, which adjusts the bar for how
many tests you ran. Designs that look significant but don't survive correction
are reported as *not significant*. At one point we had four apparent winners
that all evaporated under correction — we reported that honestly rather than
quoting the uncorrected number.

### Step 8 — Choose the final set

Ranking is **not** "sort by ipSAE". We combine five independent axes: sequence
plausibility, ipSAE, epitope recovery, structural confidence, and
developability (avoiding chemically awkward residues). Designs whose interface
has collapsed are barred from the lab list regardless of other scores.

We then re-rank under three *different* weightings and record how far each
design moves. A design that stays near the top regardless of weighting is a safer
bet than one that depends on a single metric.

---

## Part 3 — What we found

1. **A handful of designs genuinely score above the parent**, surviving
   multiple-comparison correction, each backed by 15-33 independent runs.
2. **Most designs score worse** — well over a hundred significantly below the
   parent. This is reassuring: it means the screen discriminates rather than
   flattering everything we feed it.
3. **Three results contradicted our own starting assumptions**, and we changed
   course rather than defending them:
   - We expected a bigger candidate pool to stop helping. It kept helping
     (+49% on the band that matters).
   - We expected antibody-plausibility scores to predict good interfaces. They
     **anti-correlate** — see Q6.
   - We expected CDR-H3 editing to be the strongest strategy, following the
     literature. It was the **weakest** here.

---

## Part 4 — Questions you should expect

### Q1. "Your designs don't dramatically beat the parent. Isn't that a failure?"

No, and we would be suspicious of anyone who claims otherwise. The parent binds
at 0.82 pM after decades of optimisation. The realistic outcome for a few hours
of computation is a set of **compliant, structurally sound candidates that are
not detectably damaged**, with a handful that look modestly better on a
structural proxy.

What we delivered is what was asked for: designs, a genuine ipSAE for each, and
the method. We also delivered something most pipelines don't: an honest estimate
of how much of our own ranking is noise.

### Q2. "Is ipSAE a measure of binding strength?"

**No.** ipSAE measures how *confident* a structure-prediction model is about the
interface it drew. A high ipSAE means the model is sure about the arrangement of
atoms. It is not a binding constant, it is not calibrated to affinity, and we
never convert it to one. The organizers explicitly warned against this, and
against ranking by ipSAE alone — we do neither.

### Q3. "Why did you only use part of HER2?"

Two reasons. First, the organizers asked for it. Second, it's correct: we
measured the contacts in the crystal structure and the entire binding site lies
in domain IV. Including the other 500 residues adds compute cost and prediction
uncertainty without adding a single contact. We checked the crop doesn't break
any disulfide bonds and retains every observed contact residue.

### Q4. "Why didn't you use RFdiffusion or BindCraft? They're state of the art."

They are, for a different problem. Those tools **invent new binders from
scratch**. We were asked to **edit an existing one**. Using them here would both
violate the brief and throw away the most valuable thing we have: a molecule
that already works. (Note the easy confusion: *BoltzGen* generates new proteins
and is excluded; *Boltz-2*, which we use, predicts the structure of a sequence
you already have.)

### Q5. "Why run the same design 15-35 times? Isn't that wasteful?"

It's the opposite — it's what makes the results mean anything. We measured that
a single run is only ~50-60% reliable. With one run per design, the top of our
leaderboard would largely be whichever designs got lucky. Given a fixed compute
budget, we deliberately chose **fewer designs measured well** over more designs
measured badly, and we can show you the variance decomposition that justifies it.

### Q6. "Your antibody language model scores anti-correlate with interface
quality. Doesn't that mean your generation step is broken?"

It means something more interesting. Trastuzumab's binding loops are
**affinity-matured** — evolution and engineering pushed them to be unusual,
precisely because unusual shapes grip the target. An antibody language model is
trained on typical antibodies, so it tends to suggest changes that make the loops
*more typical* — pulling them back toward the generic consensus and away from
the contacts that do the work.

Once we measured this, we stopped using those scores as something to maximise
and started using them only as a **floor** to reject implausible sequences. This
is one of the more useful findings in the project, and it is the kind of thing
you only see if you check your assumptions against structural data.

### Q7. "How do you know the predicted structures are right at all?"

We validated against the experimental ground truth. The parent model recovers
**100% of the 19 contacts** seen in the real crystal structure, with high
confidence scores (ipTM ~0.9, pLDDT ~0.93). The model reproduces a known answer
before we trust it on unknowns.

We also watched it fail correctly: one design mutated a tryptophan that makes a
4 Å contact with HER2, and its score collapsed to essentially zero. The method
detects real damage.

### Q8. "You reused the same sequence alignment across designs. Isn't that
cutting corners?"

It's a deliberate, documented trade-off. Structure predictors use an alignment
of related sequences as context. Fetching a fresh one per design costs ~100
seconds and would have dominated our budget — about six hours for this campaign.

Because every design differs from the parent by only 5-8 substitutions out of
242 and has identical length, the alignment columns stay valid. We reuse it and
rewrite only the query row. It also has a scientific benefit: every design is
evaluated under a **byte-identical** condition, so comparisons are matched by
construction.

The honest caveat, which we state in the report: this slightly favours designs
closer to the parent. We flagged it ourselves rather than waiting to be asked.

### Q9. "Why a minimum of 5 mutations and not more?"

Five is the organizers' minimum. We cap at 8 by our own choice. Our data
supports staying low: **mutation count was the strongest single predictor of
interface quality, and the relationship is negative** — more edits, worse
interfaces, on average. For a molecule this optimised, every additional change is
another chance to break something. Notably, one of our statistically significant
designs achieves it with exactly **5** substitutions.

### Q10. "What is FDR correction and why should I care?"

If you test one design at the usual 5% threshold, there's a 5% chance of a false
alarm. Test 250 designs and you expect about **12 false alarms** even if nothing
is really better. Benjamini-Hochberg correction raises the bar in proportion to
how many tests you ran.

It matters here because without it we would have reported winners that were
statistical noise. We ran it, several apparent winners disappeared, and we said
so.

### Q11. "What would you do with more time?"

Three things, in order:

1. **More replicate runs.** Reliability is still the limiting factor; going to
   ~11 runs per design everywhere would let us resolve smaller differences.
2. **A fresh-alignment control.** We have a small bias we can quantify but
   haven't yet (see Q8).
3. **Orthogonal structure prediction.** Everything structural rests on one
   model. A second, independent predictor would tell us which conclusions are
   about biology and which are about Boltz-2.

What we would *not* do is generate more candidates. We showed that's not the
bottleneck.

### Q12. "How is this better than random mutagenesis?"

Random mutagenesis would hit the six critical contact residues and destroy
binding. We froze those using measured geometry. It would also ignore
developability, introduce glycosylation sites and cysteines, and produce no
estimate of its own reliability.

That said, we hold this claim loosely: we did not run a random-mutagenesis arm,
so we can argue it mechanistically but cannot show you the head-to-head. That
would be a good control to add.

### Q13. "You cofolded more designs than the brief suggested. Why?"

True, and it's recorded in our compliance file rather than hidden. The
*ordering* rule — screen by sequence first, cofold only a shortlist — was never
violated: a million candidates were filtered down before any structure was
predicted.

We exceeded the suggested count because spare capacity went into **replicate
runs of the same shortlist**, not into exploring more candidates. Given that a
single run is only ~50-60% reliable, that was the choice that made the results
defensible. The submission is still presented as a ranked 50 with 15
nominations.

### Q14. "What's the single thing you'd want us to remember?"

That we measured our own uncertainty before making any claim. The most important
number in this project isn't an ipSAE score — it's the finding that a single
structure prediction is only about half signal. Everything else follows from
taking that seriously.

---

## Part 5 — Lines to avoid

Do not say any of these, even if pushed:

| Don't say | Say instead |
| --- | --- |
| "Our design binds tighter than Herceptin" | "It scores higher on a structural confidence metric; binding is for the assay to decide" |
| "We predict a K_D of X" | "No K_D is predicted anywhere in this work" |
| "Our best design improved ipSAE by 0.06" | "...by 0.06, against a seed-to-seed variation of about 0.06 — which is why we ran it 15+ times and corrected for multiple testing" |
| "All 50 designs are validated" | "All 50 carry a genuine computed ipSAE; none is experimentally validated" |
| "The model proves the design works" | "The model ranks designs for experimental triage" |

The strongest position in the room is the one where every number you present
has an error bar and you volunteer your own weaknesses before anyone finds them.
