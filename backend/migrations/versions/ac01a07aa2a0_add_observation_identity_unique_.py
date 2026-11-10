"""add_observation_identity_unique_constraint

Revision ID: ac01a07aa2a0
Revises: 8c02fcee9d21
Create Date: 2026-11-10 15:32:24.121486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'ac01a07aa2a0'
down_revision: Union[str, None] = '8c02fcee9d21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Defensively verify that no duplicate observations exist in historical data
    conn = op.get_bind()
    duplicate_check = conn.execute(
        sa.text(
            """
            SELECT farm_id, zone_id, observation_type, source, observed_at, count(*) AS dup_count
            FROM observations
            GROUP BY farm_id, zone_id, observation_type, source, observed_at
            HAVING count(*) > 1;
            """
        )
    ).fetchall()

    if duplicate_check:
        dup_details = "; ".join(
            f"farm={row.farm_id}, zone={row.zone_id}, type={row.observation_type}, src={row.source}, ts={row.observed_at} (count={row.dup_count})"
            for row in duplicate_check[:5]
        )
        raise RuntimeError(
            f"Cannot apply unique constraint: {len(duplicate_check)} duplicate observation group(s) exist in historical data. "
            f"Review duplicates first without deleting or modifying records silently: {dup_details}"
        )

    # 2. Add uniqueness constraint with NULLS NOT DISTINCT
    op.create_unique_constraint(
        'uq_observations_identity',
        'observations',
        ['farm_id', 'zone_id', 'observation_type', 'source', 'observed_at'],
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    op.drop_constraint('uq_observations_identity', 'observations', type_='unique')
