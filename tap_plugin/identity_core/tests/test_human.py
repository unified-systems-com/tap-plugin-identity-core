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

    def test_edge_source_is_unrestricted(self) -> None:
        """req-identity-core-human-4: the source is wildcard, so the schema accepts any type, not only
        accounts. An organization is not an account, and the write still succeeds: keeping the source an
        account is the drawer's job, which is what the edge description and the spec say."""
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


    def test_a_shared_account_points_at_two_humans(self) -> None:
        """req-identity-core-human-5: one account held by two people is recorded, not refused."""
        from tap_grid.models import Edge

        a, b = _create({"handle": "e1"}), _create({"handle": "e2"})
        account = _write(
            WriteOperation(verb="create_node", type_slug="identity_core__organization", payload={"name": "shared"})
        )
        for human in (a, b):
            edge = _write(
                WriteOperation(
                    verb="create_edge",
                    from_target=account.entity_id,
                    to_target=human.entity_id,
                    edge_type="HELD_BY_HUMAN__identity_core",
                )
            )
            assert edge.success, edge
        held = Edge.objects.filter(from_entity_id=account.entity_id, edge_type="HELD_BY_HUMAN__identity_core")
        assert {str(e.to_entity_id) for e in held} == {str(a.entity_id), str(b.entity_id)}

def test_keyed_by_handle() -> None:
    assert Human.NATURAL_KEY == ("handle",)
    assert "handle" in {f.name for f in Human._meta.get_fields()}
