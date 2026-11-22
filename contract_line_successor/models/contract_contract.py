# Copyright 2025 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    line_recurrence = fields.Boolean(default=True)

    @api.depends(
        "contract_line_ids.date_end",
        "contract_line_ids.is_canceled",
        "contract_line_ids.display_type",
    )
    def _compute_date_end(self):
        for contract in self:
            contract.date_end = False
            date_end = contract.contract_line_ids.filtered(
                lambda line: not line.display_type and not line.is_canceled
            ).mapped("date_end")
            if date_end and all(date_end):
                contract.date_end = max(date_end)

    @api.depends(
        "contract_line_ids.monthly_recurring",
        "contract_line_ids.is_canceled",
        "contract_line_ids.display_type",
        "contract_line_ids.successor_contract_line_id",
    )
    def _compute_recurring_monthly_total(self):
        for contract in self:
            contract.recurring_monthly_total = sum(
                contract.contract_line_ids.filtered(
                    lambda line: not line.display_type
                    and not line.is_canceled
                    and not line.successor_contract_line_id
                ).mapped("monthly_recurring")
            )

    def _convert_contract_lines(self, contract):
        new_lines = super()._convert_contract_lines(contract)
        new_lines._onchange_is_auto_renew()
        return new_lines
