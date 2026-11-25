# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    def write(self, vals):
        res = super().write(vals)
        if any(
            key in vals
            for key in (
                "billing_anchor_day",
                "free_trial_periods",
                "free_trial_discount",
            )
        ):
            self.contract_line_ids._sync_free_trial_discount()
        return res

    def _prepare_recurring_invoices_values(self, date_ref=False):
        """Build invoice values and optionally drop zero-total invoices."""
        invoices_values = []
        for contract in self:
            values = super(
                ContractContract, contract
            )._prepare_recurring_invoices_values(date_ref=date_ref)
            if contract.skip_zero_invoices:
                filtered = []
                for vals in values:
                    if contract._is_zero_invoice_vals(vals):
                        contract._consume_free_trial_rules(vals)
                    else:
                        filtered.append(vals)
                if len(filtered) < len(values):
                    contract.message_post(
                        body=self.env._(
                            "Factura(s) en cero omitida(s) según la "
                            "configuración del contrato."
                        )
                    )
                values = filtered
            invoices_values.extend(values)
        return invoices_values

    def _consume_free_trial_rules(self, vals):
        """Mark the trial rules of a skipped zero invoice as consumed."""
        rule_ids = set()
        for command in vals.get("invoice_line_ids", []):
            line_vals = (
                command[2]
                if isinstance(command, (list, tuple)) and len(command) == 3
                else {}
            )
            if not isinstance(line_vals, dict):
                continue
            rule_id = line_vals.get("contract_discount_id")
            if rule_id:
                rule_ids.add(rule_id)
        if not rule_ids:
            return
        rules = (
            self.env["contract.invoice.discount"]
            .browse(rule_ids)
            .filtered("is_free_trial")
        )
        if rules:
            rules.sudo().with_context(skip_free_trial_sync=True).write(
                {"free_trial_consumed": True}
            )

    def _is_zero_invoice_vals(self, vals):
        currency = (
            self.env["res.currency"].browse(vals.get("currency_id"))
            or self.currency_id
        )
        total = 0.0
        for command in vals.get("invoice_line_ids", []):
            line_vals = (
                command[2]
                if isinstance(command, (list, tuple)) and len(command) == 3
                else {}
            )
            if not isinstance(line_vals, dict) or line_vals.get(
                "display_type"
            ) in ("line_section", "line_note"):
                continue
            price = line_vals.get("price_unit", 0.0) or 0.0
            quantity = line_vals.get("quantity", 0.0) or 0.0
            discount = line_vals.get("discount", 0.0) or 0.0
            total += price * quantity * (1.0 - discount / 100.0)
        return currency.is_zero(total)
