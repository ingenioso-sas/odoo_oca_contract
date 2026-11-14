# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Custom features ported from the 17.0 branch: per-contract invoicing
mode (draft/validate/validate_send) and the monthly recurring total
(based on the native contract.line monthly_recurring field)."""

from datetime import timedelta

from odoo import fields

from .test_contract import TestContractBase


class TestContractServiceFeatures(TestContractBase):
    def _prepare_line(self):
        line = self.contract.contract_line_ids[:1]
        line.write(
            {
                "date_start": fields.Date.today() - timedelta(days=30),
                "recurring_next_date": fields.Date.today(),
                "recurring_rule_type": "monthly",
                "recurring_interval": 1,
            }
        )
        return line

    def test_invoicing_mode_validate(self):
        self.contract.write({"invoicing_mode": "validate"})
        self._prepare_line()
        invoices = self.contract.recurring_create_invoice()
        self.assertTrue(invoices)
        self.assertEqual(set(invoices.mapped("state")), {"posted"})

    def test_invoicing_mode_draft_keeps_draft(self):
        self.contract.write({"invoicing_mode": "draft"})
        self._prepare_line()
        invoices = self.contract.recurring_create_invoice()
        self.assertTrue(invoices)
        self.assertEqual(set(invoices.mapped("state")), {"draft"})

    def test_recurring_monthly_total(self):
        line = self._prepare_line()
        line.write({"price_unit": 120.0, "quantity": 1, "discount": 0})
        # 120 / month -> MRR 120
        self.assertAlmostEqual(line.monthly_recurring, 120.0, places=2)
        self.contract.invalidate_recordset()
        self.assertAlmostEqual(
            self.contract.recurring_monthly_total, 120.0, places=2
        )

    def test_template_syncs_invoicing_mode(self):
        self.template.write({"invoicing_mode": "validate"})
        contract = self.env["contract.contract"].new(
            {
                "name": "Sync test",
                "partner_id": self.partner.id,
                "contract_template_id": self.template.id,
                "line_recurrence": True,
            }
        )
        contract._onchange_contract_template_id()
        self.assertEqual(contract.invoicing_mode, "validate")
