"""Import every blueprint module so the registry is populated once. Order here is the Agent Hub order."""
# ruff: noqa: I001

from app.agents import core
from app.agents.blueprints import (  # noqa: F401
    doc_reconciliation,
    sage_lens,
    learning_path,
    review_panel,
    data_analyst,
    knowledge_qa,
    adoption_digest,
    showcase_writer,
    key_health,
    cost_sentinel,
    connector_reviewer,
    onboarding_coach,
    prompt_agent,
)


def all_blueprints() -> list[dict]:
    """Executable blueprints shown in the Agent Hub; the generic runner stays internal."""
    return [bp.manifest() for bp in core.REGISTRY.values() if bp.family != "Runtime"]
