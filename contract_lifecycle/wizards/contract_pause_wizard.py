# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ContractPauseWizard(models.TransientModel):
    _name = "contract.pause.wizard"
    _description = "Pause Contract Wizard"

    contract_id = fields.Many2one(
        comodel_name="contract.contract",
        required=True,
        ondelete="cascade",
    )
    start_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )
    end_date = fields.Date()
    is_indefinite = fields.Boolean(
        string="Indefinite pause",
        help="If checked, the contract remains paused until it is resumed "
        "manually.",
    )
    reason_id = fields.Many2one(
        comodel_name="contract.pause.reason",
        string="Pause Reason",
        required=True,
    )
    requires_comment = fields.Boolean(
        related="reason_id.requires_comment",
    )
    comment = fields.Text()

    def action_pause(self):
        self.ensure_one()
        self.contract_id._pause_contract(
            self.start_date,
            self.end_date,
            self.is_indefinite,
            self.reason_id,
            self.comment,
        )
        return self.contract_id.get_formview_action()
