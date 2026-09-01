"""Google Antigravity ACP provider profile.

antigravity-acp uses an external ACP subprocess (the official Google
Antigravity ACP kernel, agy_acp_server.par) — NOT the standard transport.
api_mode="chat_completions" and the ACP wire protocol are handled by
agent.copilot_acp_client (same generic client as copilot-acp). The profile
captures auth + endpoint metadata for registry migration.
"""

from providers import register_provider
from providers.base import ProviderProfile


class AntigravityACPProfile(ProviderProfile):
    """Google Antigravity ACP — external process, no REST models endpoint."""

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        """Model listing is handled by the ACP subprocess."""
        return None


antigravity_acp = AntigravityACPProfile(
    name="antigravity-acp",
    aliases=("antigravity", "agy-acp", "antigravity-acp-agent"),
    api_mode="chat_completions",  # ACP subprocess uses chat_completions routing
    env_vars=(),  # Managed by ACP subprocess
    base_url="acp://antigravity",  # ACP internal scheme
    auth_type="external_process",
    display_name="Google Antigravity ACP",
    description="Google Antigravity via ACP kernel (agy_acp_server.par)",
    supports_health_check=False,
)

register_provider(antigravity_acp)