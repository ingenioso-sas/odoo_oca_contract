# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    contract_billing_date = fields.Date(
        string="Contract Billing Date",
        readonly=True,
        copy=True,
        index=True,
        help="Date of the next contract invoice used to generate this line.",
    )
    contract_period_start = fields.Date(
        string="Contract Period Start",
        readonly=True,
        copy=True,
        index=True,
        help="First date of the period covered by this contract invoice line.",
    )
    contract_period_end = fields.Date(
        string="Contract Period End",
        readonly=True,
        copy=True,
        index=True,
        help="Last date of the period covered by this contract invoice line.",
    )
