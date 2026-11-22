# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ContractReferralCommission(models.Model):
    _name = "contract.referral.commission"
    _description = "Referral Commission"
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(compute="_compute_name", store=True)
    referral_id = fields.Many2one(
        comodel_name="contract.referral",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Referred Invoice",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
        domain=[("move_type", "in", ("out_invoice", "out_refund"))],
    )
    partner_id = fields.Many2one(
        related="referral_id.referrer_id",
        store=True,
        string="Referrer",
        index=True,
    )
    company_id = fields.Many2one(
        related="referral_id.company_id",
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        related="invoice_id.currency_id",
        store=True,
    )
    date = fields.Date(
        related="invoice_id.invoice_date",
        store=True,
    )
    is_adjustment = fields.Boolean(
        readonly=True,
        copy=False,
        help="True when this record reverses a commission because of a "
        "refund or credit note.",
    )
    base_amount = fields.Monetary(
        string="Commission Base",
        currency_field="currency_id",
        readonly=True,
    )
    commission_percent = fields.Float(
        string="Commission (%)",
        digits="Discount",
        readonly=True,
    )
    commission_amount = fields.Monetary(
        string="Commission Amount",
        compute="_compute_commission_amount",
        store=True,
        currency_field="currency_id",
    )
    invoice_state = fields.Selection(
        related="invoice_id.state",
        string="Invoice Status",
    )
    invoice_payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="Invoice Payment Status",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("pending", "Pending payment"),
            ("paid", "Paid"),
            ("reversed", "Reversed"),
            ("cancelled", "Cancelled"),
        ],
        string="Collection Status",
        compute="_compute_state",
        store=True,
        help="Status based on the payment of the referred invoice. It is not "
        "the payment status of the commission to the referrer.",
    )

    _referral_invoice_uniq = models.Constraint(
        "unique(referral_id, invoice_id)",
        "A commission already exists for this referral and invoice.",
    )

    @api.depends("referral_id", "invoice_id")
    def _compute_name(self):
        for commission in self:
            commission.name = (
                f"{commission.referral_id.display_name or ''} - "
                f"{commission.invoice_id.name or ''}"
            ).strip(" -")

    @api.depends("base_amount", "commission_percent", "currency_id")
    def _compute_commission_amount(self):
        for commission in self:
            amount = commission.base_amount * commission.commission_percent / 100
            commission.commission_amount = (
                commission.currency_id.round(amount)
                if commission.currency_id
                else amount
            )

    @api.depends(
        "invoice_id.state",
        "invoice_id.payment_state",
    )
    def _compute_state(self):
        for commission in self:
            invoice = commission.invoice_id
            if not invoice:
                commission.state = "draft"
            elif invoice.state == "cancel":
                commission.state = "cancelled"
            elif invoice.state == "draft":
                commission.state = "draft"
            elif invoice.payment_state == "reversed":
                commission.state = "reversed"
            elif invoice.payment_state in ("paid", "in_payment"):
                commission.state = "paid"
            else:
                commission.state = "pending"
