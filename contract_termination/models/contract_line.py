# Copyright 2025 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    @api.depends("contract_id.is_terminated")
    def _compute_allowed(self):
        terminated_lines = self.filtered("contract_id.is_terminated")
        if terminated_lines:
            terminated_lines.update(
                {
                    "is_plan_successor_allowed": False,
                    "is_stop_plan_successor_allowed": False,
                    "is_stop_allowed": False,
                    "is_cancel_allowed": False,
                    "is_un_cancel_allowed": False,
                }
            )
        remaining = self - terminated_lines
        if remaining:
            super(ContractLine, remaining)._compute_allowed()
        return True

    @api.model
    def _contract_line_to_renew_domain(self):
        return [
            ("contract_id.is_terminated", "=", False),
        ] + super()._contract_line_to_renew_domain()
