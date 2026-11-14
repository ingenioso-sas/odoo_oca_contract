# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ContractPauseReason(models.Model):
    _name = "contract.pause.reason"
    _description = "Contract Pause Reason"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    requires_comment = fields.Boolean(
        help="If checked, the pause comment is mandatory."
    )
