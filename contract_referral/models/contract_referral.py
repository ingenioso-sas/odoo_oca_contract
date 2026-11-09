# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ContractReferral(models.Model):
    _name = "contract.referral"
    _description = "Contract Referral"
    _order = "create_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    referrer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Referrer",
        required=True,
        index=True,
        help="Customer that receives the commission.",
    )
    referred_id = fields.Many2one(
        comodel_name="res.partner",
        string="Referred Customer",
        required=True,
        index=True,
        help="Customer that receives the referral discount.",
    )
    referred_contract_id = fields.Many2one(
        comodel_name="contract.contract",
        string="Referred Contract",
        required=True,
        index=True,
        ondelete="cascade",
    )
    start_date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        help="First date of the referral benefit.",
    )
    max_months = fields.Integer(
        default=0,
        help="Maximum duration in months. 0 = no month limit.",
    )
    max_invoices = fields.Integer(
        default=0,
        help="Maximum number of invoices for the benefit. 0 = unlimited.",
    )
    end_date = fields.Date(
        compute="_compute_end_date",
        store=True,
        readonly=True,
    )
    referrer_commission_percent = fields.Float(
        string="Referrer Commission (%)",
        digits="Discount",
        help="Percentage of the referred invoice used to calculate the "
        "referrer commission.",
    )
    referred_discount_percent = fields.Float(
        string="Referred Discount (%)",
        digits="Discount",
        help="Discount applied to the referred customer's invoices.",
    )
    commission_base = fields.Selection(
        selection=[
            ("untaxed", "Untaxed amount"),
            ("total", "Total amount"),
        ],
        default="untaxed",
        required=True,
        string="Commission Base",
    )
    state = fields.Selection(
        selection=[
            ("active", "Active"),
            ("finished", "Finished"),
            ("cancelled", "Cancelled"),
        ],
        default="active",
        required=True,
    )
    referred_discount_lost = fields.Boolean(
        readonly=True,
        copy=False,
        help="Set permanently when the referred customer has an overdue "
        "invoice. The referral discount will not apply again.",
    )
    referred_discount_lost_date = fields.Date(readonly=True, copy=False)
    discount_rule_ids = fields.One2many(
        comodel_name="contract.invoice.discount",
        inverse_name="referral_id",
        string="Referred Discount Rules",
        copy=False,
    )
    commission_ids = fields.One2many(
        comodel_name="contract.referral.commission",
        inverse_name="referral_id",
        string="Commissions",
        copy=False,
    )
    commission_count = fields.Integer(
        compute="_compute_commission_count",
        string="Commissions",
    )
    notes = fields.Text()

    @api.depends("referrer_id", "referred_id")
    def _compute_name(self):
        for referral in self:
            referral.name = (
                f"{referral.referrer_id.display_name or ''} → "
                f"{referral.referred_id.display_name or ''}"
            ).strip(" →")

    @api.depends("start_date", "max_months")
    def _compute_end_date(self):
        for referral in self:
            if referral.start_date and referral.max_months:
                referral.end_date = (
                    referral.start_date
                    + relativedelta(months=referral.max_months)
                    - relativedelta(days=1)
                )
            else:
                referral.end_date = False

    @api.depends("commission_ids")
    def _compute_commission_count(self):
        for referral in self:
            referral.commission_count = len(referral.commission_ids)

    @api.constrains(
        "referrer_commission_percent",
        "referred_discount_percent",
    )
    def _check_percentages(self):
        for referral in self:
            if not 0 <= referral.referrer_commission_percent <= 100:
                raise ValidationError(
                    self.env._("Commission percentage must be between 0 and 100.")
                )
            if not 0 <= referral.referred_discount_percent <= 100:
                raise ValidationError(
                    self.env._("Discount percentage must be between 0 and 100.")
                )

    @api.constrains("max_months", "max_invoices")
    def _check_limits(self):
        for referral in self:
            if referral.max_months < 0:
                raise ValidationError(
                    self.env._("Maximum months cannot be negative.")
                )
            if referral.max_invoices < 0:
                raise ValidationError(
                    self.env._("Maximum invoices cannot be negative.")
                )
            if not referral.max_months and not referral.max_invoices:
                raise ValidationError(
                    self.env._(
                        "Define a maximum of months or a maximum of invoices "
                        "for the referral."
                    )
                )

    @api.constrains("referrer_id", "referred_id")
    def _check_partners(self):
        for referral in self:
            if referral.referrer_id == referral.referred_id:
                raise ValidationError(
                    self.env._("Referrer and referred customer must be different.")
                )

    @api.constrains(
        "company_id",
        "referred_contract_id",
        "state",
    )
    def _check_unique_active_referral(self):
        for referral in self.filtered(lambda r: r.state == "active"):
            duplicate = self.search(
                [
                    ("id", "!=", referral.id),
                    ("company_id", "=", referral.company_id.id),
                    (
                        "referred_contract_id",
                        "=",
                        referral.referred_contract_id.id,
                    ),
                    ("state", "=", "active"),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    self.env._(
                        "There is already an active referral for this contract."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        referrals = super().create(vals_list)
        referrals._sync_referred_discount_rules()
        return referrals

    def write(self, vals):
        res = super().write(vals)
        if any(
            field_name in vals
            for field_name in (
                "state",
                "start_date",
                "max_months",
                "max_invoices",
                "referred_discount_percent",
                "referred_discount_lost",
                "referred_contract_id",
            )
        ):
            self._sync_referred_discount_rules()
        return res

    def _sync_referred_discount_rules(self):
        for referral in self:
            if (
                referral.state != "active"
                or referral.referred_discount_lost
                or not referral.referred_contract_id
                or not referral.referred_discount_percent
            ):
                referral.discount_rule_ids.write({"active": False})
                continue
            product_lines = referral.referred_contract_id.contract_line_ids.filtered(
                lambda line: not line.display_type
            )
            for line in product_lines:
                referral._sync_rule_for_line(line)
            referral.discount_rule_ids.filtered(
                lambda rule: rule.contract_line_id not in product_lines
            ).write({"active": False})

    def _sync_rule_for_line(self, line):
        self.ensure_one()
        rule = self.env["contract.invoice.discount"].search(
            [
                ("referral_id", "=", self.id),
                ("contract_line_id", "=", line.id),
            ],
            limit=1,
        )
        active = (
            self.state == "active"
            and not self.referred_discount_lost
            and bool(self.referred_discount_percent)
        )
        vals = {
            "name": self.env._(
                "Referral discount: %(referrer)s",
                referrer=self.referrer_id.display_name or "",
            ),
            "discount": self.referred_discount_percent,
            "date_start": self.start_date or fields.Date.context_today(self),
            "date_end": self.end_date,
            "max_invoices": self.max_invoices,
            "source": "referral",
            "active": active,
        }
        if rule:
            rule.write(vals)
        else:
            vals.update(
                {
                    "referral_id": self.id,
                    "contract_line_id": line.id,
                }
            )
            self.env["contract.invoice.discount"].create(vals)

    def _has_overdue_invoice(self):
        self.ensure_one()
        partner = self.referred_id.commercial_partner_id or self.referred_id
        today = fields.Date.context_today(self)
        domain = [
            ("company_id", "=", self.company_id.id),
            ("partner_id", "child_of", partner.id),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("invoice_date_due", "<", today),
        ]
        return bool(self.env["account.move"].sudo().search_count(domain))

    def _mark_referred_discount_lost(self):
        self.ensure_one()
        if self.referred_discount_lost:
            return
        self.write(
            {
                "referred_discount_lost": True,
                "referred_discount_lost_date": fields.Date.context_today(self),
            }
        )

    def _check_referred_discount_condition(self):
        self.ensure_one()
        if self.state != "active" or self.referred_discount_lost:
            return False
        contract = self.referred_contract_id
        today = fields.Date.context_today(self)
        if not contract or not contract.active:
            return False
        if contract.date_end and contract.date_end < today:
            return False
        if self.end_date and today > self.end_date:
            return False
        if self._has_overdue_invoice():
            self._mark_referred_discount_lost()
            return False
        return True

    def _can_create_commission(self, invoice):
        self.ensure_one()
        if self.state != "active" or self.referrer_commission_percent <= 0:
            return False
        contract = self.referred_contract_id
        invoice_date = invoice.invoice_date or invoice.date
        if not contract or not contract.active:
            return False
        if contract.date_end and invoice_date and contract.date_end < invoice_date:
            return False
        if self.start_date and invoice_date and invoice_date < self.start_date:
            return False
        if self.end_date and invoice_date and invoice_date > self.end_date:
            return False
        if self.max_invoices:
            commission_count = self.env["contract.referral.commission"].search_count(
                [("referral_id", "=", self.id)]
            )
            if commission_count >= self.max_invoices:
                return False
        return True

    def _get_commission_base_amount(self, invoice):
        self.ensure_one()
        if self.commission_base == "total":
            return invoice.amount_total
        return invoice.amount_untaxed

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_activate(self):
        self.write({"state": "active"})

    def action_finish(self):
        self.write({"state": "finished"})
