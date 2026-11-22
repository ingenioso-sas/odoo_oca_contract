# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import Command, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    invoice_discount_count = fields.Integer(
        compute="_compute_invoice_discount_count",
        string="Invoice Discounts",
    )

    def _compute_invoice_discount_count(self):
        real_ids = [rec_id for rec_id in self._ids if isinstance(rec_id, int)]
        if not real_ids:
            for contract in self:
                contract.invoice_discount_count = len(
                    contract.contract_line_ids.mapped("invoice_discount_ids").filtered(
                        "active"
                    )
                )
            return
        grouped = self.env["contract.invoice.discount"]._read_group(
            domain=[("contract_id", "in", real_ids), ("active", "=", True)],
            groupby=["contract_id"],
            aggregates=["__count"],
        )
        counts = {contract.id: count for contract, count in grouped}
        for contract in self:
            contract.invoice_discount_count = counts.get(contract.id, 0)

    def action_show_invoice_discounts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Invoice Discounts"),
            "res_model": "contract.invoice.discount",
            "view_mode": "list,form",
            "domain": [("contract_id", "=", self.id)],
            "context": {
                "default_contract_id": self.id,
                "active_test": False,
            },
        }

    def _convert_contract_lines(self, contract):
        """Copy promotional defaults from contract template lines."""
        new_lines = super()._convert_contract_lines(contract)
        for new_line in new_lines:
            if new_line.display_type or not new_line.promo_discount:
                continue
            date_start = new_line.date_start or fields.Date.context_today(self)
            date_end = False
            if new_line.promo_duration_months:
                date_end = (
                    date_start
                    + relativedelta(months=new_line.promo_duration_months)
                    - relativedelta(days=1)
                )
            new_line.invoice_discount_ids = [
                Command.create(
                    {
                        "name": new_line.promo_name or self.env._("Promotion"),
                        "discount": new_line.promo_discount,
                        "start_mode": "contract_start",
                        "date_start": date_start,
                        "date_end": date_end,
                        "max_invoices": new_line.promo_max_invoices,
                        "source": "promotion",
                    }
                )
            ]
        return new_lines
