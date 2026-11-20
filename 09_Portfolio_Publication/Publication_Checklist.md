# P002 publication checklist and repository plan

**Prepared for review · 20 November 2026**

Proposed repository name `last-mile-delivery-intelligence`. The publication scope is source, approved documentation, synthetic test fixtures, and reviewed screenshots. This portfolio entry represents a self-directed simulated engagement.

## Proposed tree

```text
last-mile-delivery-intelligence/
├── .gitignore
├── LICENSE                   MIT for original code and documentation
├── README.md
├── AGENTS.md
├── 00_Admin_and_Scope/        Charter
├── 03_SQL/                   Provision, schema, load, and reporting SQL
├── 04_Python/                Checksum-verified workbook extractor
├── 05_Quality_Assurance/     Read-only checks, synthetic tests, Phase 0 evidence
├── 06_Dashboard/             Streamlit app, dependency pins, safe config, runbooks
├── 07_Reports_and_Delivery/  Task 020 client deliverables and Task 013 evidence
├── 08_Documentation/         Dataset provenance, SQL methodology, setup
└── 09_Portfolio_Publication/ Checklist and reviewed screenshots
```

Developers create `01_Data_Raw/` and `02_Data_Processed/` locally. Raw and processed data, virtual environments, private settings, caches, logs and test outputs stay out of the release. Earlier Task 013 reports are dated analytical evidence. Task 020 documents are the client-facing record.

## Workspace audit

| Item | Finding and disposition |
|---|---|
| Generated CSV | One 25,333,095-byte staged workbook extract in `02_Data_Processed/`. It is reproducible and local. |
| Original workbook | Located outside the project. Download instructions and checksum remain public-facing documentation. |
| Virtual environment and Python caches | Approx. 470 MiB in `.venv/`, plus six project bytecode cache files at audit. Ignore both. |
| Phase 0 evidence | The in-project audit script matches its original. The report differs from its archived original only in the companion-script link, which now resolves to that local copy. |
| Duplicate and historical material | No byte-identical files within the candidate source/document set at audit. Task 013 and Task 020 reports overlap by purpose and record different maturity stages. Use Task 020 as the README entry point. |
| Credentials and local database material | No credential file or PostgreSQL data directory was identified in the project tree. The pattern-only candidate text scan found no private key, credential-bearing database URL, token prefix or quoted password assignment. The app's passfile lives outside the repository. Repeat the scan on the exact publication set. |
| Safe runtime configuration | `06_Dashboard/.streamlit/config.toml` is a distributable localhost config. The ignore rules cover Streamlit secrets separately. Preserve loopback-only examples. |
| Documentation | Active setup and QA commands use repository-relative paths. Historical paths remain in the Phase 0 evidence and provenance to document the original audit. |
| Screenshots | All three approved captures are integrated in the README with the planned captions and alt text. Task 022 removed PNG DPI metadata while preserving pixels and color information. |
| Reproducibility | Direct dependencies are pinned. Full transitive locking, a clean-checkout setup rehearsal, and final keyboard and narrow-window checks remain open. The acceptance record preserves the completed live tests. |
| Licensing and privacy | Mendeley identifies the dataset as CC BY 4.0. Preserve the authors, version, DOI, license and description of changes. The [MIT license](../LICENSE) covers original code and documentation and names Addison Thompson as the 2026 copyright holder. Keep raw rows and record-level identifiers out of publication imagery and attachments. [Official dataset](https://data.mendeley.com/datasets/kkwgfvmtxn/1) · [CC BY 4.0 deed](https://creativecommons.org/licenses/by/4.0/) |

## Before a future publication

- [ ] Approve the README, Task 020 findings and executive summary. Verify the simulated-engagement language and published numbers against the acceptance record.
- [x] Prepare the MIT license for original repository code and documentation. Keep the dataset license and attribution separate.
- [x] Confirm the copyright holder and record the final 2026 notice in `LICENSE`.
- [x] Integrate all three approved screenshots with the planned captions and alt text. Strip nonessential metadata and verify image links.
- [ ] Review the final GitHub preview and screenshot exposure at publication time.
- [x] Repair the Phase 0 companion link and make current setup and QA examples portable. Preserve historical findings and provenance.
- [ ] Rehearse the README from an empty checkout using the separately downloaded workbook and a local test database. Verify the checksum, use the scripts in order, and run the four opt-in live dashboard tests. Record resolved dependency versions and document any platform differences.
- [ ] Complete keyboard and narrow-window review. Confirm screenshots expose only approved data.
- [ ] Once Git initialization is authorized, stage only intended files and inspect the staged names, sizes, and content. Verify that the ignore rules exclude the workbook, extracts, dumps, app secrets, and passfiles. Scan the staged set for tokens, connection strings and private keys. Ignore rules cannot remove content from an existing index.
- [ ] Obtain publication approval before any remote creation or push.

No files were deleted. Git initialization and publication are outside this preparation task.

## Internal preparation checks

Validated 157 repository-relative Markdown links across the 76-file candidate set. That audit preceded the Phase 0 link repair. Ripgrep's gitignore-compatible matcher passed 14 exclusion and five inclusion fixtures without a Git repository. The test protected sample data, secrets, dumps and draft screenshots while retaining setup SQL, the safe Streamlit configuration and approved screenshot placement. A final Git staging review remains necessary when initialization is authorized.

The project regression suite passed 26 tests. Four opt-in live tests were skipped during this preparation run. The separate final acceptance record preserves the earlier 30-test live result. [Final acceptance record](../07_Reports_and_Delivery/020_Delivery_and_Acceptance.md)

## Task 023 cleanup validation

The cleanup added the MIT draft, separated repository and dataset licensing in the README, repaired the Phase 0 companion link, updated the screenshot index, and made executable examples portable. The setup path changes cover Tasks 013–020 in the QA, dashboard, and delivery folders and the PostgreSQL provisioning, schema, ingestion, arrival, sequence, comparison, and distance runbooks. Historical machine paths remain in the source evidence as provenance.

Validation found 163 resolved local Markdown targets, three valid PNGs with approved captions and alt text, and 44 Bash examples that passed syntax checks. The Phase 0 report matched the archived original after accounting for the one link replacement. The regression suite passed 26 non-live tests and skipped four opt-in live checks. Bash syntax checks establish command structure. Clean-checkout execution remains a release gate.
