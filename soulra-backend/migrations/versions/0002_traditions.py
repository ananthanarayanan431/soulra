"""traditions

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-07

"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

_SEED = [
    ("vedanta",          "Vedanta",           "India · ~800 BCE",          "ancient",   True),
    ("buddhism",         "Buddhism",          "India / E. Asia · ~500 BCE", "ancient",   True),
    ("taoism",           "Taoism",            "China · ~600 BCE",          "ancient",   False),
    ("stoicism",         "Stoicism",          "Greece · ~300 BCE",         "ancient",   True),
    ("jewish-wisdom",    "Jewish wisdom",     "Levant · ~500 BCE",         "ancient",   False),
    ("christian-mystic", "Christian mystics", "Europe · ~1200 CE",         "medieval",  False),
    ("sufism",           "Sufism",            "Persia · ~900 CE",          "medieval",  False),
    ("zen",              "Zen",               "Japan · ~1200 CE",          "medieval",  False),
    ("indigenous",       "Indigenous & earth","Many lineages",             "perennial", False),
]


def upgrade() -> None:
    op.create_table(
        "traditions",
        sa.Column("slug",          sa.String(80),  primary_key=True),
        sa.Column("name",          sa.String(120), nullable=False),
        sa.Column("origin",        sa.String(120), nullable=False),
        sa.Column("era",           sa.String(40),  nullable=False),
        sa.Column("user_selected", sa.Boolean(),   nullable=False, server_default=sa.false()),
        sa.Column("description",   sa.Text(),      nullable=True),
        sa.PrimaryKeyConstraint("slug"),
    )
    op.bulk_insert(
        sa.table(
            "traditions",
            sa.column("slug",          sa.String),
            sa.column("name",          sa.String),
            sa.column("origin",        sa.String),
            sa.column("era",           sa.String),
            sa.column("user_selected", sa.Boolean),
        ),
        [
            {"slug": slug, "name": name, "origin": origin, "era": era, "user_selected": sel}
            for slug, name, origin, era, sel in _SEED
        ],
    )


def downgrade() -> None:
    op.drop_table("traditions")
