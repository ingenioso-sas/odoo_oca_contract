# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ContractNotificationChannel(models.Model):
    _name = "contract.notification.channel"
    _description = "Contract Notification Channel"
    _order = "sequence, id"

    code = fields.Char(string="Code", required=True, index=True)
    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "unique(code)",
        "The notification channel code must be unique.",
    )
