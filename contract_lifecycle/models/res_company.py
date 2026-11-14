# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _default_enable_refund_on_stop(self):
        return True

    # Re-declare the OCA field to give new companies the credit-note behavior
    # required by the lifecycle pause and termination flows.
    enable_contract_line_refund_on_stop = fields.Boolean(
        default=lambda self: self._default_enable_refund_on_stop(),
    )
