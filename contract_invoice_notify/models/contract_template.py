# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ContractTemplate(models.Model):
    _inherit = "contract.template"

    notification_channel_ids = fields.Many2many(
        string="Notification Channels",
        comodel_name="contract.notification.channel",
        default=lambda self: self._default_notification_channel_ids(),
        help="Channels copied to contracts created from this template.",
    )
    overdue_reminder_enabled = fields.Boolean(
        default=False,
        string="Overdue reminders",
        help="Send periodic digest reminders for overdue invoices of this contract.",
    )
    overdue_grace_days = fields.Integer(
        default=3,
        string="Grace days",
        help="Days after due date before an invoice counts as overdue.",
    )
    overdue_resend_after_days = fields.Integer(
        default=7,
        string="Resend every (days)",
        help="Minimum days between two digest reminders including same invoice.",
    )
    overdue_max_reminders = fields.Integer(
        default=4,
        string="Max reminders",
        help="Max digest reminders per invoice. 0 = unlimited.",
    )

    @api.model
    def _default_notification_channel_ids(self):
        channel = self.env.ref(
            "contract_invoice_notify.notification_channel_email",
            raise_if_not_found=False,
        )
        return channel or self.env["contract.notification.channel"]
