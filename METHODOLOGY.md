# Methodology

Snapshot: 23 October 2026. Publication window: 1 January–23 October 2026, inclusive. The site is a dated research catalogue, not a live alerting service.

## Journal scope

The registry comes from Nature Portfolio's official A–Z index. It includes Nature, Nature-branded research and review journals, Nature Communications, and only npj Digital Medicine from the npj family. The separate Communications series, Scientific Reports, other npj journals, and regional news editions are excluded. Journal grouping supports navigation and does not assert journal indexing status or quality.

The registry contains 76 titles; 70 have retrievable 2026 Crossref inventories. Six show open-for-submissions pages without a retrievable Crossref journal inventory. A missing inventory is not reported as zero published research.

## Retrieval and screening

Crossref journal/ISSN queries retrieve online publication dates in the stated window. Europe PMC title/abstract AI queries provide a second recall route. Candidate recall uses explicit AI terminology, with source-level additions for missed relevant papers. All retrieved npj Digital Medicine records enter source screening, including papers with no AI keyword. DOI suffix years do not determine publication eligibility: online publication date does.

Metadata records include news, corrections and other document types. Their total is not a research-article denominator. Candidate screening checks publisher type and accessible abstract, with selected full-text, Methods, Results, supplement or author-manuscript checks. Borderline records with insufficient substantive-AI evidence remain outside the confirmed catalogue. Their DOI, status and reason are available in the screening decisions.

A substantive AI method, AI evaluation or AI system must be central to a medical, biomedical, bioinformatics or biological-discovery question. Protein design, gene/omics analysis, molecular and cellular biology, drug discovery and biomedical engineering are eligible. Generalizable molecular/genomic AI methods may involve nonhuman species. Agriculture-only, environment-only, general computing with incidental biomedical demonstrations, and pure medicine/biology without substantive AI are excluded. Routine regression alone is insufficient. An incidental AlphaFold assay in an otherwise mechanistic biology paper does not automatically qualify.

## Record detail and evidence

**Curated analyses** contain a specific English interpretation of the research question, AI approach and findings. **Source-extracted records** contain factual source extraction and a source-based eligibility screen; they are not presented as fully interpreted experimental analyses. Short attributed objective excerpts are limited to 20 words. Raw abstracts, full-text articles, PDFs and private retrieval caches are not distributed in the repository or website. Original article/DOI and additional evidence links remain accessible.

Some curated records lack fully extracted cohort counts. A blank field means extraction has not established that field, not that the published study lacked it. An accessible abstract is not described as a full-text review. Publisher metadata article types are retained, so an evidence synthesis may be labeled Article by the publisher.

## Scale and design

Patient, participant, image, visit, cell, sequence, protein, study and dataset counts retain their units. Training, validation, reader, randomized and analyzed populations must remain separate. Automatically extracted counts carry a warning if their cohort role has not been manually resolved. Unspecified numeric tokens are omitted. There is no pooled sample-size total across papers.

Four study-design concepts are separate: prospective data collection; prospective validation of an AI system; patient-level randomized controlled trials; reader/clinician experiments. Existing curated npj design labels are retained where available; unassessed fields remain explicit and are never counted as absent. These design statistics cover the labeled subset and must not be interpreted as complete across all journals. Randomization of readers or vignettes is not a patient RCT. Prospective collection does not establish prospective AI validation.

## Statistics

All charts count currently indexed publications in the selected filters. They do not estimate the proportion of all journal articles that use biomedical AI. The screening ledger supplies journal-level retrieval, candidate, screened, indexed and pending denominators. Time trends are affected by recall and screening coverage; October is partial.

Research-area and AI-method tags are transparent keyword-based descriptions of the displayed record, not mutually exclusive clinical diagnoses. Disease tags match titles and objectives and may overlap. A missing tag is not a negative diagnosis or evidence that the full article does not discuss that disease. Resource tables count populated evidence fields. Absence of a link does not prove that data or code are unavailable; a data/code statement link does not prove unrestricted public access.

Institution statistics count one first author's first institution per publication, with explicit publisher author–affiliation mapping. Exact reported organizations are used rather than ranking all collaborators. Departments, campuses and institutional aliases are not exhaustively harmonized, so these counts are exploratory. The complete reported first affiliation and coauthor affiliation list remain in each record.

CSV exports follow the current selection. Multi-label category percentages can sum to more than 100%. This catalogue uses descriptive statistics; it makes no population-level inferential or journal-quality claims.

## Reuse and corrections

The public JSON snapshot, journal registry, compact screening decisions and curation notes accompany the source. Raw publisher content is not included. Original content remains subject to its source license; original links and attribution are preserved. Corrections should identify a DOI and cite the relevant source passage or section in a GitHub issue. After changing the public snapshot, run `python3 scripts/build.py` and `python3 scripts/validate.py` before publishing.
