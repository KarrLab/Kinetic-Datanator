"""empty message

Revision ID: 8a896a87fe1c
Revises: 
Create Date: 2018-03-07 12:41:01.020817

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a896a87fe1c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('protein_subunit', sa.Column('uniprot_checked', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('protein_subunit', 'uniprot_checked')
    # ### end Alembic commands ###