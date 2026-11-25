# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestContractInvoiceRegenerate(TestContractBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract = cls.env["contract.contract"].create(
            {
                "name": "Contract to regenerate",
                "partner_id": cls.partner.id,
                "pricelist_id": cls.pricelist.id,
                "line_recurrence": True,
                "invoicing_mode": "draft",
                "contract_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_1.id,
                            "name": "Monthly service",
                            "quantity": 1,
                            "uom_id": cls.product_1.uom_id.id,
                            "price_unit": 100,
                            "recurring_rule_type": "monthly",
                            "recurring_interval": 1,
                            "recurring_invoicing_type": "post-paid",
                            "date_start": date(2026, 1, 1),
                            "recurring_next_date": date(2026, 2, 1),
                        }
                    )
                ],
            }
        )
        cls.line = cls.contract.contract_line_ids

    def _create_wizard(self, period_start, period_end, invoice_date):
        return self.env["contract.regenerate.invoice"].create(
            {
                "contract_line_id": self.line.id,
                "period_start": period_start,
                "period_end": period_end,
                "invoice_date": invoice_date,
            }
        )

    def _delete_without_recalculation(self, invoice):
        invoice.with_context(contract_skip_recalculate=True).unlink()

    def test_recalculate_dates_after_deleting_the_last_draft_invoice(self):
        first = self.contract.recurring_create_invoice()
        second = self.contract.recurring_create_invoice()
        self.assertEqual(self.line.last_date_invoiced, date(2026, 2, 28))
        self.assertEqual(self.line.recurring_next_date, date(2026, 4, 1))

        self._delete_without_recalculation(second)

        # Deleting the invoice does not rewind the dates by itself.
        self.assertEqual(self.line.last_date_invoiced, date(2026, 2, 28))
        self.line.action_recalculate_invoice_dates()
        self.assertEqual(self.line.last_date_invoiced, date(2026, 1, 31))
        self.assertEqual(self.line.recurring_next_date, date(2026, 3, 1))

    def test_recalculate_respects_the_billing_anchor(self):
        if not hasattr(self.line, "_get_anchor_invoice_date"):
            self.skipTest("contract_billing_cycle is not installed")
        self.contract.billing_anchor_day = 5
        self.line.write({"date_start": date(2026, 1, 15)})
        self.line.write({"recurring_next_date": date(2026, 1, 20)})

        self.line.action_recalculate_invoice_dates()

        self.assertEqual(self.line.last_date_invoiced, False)
        self.assertEqual(self.line.recurring_next_date, date(2026, 2, 5))
        self.assertEqual(self.line.next_period_date_start, date(2026, 1, 15))
        self.assertEqual(self.line.next_period_date_end, date(2026, 2, 4))

    def test_recalculate_respects_the_billing_anchor_after_invoicing(self):
        if not hasattr(self.line, "_get_anchor_invoice_date"):
            self.skipTest("contract_billing_cycle is not installed")
        self.contract.recurring_create_invoice()
        self.assertEqual(self.line.last_date_invoiced, date(2026, 1, 31))

        self.contract.billing_anchor_day = 5
        self.line.action_recalculate_invoice_dates()

        self.assertEqual(self.line.last_date_invoiced, date(2026, 1, 31))
        self.assertEqual(self.line.recurring_next_date, date(2026, 2, 5))
        self.assertEqual(self.line.next_period_date_start, date(2026, 2, 1))
        self.assertEqual(self.line.next_period_date_end, date(2026, 2, 4))

    def test_regenerate_invoice_keeps_the_original_period_and_date(self):
        self.contract.recurring_create_invoice()
        second = self.contract.recurring_create_invoice()
        self._delete_without_recalculation(second)

        action = self.line.action_regenerate_invoice()
        context = action["context"]
        self.assertEqual(context["default_period_start"], date(2026, 2, 1))
        self.assertEqual(context["default_period_end"], date(2026, 2, 28))
        self.assertEqual(context["default_invoice_date"], date(2026, 3, 1))

        wizard = self._create_wizard(
            date(2026, 2, 1), date(2026, 2, 28), date(2026, 3, 1)
        )
        result = wizard.action_regenerate_invoice()
        invoice = self.env["account.move"].browse(result["res_id"])

        self.assertEqual(invoice.state, "draft")
        self.assertEqual(invoice.invoice_date, date(2026, 3, 1))
        self.assertEqual(invoice.contract_period_start, date(2026, 2, 1))
        self.assertEqual(invoice.contract_period_end, date(2026, 2, 28))
        invoice_line = invoice.invoice_line_ids.filtered(
            lambda line: line.contract_line_id == self.line
        )
        self.assertEqual(invoice_line.quantity, 1.0)
        self.assertEqual(
            invoice_line.contract_period_end, date(2026, 2, 28)
        )
        self.assertEqual(self.line.last_date_invoiced, date(2026, 2, 28))
        self.assertEqual(self.line.recurring_next_date, date(2026, 4, 1))

    def test_regenerate_invoice_blocks_an_existing_period(self):
        self.contract.recurring_create_invoice()
        wizard = self._create_wizard(
            date(2026, 1, 1), date(2026, 1, 31), date(2026, 2, 1)
        )
        with self.assertRaises(UserError):
            wizard.action_regenerate_invoice()

    def test_posted_contract_invoice_cannot_be_deleted(self):
        invoice = self.contract.recurring_create_invoice()
        invoice.action_post()
        with self.assertRaises(UserError):
            invoice.unlink()
        self.assertTrue(invoice.exists())

    def test_draft_contract_invoice_delete_recalculates_dates(self):
        self.contract.recurring_create_invoice()
        second = self.contract.recurring_create_invoice()
        self.assertEqual(self.line.last_date_invoiced, date(2026, 2, 28))
        self.assertEqual(self.line.recurring_next_date, date(2026, 4, 1))

        second.unlink()

        self.assertEqual(self.line.last_date_invoiced, date(2026, 1, 31))
        self.assertEqual(self.line.recurring_next_date, date(2026, 3, 1))

    def test_recalculate_falls_back_to_invoice_date_for_old_invoices(self):
        invoice = self.contract.recurring_create_invoice()
        invoice.invoice_line_ids.write(
            {
                "contract_period_start": False,
                "contract_period_end": False,
                "contract_billing_date": False,
            }
        )

        self.line.action_recalculate_invoice_dates()

        self.assertEqual(self.line.last_date_invoiced, date(2026, 1, 31))
        self.assertEqual(self.line.recurring_next_date, date(2026, 3, 1))

    def test_recalculate_is_admin_only(self):
        user = new_test_user(
            self.env,
            login="contract_invoice_no_admin",
            groups="base.group_user",
        )
        with self.assertRaises(AccessError):
            self.line.with_user(user).action_recalculate_invoice_dates()
