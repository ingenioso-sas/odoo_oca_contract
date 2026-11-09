# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    invoice_discount_ids = fields.One2many(
        comodel_name="contract.invoice.discount",
        inverse_name="contract_line_id",
        string="Invoice Discounts",
        copy=True,
    )
    invoice_discount_count = fields.Integer(
        compute="_compute_invoice_discount_count",
        string="Active Invoice Discounts",
    )

    def _compute_invoice_discount_count(self):
        for line in self:
            line.invoice_discount_count = len(
                line.invoice_discount_ids.filtered("active")
            )

    def _get_invoice_discount(self, period_start, period_end):
        """Return (percentage, rule) using only the highest discount."""
        self.ensure_one()
        base_discount = self.discount
        best_rule = self.env["contract.invoice.discount"]
        best_discount = 0.0
        if not period_start or not period_end:
            return base_discount, best_rule
        for rule in self.invoice_discount_ids.filtered("active"):
            if not rule._check_conditions(period_start, period_end):
                continue
            effective_discount = rule._get_effective_discount(
                period_start, period_end
            )
            if effective_discount > best_discount:
                best_discount = effective_discount
                best_rule = rule
        if best_rule and best_discount > base_discount:
            return best_discount, best_rule
        return base_discount, self.env["contract.invoice.discount"]

    def _prepare_invoice_line(self):
        vals = super()._prepare_invoice_line()
        if not vals or self.display_type:
            return vals
        period_start, period_end, _billing_date = self._get_period_to_invoice(
            self.last_date_invoiced, self.recurring_next_date
        )
        discount, rule = self._get_invoice_discount(period_start, period_end)
        vals["discount"] = discount
        if rule:
            vals.update(
                {
                    "contract_discount_id": rule.id,
                    "contract_discount_name": rule.name,
                    "contract_discount_percent": discount,
                    "contract_discount_until": rule.date_end,
                    "contract_discount_source": rule.source,
                }
            )
        return vals
