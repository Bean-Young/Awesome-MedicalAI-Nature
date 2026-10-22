# Awesome MedicalAI Nature

A public, English-language research atlas for **AI × medicine, biomedical science and bioinformatics** in Nature journals, Nature Communications and npj Digital Medicine.

**[Explore the website](https://awesome-medicalai-nature.grandowlet6.chatgpt.site/)** · [Browse all papers](CATALOGUE.md) · [Methodology](METHODOLOGY.md) · [Open JSON](data/catalogue.json) · [Screening decisions](data/screening-decisions.json)

Publication window: **1 January–23 October 2026**. This is a dated, source-backed catalogue; keyword recall is not an exhaustive full-text census.

## Explore

- Filter by journal family, journal, biomedical area, disease focus, AI method and record detail.
- Read research questions, methods, experimental counts with units, datasets, authors and institutions.
- Follow article, DOI, Methods and availability evidence links.
- Compare descriptive publication counts by journal, disease, area, institution, method and month.
- Inspect separate prospective collection, prospective validation, patient RCT and reader-experiment labels where curated.
- Cancel any filter through its chip, reset all filters, or click a selected chart label again.
- Export the selected papers and statistics as CSV.

## Scope

Nature and Nature-branded research/review journals, Nature Communications, and **npj Digital Medicine only**. Separate Communications-series titles, other npj titles and Scientific Reports are excluded. Biomedical research includes molecular/cellular biology, genomics/omics, proteins and drug discovery when substantive AI is central. Pure medicine without AI is excluded.

The website distinguishes **curated analyses** from **source-extracted records**. Missing extraction fields do not establish absence in the study. Counts never combine patients, images and cells. The coverage ledger explains the denominator; this collection is not a claim about the complete biomedical-AI share of a journal.

## Run locally

No Node packages, API keys or login required.

```sh
python3 scripts/build.py
python3 scripts/validate.py
python3 -m http.server 8766 --directory dist
```

Open http://localhost:8766/ . The public snapshot is sufficient to rebuild the static site with the Python standard library. `dist/` is deployable to any static host.

## Files

- `dist/`: website and public data assets.
- `data/catalogue.json`: public normalized paper snapshot.
- `data/coverage.json`, `data/journals.json`: retrieval and screening denominators.
- `data/screening-decisions.json`: DOI-level eligibility decisions and reasons.
- `data/curation/`: source-backed manual scope and interpretation notes.
- `scripts/build.py`, `scripts/validate.py`: snapshot build and integrity checks.
- Other `scripts/`: research collection/extraction utilities. These may require `requests`, `beautifulsoup4` or `pypdf`, separately retrieved source caches and review inputs; they are not an unattended automatic curator.

Raw publisher abstracts, full texts, PDFs and local caches are excluded from Git. Original paper content and metadata remain subject to their source terms. The catalogue is independent and is not affiliated with Nature Portfolio.

For a correction, [open an issue](https://github.com/Bean-Young/Awesome-MedicalAI-Nature/issues) with the DOI and supporting original section.
