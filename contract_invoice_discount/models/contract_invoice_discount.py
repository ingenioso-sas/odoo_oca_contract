# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ContractInvoiceDiscount(models.Model):
    _name = "contract.invoice.discount"
    _description = "Contract Invoice Discount"
    _order = "date_start, sequence, id"
    _check_company_auto = True

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    contract_line_id = fields.Many2one(
        comodel_name="contract.line",
        string="Contract Line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    contract_id = fields.Many2one(
        related="contract_line_id.contract_id",
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        related="contract_line_id.company_id",
        store=True,
        index=True,
    )
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        required=True,
        default=0.0,
        help="Percentage applied to the invoice line. Only the highest "
        "applicable discount is used.",
    )
    date_start = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )
    date_end = fields.Date(
        help="Leave empty for no date limit. If set, the discount is prorated "
        "when the invoice period overlaps only partially.",
    )
    max_invoices = fields.Integer(
        default=0,
        help="Maximum number of invoices with this discount. 0 = unlimited.",
    )
    source = fields.Selection(
        selection=[
            ("promotion", "Promotion"),
            ("referral", "Referral"),
            ("manual", "Manual"),
        ],
        default="promotion",
        required=True,
    )
    active = fields.Boolean(default=True)
    applied_invoice_count = fields.Integer(
        compute="_compute_applied_invoice_count",
        string="Applied Invoices",
    )
    remaining_invoices = fields.Integer(
        compute="_compute_applied_invoice_count",
        string="Remaining Invoices",
    )
    state = fields.Selection(
        selection=[
            ("scheduled", "Scheduled"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("exhausted", "Exhausted"),
            ("inactive", "Inactive"),
        ],
        compute="_compute_state",
    )

    @api.constrains("discount")
    def _check_discount(self):
        for rule in self:
            if rule.discount < 0 or rule.discount > 100:
                raise ValidationError(
                    self.env._("Discount must be between 0 and 100.")
                )

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rule in self:
            if rule.date_end and rule.date_end < rule.date_start:
                raise ValidationError(
                    self.env._("Discount end date cannot be before start date.")
                )

    @api.constrains("max_invoices")
    def _check_max_invoices(self):
        for rule in self:
            if rule.max_invoices < 0:
                raise ValidationError(
                    self.env._("Maximum invoices cannot be negative.")
                )

    def _get_applied_invoice_count(self):
        """Count invoices directly to avoid stale computed caches."""
        self.ensure_one()
        moves = self.env["account.move"].search(
            [
                ("invoice_line_ids.contract_discount_id", "=", self.id),
                ("state", "!=", "cancel"),
            ]
        )
        return len(moves)

    @api.depends("max_invoices")
    def _compute_applied_invoice_count(self):
        for rule in self:
            applied_count = rule._get_applied_invoice_count()
            rule.applied_invoice_count = applied_count
            if rule.max_invoices:
                rule.remaining_invoices = max(
                    rule.max_invoices - applied_count, 0
                )
            else:
                rule.remaining_invoices = 0

    @api.depends(
        "active",
        "date_start",
        "date_end",
        "max_invoices",
        "applied_invoice_count",
    )
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rule in self:
            if not rule.active:
                rule.state = "inactive"
            elif rule.date_start and rule.date_start > today:
                rule.state = "scheduled"
            elif rule.date_end and rule.date_end < today:
                rule.state = "expired"
            elif (
                rule.max_invoices
                and rule._get_applied_invoice_count() >= rule.max_invoices
            ):
                rule.state = "exhausted"
            else:
                rule.state = "active"

    def _check_conditions(self, period_start, period_end):
        """Hook for modules adding business conditions (e.g. referrals)."""
        self.ensure_one()
        return True

    def _get_overlap_days(self, period_start, period_end):
        self.ensure_one()
        if not period_start or not period_end:
            return 0
        start = max(period_start, self.date_start)
        end = min(period_end, self.date_end or period_end)
        if start > end:
            return 0
        return (end - start).days + 1

    def _get_effective_discount(self, period_start, period_end):
        """Return the prorated discount for the given invoice period."""
        self.ensure_one()
        if not self.active:
            return 0.0
        if (
            self.max_invoices
            and self._get_applied_invoice_count() >= self.max_invoices
        ):
            return 0.0
        if self.date_end and self.date_start > self.date_end:
            return 0.0
        overlap_days = self._get_overlap_days(period_start, period_end)
        if not overlap_days:
            return 0.0
        period_days = (period_end - period_start).days + 1
        if period_days <= 0:
            return 0.0
        return round(self.discount * overlap_days / period_days, 2)
