# Copyright 2016 Tecnativa - Pedro M. Baeza
# Copyright 2018 Tecnativa - Carlos Dauden
# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ContractTemplate(models.Model):
    _inherit = "contract.template"

    skip_zero_qty = fields.Boolean(
        string="Skip Zero Qty Lines",
        help="If checked, contract lines with 0 qty don't create invoice line",
    )
