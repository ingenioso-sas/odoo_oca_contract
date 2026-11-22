# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    contract_discount_id = fields.Many2one(
        comodel_name="contract.invoice.discount",
        string="Contract Discount Rule",
        readonly=True,
        copy=False,
        ondelete="set null",
        index=True,
    )
    contract_discount_name = fields.Char(
        string="Contract Discount",
        readonly=True,
        copy=False,
    )
    contract_discount_percent = fields.Float(
        string="Applied Contract Discount (%)",
        digits="Discount",
        readonly=True,
        copy=False,
    )
    contract_discount_until = fields.Date(
        string="Contract Discount Until",
        readonly=True,
        copy=False,
    )
    contract_discount_source = fields.Selection(
        selection=[
            ("promotion", "Promotion"),
            ("referral", "Referral"),
            ("manual", "Manual"),
        ],
        string="Contract Discount Source",
        readonly=True,
        copy=False,
    )
