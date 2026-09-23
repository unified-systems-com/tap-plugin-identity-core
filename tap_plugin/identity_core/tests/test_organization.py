"""Behaviour tests for identity_core__organization (req-identity-core-organization)."""

from __future__ import annotations

import pytest
from tap_plugin.identity_core.models import Organization

from tap_grid.caller_context import CallerContext
from tap_grid.models import Entity
from tap_grid.services import WriteOperation, write_batch

TYPE = "identity_core__organization"


def _create(payload: dict) -> object:
    return write_batch(
        [WriteOperation(verb="create_node", type_slug=TYPE, payload=payload)],
        caller_context=CallerContext(),
    ).results[0]


@pytest.mark.django_db
class TestOrganization:
    def test_create_with_name_only(self) -> None:
        """req-identity-core-organization-1: a designed organization needs only its name."""
        result = _create({"name": "Acme Federal"})
        assert result.success
        org = Organization.all_objects.get(entity_id=result.entity_id)
        assert org.name == "Acme Federal"
        assert org.domain == ""

    def test_name_required(self) -> None:
        """req-identity-core-organization-2."""
        assert not _create({"domain": "acme.example"}).success

    def test_entity_name_is_name(self) -> None:
        result = _create({"name": "Acme Federal", "domain": "acme.example"})
        assert Entity.objects.get(pk=result.entity_id).name == "Acme Federal"

    def test_no_role_dimension(self) -> None:
        """req-identity-core-organization-3: role-free — no default dimension names a role."""
        result = _create({"name": "Acme Federal"})
        assert Entity.objects.get(pk=result.entity_id).dimensions == {}


def test_keyed_by_a_carried_field() -> None:
    assert Organization.NATURAL_KEY == ("name",)
    names = {f.name for f in Organization._meta.get_fields()}
    assert all(k in names for k in Organization.NATURAL_KEY)
