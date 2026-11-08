# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ContractNotificationTemplate(models.Model):
    _name = "contract.notification.template"
    _description = "Contract Notification Template Override"
    _order = "channel_id, purpose, id"

    contract_id = fields.Many2one(
        string="Contract",
        comodel_name="contract.contract",
        required=True,
        ondelete="cascade",
    )
    channel_id = fields.Many2one(
        string="Channel",
        comodel_name="contract.notification.channel",
        required=True,
        ondelete="cascade",
    )
    purpose = fields.Selection(
        string="Purpose",
        selection=[
            ("invoice_notification", "Invoice notification"),
            ("overdue_digest", "Overdue digest"),
        ],
        required=True,
    )
    template_id = fields.Many2one(
        string="Mail Template",
        comodel_name="mail.template",
        required=True,
        ondelete="cascade",
    )

    _contract_channel_purpose_uniq = models.Constraint(
        "unique(contract_id, channel_id, purpose)",
        "There is already a template for this contract, channel and purpose.",
    )
