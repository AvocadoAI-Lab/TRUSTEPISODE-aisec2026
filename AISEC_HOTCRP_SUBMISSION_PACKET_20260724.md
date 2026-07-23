# AISec 2026 HotCRP submission packet

This file is an author-facing copy/paste packet. Do not upload it as an anonymous artifact.

- Submission site: <https://aisec26.hotcrp.com/>
- Firm deadline: 2026-07-24 23:59 AoE
- Recommended paper type: **Original research paper**
- Do not select benchmark paper: the contribution is an evidence contract and bounded evaluation,
  not a newly proposed benchmark.

## Exact title

TrustEpisode: Auditable Evidence Contracts for AI-Assisted EDR/NDR Investigation

## Exact abstract with LaTeX macros expanded

AI-assisted security investigation turns sparse tool outputs into confident narratives, yet
arrival order, collector failure, and late evidence can silently alter the facts exposed to an
analyst or agent. We present TrustEpisode, a deterministic, auditable EDR/NDR
episode-reconstruction contract. Episode Synthesis alone owns membership; revisions and terminal
audit outcomes are append-only; source health differs from “no detection;” unsupported
probabilities remain null; and downstream AI reads versioned evidence without authority over case
facts.

On 70 sealed live CALDERA M1–M7 malicious runs (40 standalone benign controls are not detection
trials), sliding sessionization raises mean coverage from 0.807 to 0.821. Fair sliding baselines
show no superiority: EB4 ties EB2 on all action-coverage pairs (0/70/0 W/T/L)
and trails EB1 on one concurrent-benign M7 run (0/69/1; mean Δ = −0.014, 95% CI
[−0.043, 0.000]). Canonical replay is byte-identical on 60 M1–M6 runs, whereas raw arrival
order is not robust without re-canonicalization. 18/18 audit fixtures cover seven terminal failure
codes; an A–G taxonomy localizes M2’s repeatable gap to class D (token mapping failure); and
a deployed case trace preserves one Suricata and two Wazuh events with ATT&CK references.

All 8/8 synthetic boundary cards behave as specified: the valid control is accepted,
six invalid or unsealed mutations are rejected, and a resealed allowed-field mutation is accepted,
showing digest integrity still requires external writer authorization. A once-run held-out
20-card Qwen2.5-7B pilot yields 9/20 fully exact responses; locked same-card replication on
deployment-default Gemma3-1B yields 0/20. These audited configurations support no general
LLM-accuracy or fitted-calibration claim; typed evidence instead makes their errors reviewable.

## Keywords

AI-assisted security operations; attack episode reconstruction; EDR; NDR; replayable audit;
evidence provenance

## Recommended AISec topics

Select these when matching checkboxes are available, in this priority order:

1. (Network) Intrusion detection and response
2. Computer forensics
3. Containment and guardrails for autonomous agents
4. Truthfulness, calibration, and hallucination mitigation
5. Safe and usable applications of AI
6. Human factors in AI/ML and Security/Privacy

## ACM CCS concepts

- Security and privacy → Intrusion/anomaly detection and malware mitigation
- Computing methodologies → Artificial intelligence

## Exact Generative AI disclosure

OpenAI Codex and Cursor agents assisted with language editing, experiment orchestration,
consistency checking, figure preparation, citation verification, and claim-to-evidence audits.
The authors independently designed the study, verified the code, experimental outputs, citations,
screenshots, and reported results, and take responsibility for the manuscript.

## Anonymous artifact description

The supplementary ZIP contains a portable reference runtime, machine-readable contracts,
executable synthetic conformance checks, sealed or path-de-identified result copies, generated
tables, and a claim-to-evidence matrix. From a fresh Python environment it installs the packaged
runtime, fails closed unless the imported module originates inside the extracted archive,
executes all 38 implementation tests, and re-executes A1–A12, A–G, AB0–AB3, AI0–AI7, T1–T8,
temporal boundary fixtures, contract validation, table generation, and fail-closed claim
verification. It verifies but does not re-run live collection, cohort
re-synthesis requiring omitted raw lab bundles, or Ollama inference.

## Anonymous artifact URL (recommended by the AISec CFP)

The AISec CFP encourages an anonymous repository link at submission time. Publish the exact
companion ZIP only through an anonymity-checked URL, such as the CFP-suggested
`anonymous.4open.science`, or another organizer-approved mechanism. Do not paste the current
author-owned Git repository URL. Before entering the URL, open it while signed out and verify
that it reveals no owner, organization, email, commit author, redirect, or repository history.
The downloaded ZIP must match the Artifact Digest printed in the submitted PDF.

## Optional ethics statement

The evaluation used an isolated laboratory with frozen CALDERA workloads, two Ubuntu targets,
and an inline Suricata sensor. It did not involve production users, personal data, or attacks
against third-party systems. Operational screenshots were cropped to remove account-identifying
chrome, and the anonymous artifact redacts only local source-path prefixes.

## Files prepared for upload

The public HotCRP page was checked on 2026-07-24, but the submission form and its
field names are visible only after sign-in. Upload the paper PDF to the required
paper field. Attach the ZIP only if the signed-in form exposes a supplementary
material/file field; otherwise do not substitute it for the paper PDF or place it
in an unrelated field. Retain the ZIP and follow an organizer-approved anonymous
artifact route if the form has no supplementary field.

### Paper PDF

- File: `TrustEpisode_AISec2026_submission_20260724.pdf`
- SHA-256: `69b5f49da8191d47b708bafafc15ef1b34aab30fcfefe524f36c538342efa6cb`
- Format: English, anonymous, ACM double-column, Letter, 11 pages
- The Conclusion and well-marked Appendix meet on page 10; references occupy pages 10–11;
  the Generative AI paragraph appears after references/appendix and does not count toward the limit.

### Supplementary artifact (conditional on a matching HotCRP field)

- File: `TrustEpisode_reproducibility_companion_v1.zip`
- SHA-256: `cc4d451b50f975fdd7ab07c263a8ce2044ab771126808e485faac4033852a730`
- Fresh-environment audit: PASS
- Independent anonymity scan: PASS

## Author-only fields still requiring manual entry

- Signed-in verification of the actual HotCRP field names and required declarations
- An anonymity-checked artifact URL if the form provides an artifact/repository field
- Full author names, affiliations, countries, and email addresses
- Complete conflict-of-interest declarations
- Paper conflicts selected in HotCRP
- Confirmation that the work is not simultaneously submitted and does not substantially overlap
  an archival publication
- The author who will attend and present if accepted
- Any funding or institutional disclosure required by the authors’ organizations

Do not add author identity, acknowledgments, repository ownership, or funding details to the
anonymous PDF or ZIP. Those belong only in HotCRP metadata until camera-ready.
