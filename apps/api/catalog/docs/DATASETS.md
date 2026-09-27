# Datasets

Where the data in the playground comes from, how to use it, and where to get real data when a mock set is no longer enough. The page lives under Build, Datasets; the routes are `GET /v1/data`, `GET /v1/data/{id}`, `GET /v1/data/{id}/download` and `GET /v1/data/sources`.

## Mock datasets

Eight synthetic sets ship with the playground. They are generated deterministically on first use (see `apps/api/app/agents/data.py`), so every person sees the same rows, no personal or customer data is ever involved, and any blueprint or notebook can run against them safely. Each set is released under CC0 and modelled on a public set so you know which real data to graduate to.

| Set | File | Modelled on | Read by |
| --- | --- | --- | --- |
| Supplier invoices | invoices.json | Voxel51 invoice OCR set (ODbL) | Document reconciliation |
| Purchase orders | purchase_orders.json | AdventureWorks (MIT) | Document reconciliation |
| Vendor contracts | contracts.json | CUAD clause taxonomy (CC BY 4.0) | Document reconciliation |
| Monthly sales | sales.csv | AdventureWorks (MIT) | Data analyst, the pandas notebook |
| Company policies | policies.json | Synthetic | Knowledge Q&A, the Knowledge Space notebook |
| Offline research corpus | research_corpus.json | Public facts with source links | Sage Lens |
| Learning references | learning_refs.json | Public course and documentation links | Learning path |
| Sample drafts | drafts.json | Synthetic | Review panel |

The Datasets page shows, for each set, the columns with an inferred type and an example value, a preview of the first rows, the licence and the modelled-on source, the blueprints and the gallery notebook that read it, a two-line notebook snippet, and CSV and JSON downloads. Keyed corpora (a dictionary of lists) flatten to one row per item with its key when exported as CSV.

In a notebook:

```python
import playground
df = playground.frame("sales")          # pandas DataFrame
rows = playground.dataset("policies")   # raw rows
```

## Trusted public sources

When a mock set is not enough, the second tab lists curated public sources with the loader each one publishes, so a notebook can pull real data into the sandbox with one `%pip install` line followed by the snippet. URLs were verified on 2026-09-27.

| Source | Kind | Loader |
| --- | --- | --- |
| Kaggle Datasets | Community catalogue | `kagglehub` (needs KAGGLE_USERNAME and KAGGLE_KEY) |
| Hugging Face Datasets | ML datasets hub | `datasets` |
| UCI Machine Learning Repository | Academic benchmark sets | `ucimlrepo` |
| OpenML | Benchmark platform | `openml` |
| Data.gov | US government open data | CKAN API with `requests` |
| data.europa.eu | European open data portal | Search API with `requests` |
| World Bank Open Data | Development indicators | `wbgapi` |
| Our World in Data | Curated global statistics | `owid-catalog` |
| Google Dataset Search | Search engine for datasets | Browse, then pick a source |
| Registry of Open Data on AWS | Cloud-hosted open data | `boto3` with unsigned requests |
| Azure Open Datasets | Cloud-hosted open data | `azureml-opendatasets` |
| NYC TLC Trip Records | Single large public set | `pandas` with `pyarrow` |
| Awesome Public Datasets | Curated index | Browse |

Licences are per dataset on every catalogue; the page shows the general terms and links to each source's own page. Data pulled into a sandbox stays in that person's sandbox and is never sent to a model unless the notebook does so explicitly.

## Cost and token drill-down

The Cost page reconciles every number to the same ledger rows and now drills down: click a row to add it as a filter and open the next layer already narrowed (department to user to feature to model to conversation; provider, key source and blueprint lead to model; a day bar leads to feature). Chips at the top show the active filters; removing one widens the view again. Tokens are split into input, output and cached in the totals and per row, so prompt caching shows up. The ledger rows table at the bottom lists the raw calls behind the view, newest first, with paging, and both the view and the rows export as CSV.

Routes: `GET /v1/usage/breakdown?by=<layer>&<filters>&format=csv` and `GET /v1/usage/events?<filters>&limit=&offset=&format=csv`, where filters are `department`, `user_id`, `feature`, `model`, `provider`, `key_source`, `conversation_id`, `blueprint_id` and `day`. People who are not admins or champions only ever see their own rows.

## Hours on the console

The console shows Chat hours, Agent hours and Notebook hours for the last seven days with the change against the previous seven and the number of people behind each, plus an all-features tile. Hours are derived from ledger sessions the same way as the adoption analytics: events for one person are grouped into sessions (a gap of more than 30 minutes starts a new one), a session runs from its first to its last event plus a short tail, and its time is shared between the features used. `GET /v1/usage/summary` carries the figures under `hours`.
