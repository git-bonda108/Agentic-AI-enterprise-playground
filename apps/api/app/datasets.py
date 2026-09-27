"""Datasets: the mock sets that ship with the playground, described well enough to use, and the trusted public sources to go to next.

The mock sets are synthetic and deterministic (see `app.agents.data`); this module adds what a person needs before using one:
the columns with types and an example value, the public set each one is modelled on with its licence, the blueprints and
notebooks that read it, a one-line notebook snippet, and CSV or JSON export. `SOURCES` is a curated list of public data
catalogues with the loader each one publishes, so a notebook can pull real data into the sandbox with one `%pip install`.
URLs verified 2026-09-27.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from app.agents.data import DATASETS, load_csv, load_json

CC0 = {"name": "CC0 1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/"}

# What each synthetic set is modelled on, so a person knows which real set to graduate to and under which licence.
MODELED_ON: dict[str, dict] = {
    "invoices": {"name": "Voxel51 invoice OCR set", "url": "https://huggingface.co/Voxel51", "licence": "ODbL", "licence_url": "https://opendatacommons.org/licenses/odbl/"},
    "purchase_orders": {"name": "AdventureWorks sample database", "url": "https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure", "licence": "MIT (Microsoft samples)", "licence_url": "https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure"},
    "contracts": {"name": "CUAD, Contract Understanding Atticus Dataset", "url": "https://www.atticusprojectai.org/cuad", "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/"},
    "sales": {"name": "AdventureWorks sample database", "url": "https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure", "licence": "MIT (Microsoft samples)", "licence_url": "https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure"},
}

# Which gallery notebook opens each set, so the Datasets page can link straight into a runnable example.
NOTEBOOKS: dict[str, str] = {
    "sales": "data-with-pandas",
    "policies": "knowledge-qa-space",
    "invoices": "agent-with-review",
    "purchase_orders": "agent-with-review",
    "contracts": "agent-with-review",
}

SOURCES: list[dict] = [
    {"id": "kaggle", "name": "Kaggle Datasets", "url": "https://www.kaggle.com/datasets", "kind": "Community catalogue", "licence": "Per dataset; shown on each page", "install": "%pip install kagglehub", "python": 'import kagglehub\npath = kagglehub.dataset_download("owner/dataset-name")  # needs KAGGLE_USERNAME and KAGGLE_KEY', "docs": "https://github.com/Kaggle/kagglehub", "good_for": "Tabular, image and text sets with notebooks and competitions attached"},
    {"id": "huggingface", "name": "Hugging Face Datasets", "url": "https://huggingface.co/datasets", "kind": "ML datasets hub", "licence": "Per dataset; declared in the dataset card", "install": "%pip install datasets", "python": 'from datasets import load_dataset\nds = load_dataset("imdb", split="train[:1000]")', "docs": "https://huggingface.co/docs/datasets/index", "good_for": "Text, audio and vision sets for training and evaluation; streaming for large corpora"},
    {"id": "uci", "name": "UCI Machine Learning Repository", "url": "https://archive.ics.uci.edu", "kind": "Academic benchmark sets", "licence": "Mostly CC BY 4.0; per dataset", "install": "%pip install ucimlrepo", "python": "from ucimlrepo import fetch_ucirepo\nadult = fetch_ucirepo(id=2)\nX, y = adult.data.features, adult.data.targets", "docs": "https://github.com/uci-ml-repo/ucimlrepo", "good_for": "Classic tabular benchmarks with documented features"},
    {"id": "openml", "name": "OpenML", "url": "https://www.openml.org", "kind": "Benchmark platform", "licence": "Per dataset; mostly public domain or CC", "install": "%pip install openml", "python": "import openml\ndataset = openml.datasets.get_dataset(61)  # iris\nX, y, _, _ = dataset.get_data(target=dataset.default_target_attribute)", "docs": "https://openml.github.io/openml-python/", "good_for": "Reproducible tasks and benchmark suites with versioned data"},
    {"id": "datagov", "name": "Data.gov", "url": "https://catalog.data.gov/dataset", "kind": "US government open data", "licence": "Mostly US public domain; per dataset", "install": "%pip install requests", "python": 'import requests\nr = requests.get("https://catalog.data.gov/api/3/action/package_search", params={"q": "electric vehicles", "rows": 5})\nprint([d["title"] for d in r.json()["result"]["results"]])', "docs": "https://data.gov", "good_for": "Federal, state and city sets; CKAN API for search and downloads"},
    {"id": "eu", "name": "data.europa.eu", "url": "https://data.europa.eu/en", "kind": "European open data portal", "licence": "Mostly CC BY 4.0; per dataset", "install": "%pip install requests", "python": 'import requests\nr = requests.get("https://data.europa.eu/api/hub/search/search", params={"q": "air quality", "limit": 5})\nprint([d["title"].get("en") for d in r.json()["result"]["results"]])', "docs": "https://data.europa.eu/en", "good_for": "EU institutions and member-state sets with multilingual metadata"},
    {"id": "worldbank", "name": "World Bank Open Data", "url": "https://data.worldbank.org", "kind": "Development indicators", "licence": "CC BY 4.0", "install": "%pip install wbgapi", "python": 'import wbgapi as wb\ndf = wb.data.DataFrame("NY.GDP.PCAP.CD", ["IND", "USA", "DEU"], time=range(2015, 2025))', "docs": "https://github.com/tgherzog/wbgapi", "good_for": "Country-level economic and social indicators over time"},
    {"id": "owid", "name": "Our World in Data", "url": "https://ourworldindata.org", "kind": "Curated global statistics", "licence": "CC BY 4.0", "install": "%pip install owid-catalog", "python": 'from owid import catalog\nresults = catalog.find("population")\ntable = results.iloc[0].load()', "docs": "https://github.com/owid/owid-catalog-py", "good_for": "Long-run series on health, energy, economy and environment with charts"},
    {"id": "google", "name": "Google Dataset Search", "url": "https://datasetsearch.research.google.com", "kind": "Search engine for datasets", "licence": "Per dataset", "install": "", "python": "", "docs": "https://datasetsearch.research.google.com", "good_for": "Finding a set by topic across thousands of repositories before you pick a source"},
    {"id": "aws", "name": "Registry of Open Data on AWS", "url": "https://registry.opendata.aws", "kind": "Cloud-hosted open data", "licence": "Per dataset", "install": "%pip install boto3", "python": 'import boto3\nfrom botocore import UNSIGNED\nfrom botocore.config import Config\ns3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))\nprint(s3.list_objects_v2(Bucket="noaa-ghcn-pds", MaxKeys=5)["Contents"])', "docs": "https://registry.opendata.aws", "good_for": "Large scientific and geospatial sets read straight from S3 without egress into your account"},
    {"id": "azure", "name": "Azure Open Datasets", "url": "https://learn.microsoft.com/en-us/azure/open-datasets/dataset-catalog", "kind": "Cloud-hosted open data", "licence": "Per dataset", "install": "%pip install azureml-opendatasets", "python": "from azureml.opendatasets import NycTlcGreen\nfrom datetime import datetime\ndf = NycTlcGreen(start_date=datetime(2018, 5, 1), end_date=datetime(2018, 5, 7)).to_pandas_dataframe()", "docs": "https://learn.microsoft.com/en-us/azure/open-datasets/dataset-catalog", "good_for": "Weather, census, holidays and transport sets ready for Azure ML and Fabric"},
    {"id": "nyc-tlc", "name": "NYC TLC Trip Records", "url": "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page", "kind": "Single large public set", "licence": "NYC open data terms", "install": "%pip install pandas pyarrow", "python": 'import pandas as pd\ndf = pd.read_parquet("https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet")', "docs": "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page", "good_for": "A realistic multi-million-row table for performance and analytics demos"},
    {"id": "awesome", "name": "Awesome Public Datasets", "url": "https://github.com/awesomedata/awesome-public-datasets", "kind": "Curated index", "licence": "Per dataset", "install": "", "python": "", "docs": "https://github.com/awesomedata/awesome-public-datasets", "good_for": "A topic-by-topic list of high-quality sets maintained by the community"},
]


def _type_of(v: Any) -> str:
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "object"
    s = str(v)
    if s.count("-") == 2 and len(s) == 10 and s[:4].isdigit():
        return "date"
    try:
        float(s)
        return "number" if "." in s else "integer"
    except ValueError:
        return "string"


def columns_for(rows: list[dict]) -> list[dict]:
    """Column names, inferred types and an example value from the first rows."""
    if not rows:
        return []
    names: list[str] = []
    for r in rows[:50]:
        for k in r:
            if k not in names:
                names.append(k)
    out = []
    for n in names:
        sample = next((r[n] for r in rows[:50] if r.get(n) not in (None, "")), "")
        example = sample if isinstance(sample, (int, float, bool)) else str(sample)[:60]
        out.append({"name": n, "type": _type_of(sample), "example": example})
    return out


def _rows(spec: dict):
    return load_csv(spec["file"]) if spec["file"].endswith(".csv") else load_json(spec["file"])


def catalog() -> list[dict]:
    """The mock sets with schema, provenance, consumers, a notebook snippet and export links."""
    out = []
    for d in DATASETS:
        rows = _rows(d)
        if isinstance(rows, dict):
            preview = [{"key": k, "items": len(v)} for k, v in rows.items()]
            count, columns, shape = len(rows), [{"name": "key", "type": "string", "example": next(iter(rows), "")}, {"name": "items", "type": "list", "example": "…"}], "keyed"
        else:
            preview, count, columns, shape = rows[:5], len(rows), columns_for(rows), "table"
        out.append({
            **d,
            "rows": count,
            "preview": preview,
            "columns": columns,
            "shape": shape,
            "licence": CC0,
            "modeled_on": MODELED_ON.get(d["id"]),
            "notebook": NOTEBOOKS.get(d["id"]),
            "snippet": f'import playground\ndf = playground.frame("{d["id"]}")' if shape == "table" else f'import playground\nrows = playground.dataset("{d["id"]}")',
            "download": {"csv": f"/v1/data/{d['id']}/download?format=csv", "json": f"/v1/data/{d['id']}/download?format=json"},
        })
    return out


def export_rows(dataset_id: str, fmt: str) -> tuple[str, str, str]:
    """(body, media type, filename) for a dataset as CSV or JSON. Keyed corpora flatten to one row per item with its key."""
    spec = next((d for d in DATASETS if d["id"] == dataset_id), None)
    if spec is None:
        raise KeyError(dataset_id)
    rows = _rows(spec)
    if isinstance(rows, dict):
        rows = [{"key": k, **(item if isinstance(item, dict) else {"value": item})} for k, items in rows.items() for item in items]
    if fmt == "json":
        return json.dumps(rows, indent=2), "application/json", f"{dataset_id}.json"
    names: list[str] = []
    for r in rows:
        for k in r:
            if k not in names:
                names.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=names, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
    return buf.getvalue(), "text/csv", f"{dataset_id}.csv"


def sources() -> list[dict]:
    return SOURCES
