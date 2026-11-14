# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    contract_id = fields.Many2one(
        comodel_name="contract.contract",
        string="Contract",
        compute="_compute_contract_id",
        store=True,
        index=True,
        readonly=True,
        copy=False,
        help="Contract that originated this invoice. Empty when the invoice "
        "was not generated from a contract.",
    )
    contract_billing_date = fields.Date(
        string="Contract Billing Date",
        compute="_compute_contract_period",
        store=True,
        index=True,
        readonly=True,
        copy=False,
        help="Contract next invoice date used to generate this invoice.",
    )
    contract_period_start = fields.Date(
        string="Contract Period Start",
        compute="_compute_contract_period",
        store=True,
        index=True,
        readonly=True,
        copy=False,
        help="First date of the invoiced period. For invoices with lines from "
        "different periods it is the earliest start date.",
    )
    contract_period_end = fields.Date(
        string="Contract Period End",
        compute="_compute_contract_period",
        store=True,
        index=True,
        readonly=True,
        copy=False,
        help="Last date of the invoiced period. For invoices with lines from "
        "different periods it is the latest end date.",
    )

    @api.depends(
        "invoice_line_ids.display_type",
        "invoice_line_ids.contract_line_id.contract_id",
    )
    def _compute_contract_id(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type in (False, "product")
            )
            contracts = lines.mapped("contract_line_id.contract_id")
            move.contract_id = contracts if len(contracts) == 1 else False

    @api.depends(
        "invoice_line_ids.display_type",
        "invoice_line_ids.contract_billing_date",
        "invoice_line_ids.contract_period_start",
        "invoice_line_ids.contract_period_end",
    )
    def _compute_contract_period(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type in (False, "product")
            )
            billing_dates = [
                value
                for value in lines.mapped("contract_billing_date")
                if value
            ]
            period_starts = [
                value for value in lines.mapped("contract_period_start") if value
            ]
            period_ends = [
                value for value in lines.mapped("contract_period_end") if value
            ]
            move.contract_billing_date = (
                min(billing_dates) if billing_dates else False
            )
            move.contract_period_start = (
                min(period_starts) if period_starts else False
            )
            move.contract_period_end = max(period_ends) if period_ends else False
