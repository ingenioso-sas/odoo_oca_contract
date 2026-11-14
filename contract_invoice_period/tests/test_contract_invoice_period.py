# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import date

from odoo import Command

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestContractInvoicePeriod(TestContractBase):
    def _line_vals(self, **overrides):
        vals = {
            "product_id": self.product_1.id,
            "name": "Service",
            "quantity": 1,
            "uom_id": self.product_1.uom_id.id,
            "price_unit": 100,
            "recurring_rule_type": "monthly",
            "recurring_interval": 1,
            "date_start": date(2026, 1, 1),
            "recurring_next_date": date(2026, 1, 1),
            "recurring_invoicing_type": "pre-paid",
        }
        vals.update(overrides)
        return vals

    def _create_contract(self, lines=None):
        return self.env["contract.contract"].create(
            {
                "name": "Contract with invoice period",
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "line_recurrence": True,
                "contract_line_ids": [
                    Command.create(line)
                    for line in (lines or [self._line_vals()])
                ],
            }
        )

    def _product_lines(self, invoice):
        return invoice.invoice_line_ids.filtered(
            lambda line: line.display_type in (False, "product")
        )

    def test_prepaid_period_is_stored_in_invoice(self):
        contract = self._create_contract()
        invoice = contract.recurring_create_invoice()

        self.assertEqual(invoice.contract_id, contract)
        self.assertEqual(invoice.contract_billing_date, date(2026, 1, 1))
        self.assertEqual(invoice.contract_period_start, date(2026, 1, 1))
        self.assertEqual(invoice.contract_period_end, date(2026, 1, 31))
        # The accounting document date is not changed by this module.
        self.assertEqual(invoice.invoice_date, date(2026, 1, 1))

        line = self._product_lines(invoice)
        self.assertEqual(len(line), 1)
        self.assertEqual(line.contract_billing_date, date(2026, 1, 1))
        self.assertEqual(line.contract_period_start, date(2026, 1, 1))
        self.assertEqual(line.contract_period_end, date(2026, 1, 31))

    def test_postpaid_period_is_stored_in_invoice(self):
        contract = self._create_contract(
            lines=[
                self._line_vals(
                    recurring_invoicing_type="post-paid",
                    recurring_next_date=date(2026, 2, 1),
                )
            ]
        )
        invoice = contract.recurring_create_invoice()

        self.assertEqual(invoice.contract_billing_date, date(2026, 2, 1))
        self.assertEqual(invoice.contract_period_start, date(2026, 1, 1))
        self.assertEqual(invoice.contract_period_end, date(2026, 1, 31))

    def test_prorated_period_is_stored_in_invoice(self):
        contract = self._create_contract(
            lines=[
                self._line_vals(
                    date_start=date(2026, 1, 15),
                    recurring_next_date=date(2026, 1, 15),
                    date_end=date(2026, 1, 31),
                )
            ]
        )
        invoice = contract.recurring_create_invoice()

        self.assertEqual(invoice.contract_period_start, date(2026, 1, 15))
        self.assertEqual(invoice.contract_period_end, date(2026, 1, 31))

    def test_header_aggregates_lines_with_different_periods(self):
        contract = self._create_contract(
            lines=[
                self._line_vals(),
                self._line_vals(recurring_rule_type="quarterly"),
            ]
        )
        invoice = contract.recurring_create_invoice()

        self.assertEqual(invoice.contract_period_start, date(2026, 1, 1))
        self.assertEqual(invoice.contract_period_end, date(2026, 3, 31))
        periods = {
            (line.contract_period_start, line.contract_period_end)
            for line in self._product_lines(invoice)
        }
        self.assertEqual(
            periods,
            {
                (date(2026, 1, 1), date(2026, 1, 31)),
                (date(2026, 1, 1), date(2026, 3, 31)),
            },
        )

    def test_consecutive_invoices_keep_their_own_periods(self):
        contract = self._create_contract()

        first = contract.recurring_create_invoice()
        second = contract.recurring_create_invoice()
        third = contract.recurring_create_invoice()

        self.assertEqual(first.contract_period_start, date(2026, 1, 1))
        self.assertEqual(first.contract_period_end, date(2026, 1, 31))
        self.assertEqual(second.contract_period_start, date(2026, 2, 1))
        self.assertEqual(second.contract_period_end, date(2026, 2, 28))
        self.assertEqual(third.contract_period_start, date(2026, 3, 1))
        self.assertEqual(third.contract_period_end, date(2026, 3, 31))

    def test_section_lines_do_not_get_contract_period(self):
        contract = self._create_contract(
            lines=[
                self._line_vals(),
                {
                    "display_type": "line_section",
                    "name": "Services",
                },
            ]
        )
        section = contract.contract_line_ids.filtered(
            lambda line: line.display_type == "line_section"
        )
        product = contract.contract_line_ids.filtered(
            lambda line: not line.display_type
        )[:1]

        section_vals = section._prepare_invoice_line() or {}
        product_vals = product._prepare_invoice_line() or {}

        self.assertNotIn("contract_period_start", section_vals)
        self.assertNotIn("contract_period_end", section_vals)
        self.assertNotIn("contract_billing_date", section_vals)
        self.assertIn("contract_period_start", product_vals)
        self.assertIn("contract_period_end", product_vals)
        self.assertIn("contract_billing_date", product_vals)

    def test_manual_invoice_without_contract_has_empty_period(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                            "quantity": 1,
                            "price_unit": 100,
                        }
                    )
                ],
            }
        )

        self.assertFalse(invoice.contract_id)
        self.assertFalse(invoice.contract_billing_date)
        self.assertFalse(invoice.contract_period_start)
        self.assertFalse(invoice.contract_period_end)

    def test_invoice_report_shows_contract_period(self):
        contract = self._create_contract()
        invoice = contract.recurring_create_invoice()

        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice", invoice.ids
        )
        text = html.decode() if isinstance(html, bytes) else str(html)

        self.assertIn('name="contract_billing_date"', text)
        self.assertIn('name="contract_period"', text)
        self.assertIn("2026", text)
