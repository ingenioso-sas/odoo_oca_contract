# Copyright 2025 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ContractTemplateLine(models.Model):
    _inherit = "contract.template.line"

    is_auto_renew = fields.Boolean(string="Auto Renew", default=False)
    auto_renew_interval = fields.Integer(
        string="Renew Every",
        default=1,
        help="Renew every (Days/Weeks/Months/Years)",
    )
    auto_renew_rule_type = fields.Selection(
        [
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("yearly", "Year(s)"),
        ],
        default="yearly",
        string="Renewal type",
        help="Specify interval for automatic renewal.",
    )
    termination_notice_interval = fields.Integer(
        default=1,
        string="Termination Notice Before",
    )
    termination_notice_rule_type = fields.Selection(
        [("daily", "Day(s)"), ("weekly", "Week(s)"), ("monthly", "Month(s)")],
        default="monthly",
        string="Termination Notice type",
    )

    @api.constrains("auto_renew_interval", "termination_notice_interval")
    def _check_renewal_intervals(self):
        for rec in self:
            if rec.auto_renew_interval <= 0:
                raise ValidationError(
                    self.env._("Auto-renew interval must be greater than zero.")
                )
            if rec.termination_notice_interval < 0:
                raise ValidationError(
                    self.env._("Termination notice interval cannot be negative.")
                )
