# Data Distribution for NLTK

This repository contains data packages (corpora, models, tokenizers, etc.) for use with [NLTK](https://www.nltk.org/).

## Installation

To install data using the NLTK downloader, run:

```python
import nltk
nltk.download()
```

For detailed instructions, please see the [NLTK website](https://www.nltk.org/).

---

## Recent Enhancements

> **Note:** You do not need to update `index.xml` when adding or modifying packages. It is automatically rebuilt after changes are merged.

### Licensing Transparency ([PR #242](https://github.com/nltk/nltk_data/pull/242))
- Added a top-level `LICENSE` (Apache License 2.0) for the repository.
- Added `LICENSE-OVERVIEW.md` summarizing the licensing structure, with emphasis on the diversity of dataset licenses and the importance of reviewing individual terms.
- Added `DATASET-LICENSES.md` — a comprehensive, grouped list of all data packages and their licenses, highlighting any ambiguous or unclarified licensing.
- These changes improve transparency, support responsible use, and aid compliance for all users.

### Contribution Guidelines
- Introduced a detailed `CONTRIBUTING.md` with step-by-step instructions for adding a new data package using Git and GitHub.
- Please see `CONTRIBUTING.md` for instructions on adding datasets and making other contributions.
- Contributors are encouraged to clarify dataset licenses and to consult the new licensing overview and dataset license table.

---

*For instructions on adding new data packages, please see [CONTRIBUTING.md](CONTRIBUTING.md). For licensing details, see [LICENSE-OVERVIEW.md](LICENSE-OVERVIEW.md) and [DATASET-LICENSES.md](DATASET-LICENSES.md).*