# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    opt_out_overdue_reminder = fields.Boolean(
        string="No overdue reminders",
        help="If checked, overdue digest reminders are never sent "
        "to this contact (WhatsApp/email).",
    )
