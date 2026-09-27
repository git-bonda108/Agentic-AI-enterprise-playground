"""Batch 17: the documentation hub serves every product guide, its images and search, and the shipped mirror never drifts."""

import filecmp
from pathlib import Path

from app.docs_hub import GUIDES, SECTIONS, catalog_dir, docs_dir, headings, search, slugify


def test_shipped_mirror_matches_the_repository_docs_and_excludes_the_delivery_log():
    repo, mirror = docs_dir(), catalog_dir()
    assert mirror.exists(), "run `npm run sync:docs`"
    if repo == mirror:
        return  # running from the image: nothing to compare
    listed = {g["file"] for g in GUIDES}
    for g in GUIDES:
        assert filecmp.cmp(repo / g["file"], mirror / g["file"], shallow=False), f"{g['file']} drifted: run `npm run sync:docs`"
    assert not (mirror / "BATCHES.md").exists() and "BATCHES.md" not in listed
    assert {p.name for p in (repo / "images").iterdir()} == {p.name for p in (mirror / "images").iterdir()}
    assert {p.name for p in repo.glob("*.md")} - {"BATCHES.md"} == listed, "every guide in docs/ must be listed in the hub (or be the internal delivery log)"


def test_guides_list_carries_sections_reading_time_and_headings(client, headers):
    body = client.get("/v1/docs", headers=headers).json()
    assert body["sections"] == SECTIONS and len(body["guides"]) == len(GUIDES)
    slugs = [g["slug"] for g in body["guides"]]
    assert len(slugs) == len(set(slugs)) and slugs[0] == "tour"
    for g in body["guides"]:
        assert g["section"] in SECTIONS and g["summary"] and g["page"].startswith("/") and g["minutes"] >= 1
        assert g["headings"] and all(h["id"] and h["text"] for h in g["headings"])
    assert body["files"]["API.md"] == "api"


def test_one_guide_returns_markdown_with_neighbours_and_unknown_is_404(client, headers):
    g = client.get("/v1/docs/deployment", headers=headers).json()
    assert g["markdown"].startswith("# Deployment") and g["title"] == "Deployment"
    assert g["prev"]["slug"] == "security" and g["next"] is None
    assert {"text": "3. Deploy in one command", "id": "3-deploy-in-one-command"} in g["headings"]
    first = client.get("/v1/docs/tour", headers=headers).json()
    assert first["prev"] is None and first["next"]["slug"] == "workflows"
    assert client.get("/v1/docs/nope", headers=headers).status_code == 404


def test_images_are_served_and_paths_are_constrained(client, headers):
    r = client.get("/v1/docs/images/deployment.png", headers=headers)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert client.get("/v1/docs/images/..%2FAPI.md", headers=headers).status_code in (404, 422)
    assert client.get("/v1/docs/images/nope.png", headers=headers).status_code == 404


def test_search_finds_paragraphs_with_a_section_anchor(client, headers):
    hits = client.get("/v1/docs/search?q=azd deploy", headers=headers).json()["hits"]
    assert hits and hits[0]["slug"] == "cloud-platforms" and "azd" in hits[0]["snippet"].lower()
    assert all({"slug", "title", "section", "anchor", "snippet", "score"} <= set(h) for h in hits)
    assert client.get("/v1/docs/search?q=zzqqxx", headers=headers).json()["hits"] == []
    assert client.get("/v1/docs/search?q=", headers=headers).status_code == 422
    assert search("a") == []


def test_heading_ids_match_the_renderer_convention():
    assert slugify("3. Deploy in one command") == "3-deploy-in-one-command"
    assert slugify("Two ways to build: `code` and low-code") == "two-ways-to-build-code-and-low-code"
    md = "## One\n```\n## not a heading\n```\n## Two words"
    assert headings(md) == [{"text": "One", "id": "one"}, {"text": "Two words", "id": "two-words"}]
    assert Path(docs_dir() / "API.md").exists()
