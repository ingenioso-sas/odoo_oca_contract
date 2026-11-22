# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    opt_out_overdue_reminder = fields.Boolean(
        string="Opt out of overdue reminders",
        help="If checked, this contact will not receive overdue contract "
        "invoice reminders (by email or WhatsApp).",
    )
