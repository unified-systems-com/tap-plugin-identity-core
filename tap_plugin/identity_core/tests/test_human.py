"""Behaviour tests for identity_core__human and HELD_BY_HUMAN (req-identity-core-human)."""

from __future__ import annotations

import pytest
from tap_plugin.identity_core.models import Human

from tap_grid.caller_context import CallerContext
from tap_grid.models import Entity
from tap_grid.services import WriteOperation, write_batch

TYPE = "identity_core__human"


def _write(op: WriteOperation) -> object:
    return write_batch([op], caller_context=CallerContext()).results[0]


def _create(payload: dict) -> object:
    return _write(WriteOperation(verb="create_node", type_slug=TYPE, payload=payload))


@pytest.mark.django_db
class TestHuman:
    def test_create_with_handle_only(self) -> None:
        """req-identity-core-human-1: a handle alone is enough; name stays blank (not observed)."""
        result = _create({"handle": "e1042"})
        assert result.success
        human = Human.all_objects.get(entity_id=result.entity_id)
        assert human.handle == "e1042"
        assert human.name == ""

    def test_handle_required(self) -> None:
        """req-identity-core-human-2."""
        assert not _create({"name": "Ada Lovelace"}).success

    def test_display_name_prefers_name(self) -> None:
        named = _create({"handle": "e1042", "name": "Ada Lovelace"})
        assert Entity.objects.get(pk=named.entity_id).name == "Ada Lovelace"
        bare = _create({"handle": "e2001"})
        assert Entity.objects.get(pk=bare.entity_id).name == "e2001"

    def test_no_configuration_blob(self) -> None:
        """req-identity-core-human-3: no free-form field to collect personal data into."""
        assert not _create({"handle": "e1042", "configuration": {"ssn": "x"}}).success

    def test_any_account_type_can_be_held_by_a_human(self) -> None:
        """req-identity-core-human-4: the edge's source is wildcard, so a type from another plugin
        (here identity_core's own organization, standing in for a vendor account) can point at a human."""
        human = _create({"handle": "e1042"})
        other = _write(
            WriteOperation(verb="create_node", type_slug="identity_core__organization", payload={"name": "x"})
        )
        edge = _write(
            WriteOperation(
                verb="create_edge",
                from_target=other.entity_id,
                to_target=human.entity_id,
                edge_type="HELD_BY_HUMAN__identity_core",
                payload={"properties": {"matched_on": "operator seed"}},
            )
        )
        assert edge.success, edge


def test_keyed_by_handle() -> None:
    assert Human.NATURAL_KEY == ("handle",)
    assert "handle" in {f.name for f in Human._meta.get_fields()}
