# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if self.env.context.get("skip_referral_sync"):
            return lines
        eligible_lines = lines.filtered(
            lambda line: not line.display_type and line.contract_id
        )
        if not eligible_lines:
            return lines
        referrals = self.env["contract.referral"].search(
            [
                ("referred_contract_id", "in", eligible_lines.contract_id.ids),
                ("state", "=", "active"),
            ]
        )
        for line in eligible_lines:
            for referral in referrals.filtered(
                lambda r, c=line.contract_id: r.referred_contract_id == c
            ):
                referral._sync_rule_for_line(line)
        return lines
