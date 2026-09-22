"""Identity Core plugin models package."""

from tap_plugin.identity_core.models.oidc_issuer import OidcIssuer
from tap_plugin.identity_core.models.organization import Organization

__all__ = [
    "OidcIssuer",
    "Organization",
]
