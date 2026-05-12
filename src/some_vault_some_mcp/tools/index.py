"""Index tools: vault_index_status, vault_reindex."""

import logging

from some_vault_some_mcp.core.indexer import get_index_status, incremental_index
from some_vault_some_mcp.models import IndexStatus, ReindexResult

logger = logging.getLogger(__name__)


def vault_index_status(vault_path: str, db_path: str, provider_dims: int | None = None) -> IndexStatus:
    info = get_index_status(vault_path, db_path, provider_dims)
    return IndexStatus(**info)


def vault_reindex(
    vault_path: str,
    db_path: str,
    provider,
    single_file: str | None = None,
) -> ReindexResult:
    """Trigger incremental reindex. Limits to single_file if provided."""
    result = incremental_index(
        vault_path=vault_path,
        db_path=db_path,
        provider=provider,
        single_file=single_file,
    )
    return ReindexResult(**result)
