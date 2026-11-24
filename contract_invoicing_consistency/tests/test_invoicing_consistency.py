# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import Command
from odoo.exceptions import ValidationError

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestContractInvoicingConsistency(TestContractBase):
    def _line_vals(self, **overrides):
        vals = {
            "product_id": self.product_1.id,
            "name": "Service",
            "quantity": 1,
            "uom_id": self.product_1.uom_id.id,
            "price_unit": 100,
            "recurring_rule_type": "monthly",
            "recurring_interval": 1,
            "recurring_invoicing_type": "pre-paid",
            "date_start": date(2026, 10, 1),
            "last_date_invoiced": date(2026, 10, 31),
            "recurring_next_date": date(2026, 11, 1),
        }
        vals.update(overrides)
        return vals

    def _create_contract(self, lines):
        return self.env["contract.contract"].create(
            {
                "name": "Invoicing consistency contract",
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "line_recurrence": True,
                "invoicing_mode": "draft",
                "contract_line_ids": [
                    Command.create(line) for line in lines
                ],
            }
        )

    def test_postpaid_invoice_date_must_be_after_the_period(self):
        with self.assertRaises(ValidationError):
            self._create_contract(
                [
                    self._line_vals(
                        recurring_invoicing_type="post-paid",
                        recurring_next_date=date(2026, 11, 1),
                    )
                ]
            )

    def test_prepaid_invoice_date_cannot_be_before_the_period(self):
        with self.assertRaises(ValidationError):
            self._create_contract(
                [
                    self._line_vals(
                        recurring_invoicing_type="pre-paid",
                        recurring_next_date=date(2026, 10, 1),
                    )
                ]
            )

    def test_valid_postpaid_invoice_date(self):
        contract = self._create_contract(
            [
                self._line_vals(
                    recurring_invoicing_type="post-paid",
                    recurring_next_date=date(2026, 12, 1),
                )
            ]
        )
        line = contract.contract_line_ids
        self.assertEqual(line.next_period_date_end, date(2026, 11, 30))
        self.assertEqual(line.recurring_next_date, date(2026, 12, 1))

    def test_write_rejects_an_inconsistent_invoice_date(self):
        contract = self._create_contract(
            [
                self._line_vals(
                    recurring_invoicing_type="post-paid",
                    recurring_next_date=date(2026, 12, 1),
                )
            ]
        )
        line = contract.contract_line_ids
        with self.assertRaises(ValidationError):
            line.write({"recurring_next_date": date(2026, 11, 1)})
        self.assertEqual(line.recurring_next_date, date(2026, 12, 1))

    def test_warning_when_the_contract_mixes_invoicing_types(self):
        contract = self._create_contract(
            [
                self._line_vals(name="Pre-paid line"),
                self._line_vals(
                    name="Post-paid line",
                    recurring_invoicing_type="post-paid",
                    recurring_next_date=date(2026, 12, 1),
                ),
            ]
        )
        self.assertTrue(contract.mixed_invoicing_warning)
        self.assertIn("mezcla", contract.mixed_invoicing_warning)
        self.assertIn("Pre-paid line", contract.mixed_invoicing_warning)
        self.assertIn("Post-paid line", contract.mixed_invoicing_warning)

    def test_no_warning_when_all_lines_share_the_invoicing_type(self):
        pre_paid = self._create_contract(
            [self._line_vals(name="Pre-paid line")]
        )
        post_paid = self._create_contract(
            [
                self._line_vals(
                    name="Post-paid line",
                    recurring_invoicing_type="post-paid",
                    recurring_next_date=date(2026, 12, 1),
                )
            ]
        )
        self.assertFalse(pre_paid.mixed_invoicing_warning)
        self.assertFalse(post_paid.mixed_invoicing_warning)
