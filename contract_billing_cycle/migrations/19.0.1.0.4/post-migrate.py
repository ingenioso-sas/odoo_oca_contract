# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Copy the old full-period trial setting to the new duration fields."""
    if not version:
        return
    for table in ("contract_template", "contract_contract"):
        cr.execute(
            f"ALTER TABLE {table} ALTER COLUMN billing_anchor_day SET DEFAULT 1"
        )
        cr.execute(
            f"ALTER TABLE {table} ALTER COLUMN free_trial_duration SET DEFAULT 0"
        )
        cr.execute(
            f"ALTER TABLE {table} ALTER COLUMN free_trial_unit "
            "SET DEFAULT 'months'"
        )
        cr.execute(
            f"ALTER TABLE {table} ALTER COLUMN free_trial_discount "
            "SET DEFAULT 100"
        )
        cr.execute(
            f"ALTER TABLE {table} ALTER COLUMN skip_zero_invoices "
            "SET DEFAULT false"
        )
        cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = %s
               AND column_name = 'free_trial_periods'
            """,
            (table,),
        )
        if not cr.fetchone():
            continue
        cr.execute(
            f"""
            UPDATE {table}
               SET free_trial_duration = free_trial_periods,
                   free_trial_unit = 'months'
             WHERE free_trial_periods > 0
               AND free_trial_duration = 0
            """
        )
        cr.execute(f"ALTER TABLE {table} DROP COLUMN free_trial_periods")
