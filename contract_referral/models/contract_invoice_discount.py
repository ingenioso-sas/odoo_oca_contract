# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ContractInvoiceDiscount(models.Model):
    _inherit = "contract.invoice.discount"

    referral_id = fields.Many2one(
        comodel_name="contract.referral",
        string="Referral",
        ondelete="cascade",
        index=True,
        copy=False,
        check_company=True,
    )

    def _check_conditions(self, period_start, period_end):
        if not super()._check_conditions(period_start, period_end):
            return False
        if self.referral_id:
            return self.referral_id._check_referred_discount_condition(
                period_start, period_end
            )
        return True
