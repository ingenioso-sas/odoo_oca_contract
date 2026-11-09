# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines.filtered(
            lambda line: not line.display_type and line.contract_id
        ):
            referrals = self.env["contract.referral"].search(
                [
                    ("referred_contract_id", "=", line.contract_id.id),
                    ("state", "=", "active"),
                ]
            )
            for referral in referrals:
                referral._sync_rule_for_line(line)
        return lines
