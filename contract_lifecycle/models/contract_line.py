# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class ContractLine(models.Model):
    _inherit = "contract.line"

    def _can_be_invoiced(self, date_ref):
        if not super()._can_be_invoiced(date_ref):
            return False
        if self.contract_id.is_paused or self.contract_id.is_terminated:
            return False
        return True

    def _prepare_value_for_plan_successor(
        self,
        date_start,
        date_end,
        is_auto_renew,
        recurring_next_date=False,
    ):
        """Do not copy discount rules to the successor automatically.

        OCA copies all writable fields, including the one2many of discount
        rules. The lifecycle module copies those rules with adjusted dates and
        remaining invoice counts instead.
        """
        values = super()._prepare_value_for_plan_successor(
            date_start,
            date_end,
            is_auto_renew,
            recurring_next_date,
        )
        values.pop("invoice_discount_ids", None)
        return values
