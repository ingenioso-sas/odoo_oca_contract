# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import Command
from odoo.tests import Form

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestContractBillingCycle(TestContractBase):
    def _line_vals(self, **overrides):
        vals = {
            "product_id": self.product_1.id,
            "name": "Service from #START# to #END#",
            "quantity": 1,
            "uom_id": self.product_1.uom_id.id,
            "price_unit": 100,
            "recurring_rule_type": "monthly",
            "recurring_interval": 1,
            "recurring_invoicing_type": "post-paid",
            "date_start": date(2026, 10, 15),
        }
        vals.update(overrides)
        return vals

    def _create_contract(self, line_overrides=None, **contract_overrides):
        line_vals = self._line_vals(**(line_overrides or {}))
        vals = {
            "name": "Billing cycle contract",
            "partner_id": self.partner.id,
            "pricelist_id": self.pricelist.id,
            "line_recurrence": True,
            "invoicing_mode": "draft",
            "billing_anchor_day": 1,
            "free_trial_periods": 0,
            "free_trial_discount": 100,
            "skip_zero_invoices": False,
            "contract_line_ids": [Command.create(line_vals)],
        }
        vals.update(contract_overrides)
        return self.env["contract.contract"].create(vals)

    def _product_line(self, invoice):
        return invoice.invoice_line_ids.filtered(
            lambda line: line.display_type in (False, "product")
        )[:1]

    def test_billing_anchor_moves_first_invoice_to_the_first(self):
        contract = self._create_contract()
        line = contract.contract_line_ids

        self.assertEqual(line.recurring_next_date, date(2026, 11, 1))
        self.assertEqual(line.next_period_date_start, date(2026, 10, 15))
        self.assertEqual(line.next_period_date_end, date(2026, 10, 31))

        invoice = contract.recurring_create_invoice()
        self.assertEqual(invoice.invoice_date, date(2026, 11, 1))
        self.assertEqual(invoice.contract_period_start, date(2026, 10, 15))
        self.assertEqual(invoice.contract_period_end, date(2026, 10, 31))
        product_line = self._product_line(invoice)
        self.assertEqual(product_line.quantity, 1.0)
        self.assertAlmostEqual(
            product_line.price_unit, 100 * 17 / 31, places=2
        )
        self.assertIn("prorrateado", product_line.name)

        self.assertEqual(line.last_date_invoiced, date(2026, 10, 31))
        self.assertEqual(line.recurring_next_date, date(2026, 12, 1))
        self.assertEqual(line.next_period_date_start, date(2026, 11, 1))
        self.assertEqual(line.next_period_date_end, date(2026, 11, 30))

    def test_full_period_keeps_the_regular_price(self):
        contract = self._create_contract(
            line_overrides={"date_start": date(2026, 11, 1)}
        )
        line = contract.contract_line_ids
        self.assertEqual(line.recurring_next_date, date(2026, 12, 1))

        invoice = contract.recurring_create_invoice()
        product_line = self._product_line(invoice)
        self.assertEqual(invoice.invoice_date, date(2026, 12, 1))
        self.assertEqual(product_line.price_unit, 100.0)
        self.assertNotIn("prorrateado", product_line.name)

    def test_custom_billing_anchor_day(self):
        contract = self._create_contract(
            line_overrides={"date_start": date(2026, 10, 3)},
            billing_anchor_day=5,
        )
        line = contract.contract_line_ids
        self.assertEqual(line.recurring_next_date, date(2026, 10, 5))
        self.assertEqual(line.next_period_date_end, date(2026, 10, 4))

        invoice = contract.recurring_create_invoice()
        product_line = self._product_line(invoice)
        self.assertEqual(invoice.invoice_date, date(2026, 10, 5))
        self.assertEqual(invoice.contract_period_start, date(2026, 10, 3))
        self.assertEqual(invoice.contract_period_end, date(2026, 10, 4))
        self.assertAlmostEqual(
            product_line.price_unit, 100 * 2 / 30, places=2
        )

        self.assertEqual(line.recurring_next_date, date(2026, 11, 5))
        self.assertEqual(line.next_period_date_start, date(2026, 10, 5))
        self.assertEqual(line.next_period_date_end, date(2026, 11, 4))

    def test_anchor_invoice_date_hook(self):
        contract = self._create_contract()
        line = contract.contract_line_ids
        self.assertEqual(
            line._get_anchor_invoice_date(date(2026, 10, 15)),
            date(2026, 11, 1),
        )
        self.assertEqual(
            line._get_anchor_invoice_date(date(2026, 11, 1)),
            date(2026, 12, 1),
        )

    def test_anchor_does_not_apply_to_prepaid_lines(self):
        contract = self._create_contract(
            line_overrides={"recurring_invoicing_type": "pre-paid"}
        )
        line = contract.contract_line_ids
        self.assertEqual(line.recurring_next_date, date(2026, 10, 15))
        self.assertEqual(line.next_period_date_end, date(2026, 11, 14))

    def test_changing_the_anchor_recomputes_the_first_invoice(self):
        contract = self._create_contract()
        line = contract.contract_line_ids
        self.assertEqual(line.recurring_next_date, date(2026, 11, 1))

        contract.billing_anchor_day = 5

        self.assertEqual(line.recurring_next_date, date(2026, 11, 5))
        self.assertEqual(line.next_period_date_end, date(2026, 11, 4))

    def test_first_full_period_is_free(self):
        contract = self._create_contract(free_trial_periods=1)
        line = contract.contract_line_ids

        self.assertEqual(line.free_trial_start, date(2026, 11, 1))
        self.assertEqual(line.free_trial_end, date(2026, 11, 30))
        rule = line.free_trial_discount_id
        self.assertTrue(rule)
        self.assertTrue(rule.is_free_trial)
        self.assertEqual(rule.date_start, date(2026, 11, 1))
        self.assertEqual(rule.date_end, date(2026, 11, 30))

        first = contract.recurring_create_invoice()
        self.assertAlmostEqual(first.amount_untaxed, 100 * 17 / 31, places=2)

        second = contract.recurring_create_invoice()
        self.assertEqual(second.invoice_date, date(2026, 12, 1))
        self.assertEqual(self._product_line(second).discount, 100.0)
        self.assertEqual(second.amount_untaxed, 0.0)

        third = contract.recurring_create_invoice()
        self.assertEqual(third.invoice_date, date(2027, 1, 1))
        self.assertEqual(self._product_line(third).discount, 0.0)
        self.assertEqual(third.amount_untaxed, 100.0)

    def test_start_on_anchor_makes_the_first_period_free(self):
        contract = self._create_contract(
            line_overrides={"date_start": date(2026, 11, 1)},
            free_trial_periods=1,
        )
        line = contract.contract_line_ids
        self.assertEqual(line.free_trial_start, date(2026, 11, 1))
        self.assertEqual(line.free_trial_end, date(2026, 11, 30))

        first = contract.recurring_create_invoice()
        self.assertEqual(first.invoice_date, date(2026, 12, 1))
        self.assertEqual(self._product_line(first).discount, 100.0)
        self.assertEqual(first.amount_untaxed, 0.0)

        second = contract.recurring_create_invoice()
        self.assertEqual(second.amount_untaxed, 100.0)

    def test_zero_invoice_can_be_skipped(self):
        contract = self._create_contract(
            free_trial_periods=1,
            skip_zero_invoices=True,
        )
        line = contract.contract_line_ids

        first = contract.recurring_create_invoice()
        self.assertAlmostEqual(first.amount_untaxed, 100 * 17 / 31, places=2)

        skipped = contract.recurring_create_invoice()
        self.assertFalse(skipped)
        self.assertEqual(line.last_date_invoiced, date(2026, 11, 30))
        self.assertEqual(line.recurring_next_date, date(2027, 1, 1))

        third = contract.recurring_create_invoice()
        self.assertEqual(third.invoice_date, date(2027, 1, 1))
        self.assertEqual(third.amount_untaxed, 100.0)

    def test_zero_invoice_is_created_by_default(self):
        contract = self._create_contract(free_trial_periods=1)
        contract.recurring_create_invoice()
        trial_invoice = contract.recurring_create_invoice()
        self.assertTrue(trial_invoice)
        self.assertEqual(trial_invoice.amount_untaxed, 0.0)

    def test_discount_applies_on_the_prorated_price(self):
        contract = self._create_contract()
        line = contract.contract_line_ids
        self.env["contract.invoice.discount"].create(
            {
                "name": "Commercial discount",
                "contract_line_id": line.id,
                "discount": 20,
                "start_mode": "fixed_date",
                "date_start": date(2026, 10, 15),
                "max_invoices": 1,
            }
        )
        invoice = contract.recurring_create_invoice()
        product_line = self._product_line(invoice)
        self.assertAlmostEqual(
            product_line.price_unit, 100 * 17 / 31, places=2
        )
        self.assertEqual(product_line.discount, 20.0)
        self.assertAlmostEqual(
            invoice.amount_untaxed,
            (100 * 17 / 31) * 0.8,
            places=2,
        )

    def test_template_copies_billing_cycle_fields(self):
        template = self.env["contract.template"].create(
            {
                "name": "Billing cycle template",
                "billing_anchor_day": 5,
                "free_trial_periods": 2,
                "free_trial_discount": 100,
                "skip_zero_invoices": True,
            }
        )
        with Form(self.env["contract.contract"]) as contract_form:
            contract_form.name = "Contract from billing cycle template"
            contract_form.contract_template_id = template
            contract_form.partner_id = self.partner
            contract = contract_form.save()
        self.assertEqual(contract.billing_anchor_day, 5)
        self.assertEqual(contract.free_trial_periods, 2)
        self.assertEqual(contract.free_trial_discount, 100)
        self.assertTrue(contract.skip_zero_invoices)
