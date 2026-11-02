# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Service-subscription features ported from subscription_package /
subscription_oca: pause/resume, per-contract invoicing mode, to-renew flag
and monthly recurring total."""

from datetime import timedelta

from odoo import fields

from .test_contract import TestContractBase


class TestContractServiceFeatures(TestContractBase):
    def test_pause_excludes_line_from_invoicing(self):
        line = self.contract.contract_line_ids[:1]
        line.write(
            {
                "date_start": "2018-01-01",
                "recurring_next_date": "2018-01-15",
                "recurring_rule_type": "monthly",
                "recurring_interval": 1,
            }
        )
        self.assertTrue(line.create_invoice_visibility)
        line.action_pause()
        self.assertTrue(line.is_paused)
        self.assertFalse(line.create_invoice_visibility)
        # Paused lines are skipped by the invoicing engine
        to_invoice = self.contract._get_lines_to_invoice(fields.Date.to_date("2018-02-01"))
        self.assertNotIn(line, to_invoice)
        next_date_before = line.recurring_next_date
        line.action_resume()
        self.assertFalse(line.is_paused)
        # Resume shifts next date by the paused gap (no catch-up billing)
        self.assertGreaterEqual(line.recurring_next_date, next_date_before)

    def test_pause_does_not_break_successor(self):
        line = self.contract.contract_line_ids[:1]
        line.write(
            {
                "date_start": "2018-01-01",
                "date_end": "2018-12-31",
                "recurring_next_date": "2018-01-15",
                "recurring_rule_type": "monthly",
                "recurring_interval": 1,
            }
        )
        line.action_pause()
        line.action_resume()
        successor = line.plan_successor(
            fields.Date.to_date("2019-01-01"),
            fields.Date.to_date("2019-12-31"),
            False,
        )
        self.assertFalse(successor.is_paused)

    def test_invoicing_mode_validate(self):
        self.contract.write({"invoicing_mode": "validate"})
        line = self.contract.contract_line_ids[:1]
        line.write(
            {
                "date_start": fields.Date.today() - timedelta(days=30),
                "recurring_next_date": fields.Date.today(),
                "recurring_rule_type": "monthly",
                "recurring_interval": 1,
            }
        )
        invoices = self.contract.recurring_create_invoice()
        self.assertTrue(invoices)
        self.assertEqual(set(invoices.mapped("state")), {"posted"})

    def test_is_to_renew_and_monthly_total(self):
        line = self.contract.contract_line_ids[:1]
        line.write(
            {
                "price_unit": 120.0,
                "quantity": 1,
                "discount": 0,
                "automatic_price": False,
                "specific_price": 120.0,
                "recurring_rule_type": "monthly",
                "recurring_interval": 1,
                "date_start": "2018-01-01",
                "date_end": fields.Date.today() + timedelta(days=5),
                "recurring_next_date": fields.Date.today() + timedelta(days=5),
            }
        )
        # 120 / month -> MRR 120
        self.assertAlmostEqual(line.recurring_monthly_amount, 120.0, places=2)
        self.assertAlmostEqual(
            self.contract.recurring_monthly_total, 120.0, places=2
        )
        # Ending within the alert window flags the contract
        self.contract.write({"renew_alert_days": 15})
        self.contract._compute_is_to_renew()
        self.assertTrue(self.contract.is_to_renew)

    def test_template_syncs_invoicing_mode(self):
        self.template.write({"invoicing_mode": "validate"})
        contract = self.env["contract.contract"].create(
            {
                "name": "Sync test",
                "partner_id": self.partner.id,
                "contract_template_id": self.template.id,
                "line_recurrence": True,
            }
        )
        form = contract  # onchange simulation
        form._onchange_contract_template_id()
        self.assertEqual(form.invoicing_mode, "validate")
