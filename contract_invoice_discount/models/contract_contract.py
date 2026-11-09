# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import Command, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

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
                        "date_start": date_start,
                        "date_end": date_end,
                        "max_invoices": new_line.promo_max_invoices,
                        "source": "promotion",
                    }
                )
            ]
        return new_lines
