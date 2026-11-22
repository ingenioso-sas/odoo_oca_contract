# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests import Form

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestContractInvoiceDiscount(TestContractBase):
    def _line_vals(self, **overrides):
        today = fields.Date.context_today(self)
        vals = {
            "product_id": self.product_1.id,
            "name": "Service",
            "quantity": 1,
            "uom_id": self.product_1.uom_id.id,
            "price_unit": 100,
            "recurring_rule_type": "monthly",
            "recurring_interval": 1,
            "date_start": today,
            "recurring_next_date": today,
            "recurring_invoicing_type": "pre-paid",
        }
        vals.update(overrides)
        return vals

    def _create_contract(self, **line_overrides):
        return self.env["contract.contract"].create(
            {
                "name": "Contract with invoice discount",
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "line_recurrence": True,
                "contract_line_ids": [
                    Command.create(self._line_vals(**line_overrides))
                ],
            }
        )

    def _product_line(self, invoice):
        return invoice.invoice_line_ids.filtered(
            lambda line: line.display_type in (False, "product")
        )[:1]

    def _add_rule(self, contract, **overrides):
        today = fields.Date.context_today(self)
        line = contract.contract_line_ids.filtered(
            lambda line: not line.display_type
        )[:1]
        vals = {
            "name": "Promotion",
            "contract_line_id": line.id,
            "discount": 20,
            "date_start": today,
            "date_end": today + relativedelta(months=1) - relativedelta(days=1),
            "max_invoices": 1,
            "source": "promotion",
        }
        vals.update(overrides)
        return self.env["contract.invoice.discount"].create(vals)

    def _backdated_contract(self, line_start=None):
        """Create a contract whose next invoice period is in the past."""
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        period_start = month_start - relativedelta(months=2)
        period_end = (
            month_start - relativedelta(months=1) - relativedelta(days=1)
        )
        recurring_next_date = month_start - relativedelta(months=1)
        last_date_invoiced = period_start - relativedelta(days=1)
        contract = self._create_contract(
            date_start=line_start or period_start - relativedelta(months=1),
            last_date_invoiced=last_date_invoiced,
            recurring_next_date=recurring_next_date,
            recurring_invoicing_type="post-paid",
        )
        return contract, period_start, period_end

    def test_next_invoice_start_mode_uses_next_period(self):
        contract, period_start, _period_end = self._backdated_contract()
        rule = self._add_rule(
            contract,
            start_mode="next_invoice",
            date_end=False,
            max_invoices=1,
        )
        self.assertEqual(rule.date_start, period_start)

        invoice = contract.recurring_create_invoice()
        line = self._product_line(invoice)
        self.assertEqual(line.discount, 20.0)
        self.assertEqual(line.contract_discount_id, rule)
        self.assertEqual(rule.applied_invoice_count, 1)
        self.assertEqual(rule.remaining_invoices, 0)

    def test_contract_start_mode_uses_contract_line_start(self):
        today = fields.Date.context_today(self)
        line_start = today.replace(day=1) - relativedelta(months=4)
        contract, _period_start, _period_end = self._backdated_contract(
            line_start=line_start
        )
        rule = self._add_rule(
            contract,
            start_mode="contract_start",
            date_end=False,
            max_invoices=1,
        )
        self.assertEqual(rule.date_start, line_start)

        invoice = contract.recurring_create_invoice()
        self.assertEqual(self._product_line(invoice).discount, 20.0)

    def test_fixed_date_start_mode_keeps_manual_date(self):
        contract, period_start, _period_end = self._backdated_contract()
        fixed_date = period_start - relativedelta(days=5)
        rule = self._add_rule(
            contract,
            start_mode="fixed_date",
            date_start=fixed_date,
            date_end=False,
            max_invoices=1,
        )
        self.assertEqual(rule.date_start, fixed_date)

    def test_context_default_start_mode_is_next_invoice(self):
        contract, period_start, _period_end = self._backdated_contract()
        line = contract.contract_line_ids.filtered(
            lambda item: not item.display_type
        )[:1]
        rule = (
            self.env["contract.invoice.discount"]
            .with_context(default_start_mode="next_invoice")
            .create(
                {
                    "name": "Manual discount",
                    "contract_line_id": line.id,
                    "discount": 10,
                    "max_invoices": 1,
                }
            )
        )
        self.assertEqual(rule.start_mode, "next_invoice")
        self.assertEqual(rule.date_start, period_start)

    def test_credit_note_does_not_consume_extra_invoice(self):
        contract, _period_start, _period_end = self._backdated_contract()
        rule = self._add_rule(
            contract,
            start_mode="next_invoice",
            date_end=False,
            max_invoices=2,
        )
        invoice = contract.recurring_create_invoice()
        self.assertEqual(rule.applied_invoice_count, 1)

        product_line = self._product_line(invoice)
        self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Refund",
                            "quantity": 1,
                            "price_unit": product_line.price_unit,
                            "account_id": product_line.account_id.id,
                            "contract_discount_id": rule.id,
                        }
                    )
                ],
            }
        )
        rule.invalidate_recordset()
        self.assertEqual(rule.applied_invoice_count, 1)

    def test_next_invoice_mode_consumes_multiple_invoices(self):
        contract, period_start, _period_end = self._backdated_contract()
        rule = self._add_rule(
            contract,
            start_mode="next_invoice",
            date_end=False,
            max_invoices=2,
        )
        self.assertEqual(rule.date_start, period_start)

        first = contract.recurring_create_invoice()
        second = contract.recurring_create_invoice()
        third = contract.recurring_create_invoice()

        self.assertEqual(self._product_line(first).discount, 20.0)
        self.assertEqual(self._product_line(second).discount, 20.0)
        self.assertEqual(self._product_line(third).discount, 0.0)
        self.assertEqual(rule.date_start, period_start)
        rule.invalidate_recordset()
        self.assertEqual(rule.applied_invoice_count, 2)
        self.assertEqual(rule.remaining_invoices, 0)

    def test_recompute_start_date_updates_existing_rule(self):
        contract, _period_start, _period_end = self._backdated_contract()
        rule = self._add_rule(
            contract,
            start_mode="contract_start",
            date_end=False,
            max_invoices=1,
        )
        line = contract.contract_line_ids.filtered(
            lambda item: not item.display_type
        )[:1]
        new_start = line.date_start - relativedelta(days=10)
        line.date_start = new_start
        self.assertNotEqual(rule.date_start, new_start)

        rule.action_recompute_date_start()
        self.assertEqual(rule.date_start, new_start)

    def test_first_month_discount_then_regular_price(self):
        contract = self._create_contract()
        rule = self._add_rule(contract)
        invoice = contract.recurring_create_invoice()
        line = self._product_line(invoice)

        self.assertEqual(line.discount, 20.0)
        self.assertEqual(line.contract_discount_id, rule)
        self.assertEqual(line.contract_discount_name, "Promotion")
        self.assertEqual(line.contract_discount_percent, 20.0)

        next_invoice = contract.recurring_create_invoice()
        next_line = self._product_line(next_invoice)
        self.assertEqual(next_line.discount, 0.0)
        self.assertFalse(next_line.contract_discount_id)

    def test_six_months_and_max_invoices(self):
        contract = self._create_contract()
        today = fields.Date.context_today(self)
        self._add_rule(
            contract,
            discount=10,
            date_end=today + relativedelta(months=6) - relativedelta(days=1),
            max_invoices=6,
        )
        for index in range(6):
            invoice = contract.recurring_create_invoice()
            self.assertEqual(
                self._product_line(invoice).discount,
                10.0,
                "Discount should apply to invoice %s" % (index + 1),
            )
        extra_invoice = contract.recurring_create_invoice()
        self.assertEqual(self._product_line(extra_invoice).discount, 0.0)

    def test_highest_discount_wins(self):
        contract = self._create_contract(discount=10)
        self._add_rule(contract, discount=20)
        invoice = contract.recurring_create_invoice()
        self.assertEqual(self._product_line(invoice).discount, 20.0)

        low_contract = self._create_contract(discount=10)
        self._add_rule(low_contract, discount=5)
        low_invoice = low_contract.recurring_create_invoice()
        self.assertEqual(self._product_line(low_invoice).discount, 10.0)

    def test_partial_period_is_prorated(self):
        contract = self._create_contract()
        today = fields.Date.context_today(self)
        self._add_rule(
            contract,
            discount=20,
            date_start=today,
            date_end=today + relativedelta(days=14),
        )
        contract_line = contract.contract_line_ids[:1]
        period_start, period_end, _next_date = contract_line._get_period_to_invoice(
            contract_line.last_date_invoiced,
            contract_line.recurring_next_date,
        )
        invoice = contract.recurring_create_invoice()
        line = self._product_line(invoice)
        period_days = (period_end - period_start).days + 1
        overlap_days = 15
        expected = round(20 * overlap_days / period_days, 2)
        self.assertEqual(line.discount, expected)

    def test_template_promotion_is_copied(self):
        today = fields.Date.context_today(self)
        template = self.env["contract.template"].create(
            {
                "name": "Template with promotion",
                "company_id": self.env.company.id,
                "contract_type": "sale",
                "line_recurrence": True,
                "contract_line_ids": [
                    Command.create(
                        self._line_vals(
                            promo_name="Template promotion",
                            promo_discount=20,
                            promo_duration_months=1,
                            promo_max_invoices=1,
                        )
                    )
                ],
            }
        )
        with Form(self.env["contract.contract"]) as form:
            form.name = "Contract from promotion template"
            form.partner_id = self.partner
            form.contract_template_id = template
            contract = form.save()

        rule = contract.contract_line_ids.invoice_discount_ids[:1]
        self.assertTrue(rule)
        self.assertEqual(rule.start_mode, "contract_start")
        invoice = contract.recurring_create_invoice()
        line = self._product_line(invoice)
        self.assertEqual(line.discount, 20.0)
        self.assertEqual(line.contract_discount_name, "Template promotion")
        self.assertTrue(
            contract.contract_line_ids.invoice_discount_ids.date_start >= today
        )

    def test_report_shows_discount_name(self):
        contract = self._create_contract()
        self._add_rule(contract, name="First month promotion")
        invoice = contract.recurring_create_invoice()
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice", invoice.ids
        )
        text = html.decode() if isinstance(html, bytes) else str(html)
        self.assertIn("First month promotion", text)

    def test_write_start_mode_and_date_end_together(self):
        contract, _period_start, _period_end = self._backdated_contract()
        today = fields.Date.context_today(self)
        rule = self._add_rule(
            contract,
            start_mode="fixed_date",
            date_start=today + relativedelta(months=2),
            date_end=today + relativedelta(months=3),
            max_invoices=1,
        )
        line = contract.contract_line_ids.filtered(lambda l: not l.display_type)[:1]
        rule.write(
            {
                "start_mode": "contract_start",
                "date_end": line.date_start + relativedelta(days=20),
            }
        )
        self.assertEqual(rule.date_start, line.date_start)
        self.assertEqual(rule.date_end, line.date_start + relativedelta(days=20))
