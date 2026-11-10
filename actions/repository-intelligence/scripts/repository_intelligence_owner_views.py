# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Closed, optional owner-view presentation dispatch.

The fixed generator chooses these modules. Input documents cannot select code,
install providers, change policy, or grant human ratification authority.
"""

from __future__ import annotations

import importlib.util
from html.parser import HTMLParser
from pathlib import Path


VIEWS = {
    "hygiene": {"provenance": "hygiene_conformance", "module": "render_repository_intelligence_hygiene.py",
                "input_label": "Observatory conformance", "loaded_label": "Observatory conformance model loaded",
                "availability": "Assessed contract evidence supplied; applicability inventory unknown."},
    "audits": {"provenance": "audit_evidence", "module": "render_repository_intelligence_audits.py",
               "input_label": "Observatory audit evidence", "loaded_label": "Observatory audit model loaded",
               "availability": "Supplied audit evidence; findings retain their classification and uncertainty."},
    "sanity": {"provenance": "architecture_coherence", "module": "render_repository_intelligence_sanity.py",
               "input_label": "Observatory architecture review", "loaded_label": "Observatory coherence model loaded",
               "availability": "Supplied architecture review evidence; human ratification remains separate."},
}


def filter_choices(body):
    """Derive presentation choices from our rendered public record attributes."""
    class Choices(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.values = {"state": set(), "kind": set()}

        def handle_starttag(self, tag, attributes):
            attributes = dict(attributes)
            if "data-filter-item" not in attributes:
                return
            for dimension in self.values:
                value = attributes.get("data-" + dimension)
                if value:
                    if len(value) > 128 or value not in self.values[dimension] and len(self.values[dimension]) >= 128:
                        raise ValueError("Owner filter choices are incompatible")
                    self.values[dimension].add(value)

    parser = Choices()
    parser.feed(body)
    parser.close()
    return {dimension: sorted(values) for dimension, values in parser.values.items()}


def helper(identifier):
    if identifier not in VIEWS:
        raise ValueError("Owner view selection is incompatible")
    path = Path(__file__).with_name(VIEWS[identifier]["module"])
    specification = importlib.util.spec_from_file_location("relay_owner_view_" + identifier, path)
    if specification is None or specification.loader is None:
        raise ValueError("Owner view renderer is unavailable")
    value = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(value)
    return value


def validate_receipts(provenance, repository, source_commit):
    """Return supported views only after their exact public owner proof passes."""
    present = {identifier: definition for identifier, definition in VIEWS.items()
               if definition["provenance"] in provenance}
    if present and provenance["consumer"]["visibility"] != "public":
        raise ValueError("Owner views require public consumer evidence")
    values = {}
    for identifier, definition in present.items():
        receipt = provenance[definition["provenance"]]
        helper(identifier).validate_receipt(receipt, repository, source_commit, provenance["generated_at"])
        values[identifier] = receipt
    return values
