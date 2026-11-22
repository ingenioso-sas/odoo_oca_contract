# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class ContractLine(models.Model):
    _inherit = "contract.line"

    def _prepare_invoice_line(self):
        """Add the contract billing period to the generated invoice line.

        The period is calculated before ``last_date_invoiced`` is updated, so
        the invoice keeps the exact dates that were billed. Without these
        fields the information is lost as soon as the contract advances.
        """
        vals = super()._prepare_invoice_line()
        if not vals or self.display_type:
            return vals
        refund_period = self.env.context.get("contract_refund_period")
        if refund_period:
            period_start, period_end = refund_period
            billing_date = period_start
        else:
            period_start, period_end, _billing_date = self._get_period_to_invoice(
                self.last_date_invoiced, self.recurring_next_date
            )
            billing_date = self.recurring_next_date
        vals.update(
            {
                "contract_billing_date": billing_date,
                "contract_period_start": period_start,
                "contract_period_end": period_end,
            }
        )
        return vals
