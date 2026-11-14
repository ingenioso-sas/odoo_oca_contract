# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ContractResumeWizard(models.TransientModel):
    _name = "contract.resume.wizard"
    _description = "Resume Contract Wizard"

    contract_id = fields.Many2one(
        comodel_name="contract.contract",
        required=True,
        ondelete="cascade",
    )
    pause_id = fields.Many2one(
        comodel_name="contract.pause",
        required=True,
        domain="[('contract_id', '=', contract_id), ('state', '=', 'active'), "
        "('is_indefinite', '=', True)]",
    )
    resume_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )

    def action_resume(self):
        self.ensure_one()
        self.contract_id._resume_contract(self.pause_id, self.resume_date)
        return self.contract_id.get_formview_action()
