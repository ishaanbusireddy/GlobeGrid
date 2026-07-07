"""Section 4.1 — RSS ingestion (stdlib xml.etree, no feedparser needed).

Handles both RSS 2.0 (<item>) and Atom (<entry>) since NPR/Google News mix
formats. Returns normalized payload dicts for raw_items.raw_content.
"""

import xml.etree.ElementTree as ET

from ..http import fetch_url

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _text(elem, *names):
    for name in names:
        child = elem.find(name)
        if child is not None and (child.text or "").strip():
            return child.text.strip()
    return ""


def fetch(source: dict) -> list[dict]:
    body = fetch_url(source["url"])
    root = ET.fromstring(body)
    items = []

    for item in root.iter("item"):  # RSS 2.0
        link = _text(item, "link") or _text(item, "guid")
        items.append({
            "title": _text(item, "title"),
            "summary": _text(item, "description"),
            "link": link,
            "published": _text(item, "pubDate") or _text(item, "date"),
            "external_id": _text(item, "guid") or link or _text(item, "title"),
        })

    if not items:  # Atom
        for entry in root.iter(f"{ATOM_NS}entry"):
            link_el = entry.find(f"{ATOM_NS}link")
            link = link_el.get("href", "") if link_el is not None else ""
            items.append({
                "title": _text(entry, f"{ATOM_NS}title"),
                "summary": _text(entry, f"{ATOM_NS}summary", f"{ATOM_NS}content"),
                "link": link,
                "published": _text(entry, f"{ATOM_NS}updated", f"{ATOM_NS}published"),
                "external_id": _text(entry, f"{ATOM_NS}id") or link,
            })

    return [i for i in items if i["title"]][:50]
