# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestContractReferral(TestContractBase):
    def setUp(self):
        super().setUp()
        self.today = fields.Date.context_today(self)
        self.referred_partner = self.env["res.partner"].create(
            {
                "name": "Referred Customer",
                "email": "referred@example.com",
            }
        )
        self.referred_contract = self._create_referred_contract()

    def _create_referred_contract(self, line_count=1, **line_overrides):
        vals = {
            "product_id": self.product_1.id,
            "name": "Service",
            "quantity": 1,
            "uom_id": self.product_1.uom_id.id,
            "price_unit": 100,
            "recurring_rule_type": "monthly",
            "recurring_interval": 1,
            "date_start": self.today,
            "recurring_next_date": self.today,
            "recurring_invoicing_type": "pre-paid",
        }
        vals.update(line_overrides)
        lines = []
        for index in range(line_count):
            line_vals = dict(vals)
            if index:
                line_vals["name"] = f"{vals['name']} {index + 1}"
            lines.append(Command.create(line_vals))
        return self.env["contract.contract"].create(
            {
                "name": "Referred contract",
                "partner_id": self.referred_partner.id,
                "pricelist_id": self.pricelist.id,
                "line_recurrence": True,
                "invoicing_mode": "validate",
                "contract_line_ids": lines,
            }
        )

    def _create_referral(self, **overrides):
        vals = {
            "company_id": self.env.company.id,
            "referrer_id": self.partner.id,
            "referred_id": self.referred_partner.id,
            "referred_contract_id": self.referred_contract.id,
            "start_date": self.today,
            "max_months": 6,
            "max_invoices": 6,
            "referrer_commission_percent": 10,
            "referred_discount_percent": 15,
            "commission_base": "untaxed",
            "state": "active",
        }
        vals.update(overrides)
        return self.env["contract.referral"].create(vals)

    def _product_line(self, invoice):
        return invoice.invoice_line_ids.filtered(
            lambda line: line.display_type in (False, "product")
        )[:1]

    def test_referral_creates_discount_rule_and_commission(self):
        referral = self._create_referral()
        rule = referral.discount_rule_ids
        self.assertEqual(len(rule), 1)
        self.assertEqual(rule.source, "referral")
        self.assertEqual(rule.referral_id, referral)
        self.assertEqual(rule.discount, 15.0)
        self.assertEqual(rule.start_mode, "fixed_date")
        self.assertEqual(rule.date_start, self.today)

        invoice = self.referred_contract.recurring_create_invoice()
        self.assertEqual(invoice.state, "posted")
        line = self._product_line(invoice)
        self.assertEqual(line.discount, 15.0)
        self.assertEqual(line.contract_discount_id, rule)
        self.assertEqual(line.contract_discount_source, "referral")

        commission = self.env["contract.referral.commission"].search(
            [("referral_id", "=", referral.id)]
        )
        self.assertEqual(len(commission), 1)
        self.assertEqual(commission.invoice_id, invoice)
        self.assertEqual(commission.base_amount, invoice.amount_untaxed)
        self.assertAlmostEqual(
            commission.commission_amount,
            round(invoice.amount_untaxed * 0.10, 2),
            places=2,
        )
        self.assertEqual(commission.state, "pending")

    def test_commission_base_total_uses_total_amount(self):
        referral = self._create_referral(commission_base="total")
        invoice = self.referred_contract.recurring_create_invoice()
        commission = self.env["contract.referral.commission"].search(
            [("referral_id", "=", referral.id)]
        )
        self.assertEqual(len(commission), 1)
        self.assertEqual(commission.base_amount, invoice.amount_total)
        self.assertAlmostEqual(
            commission.commission_amount,
            round(invoice.amount_total * 0.10, 2),
            places=2,
        )

    def test_multiple_lines_get_discount_and_single_commission(self):
        contract = self._create_referred_contract(line_count=2)
        referral = self._create_referral(referred_contract_id=contract.id)
        self.assertEqual(len(referral.discount_rule_ids), 2)

        invoice = contract.recurring_create_invoice()
        product_lines = invoice.invoice_line_ids.filtered(
            lambda line: line.display_type in (False, "product")
        )
        self.assertEqual(len(product_lines), 2)
        self.assertEqual(set(product_lines.mapped("discount")), {15.0})
        self.assertEqual(
            set(product_lines.mapped("contract_discount_source")),
            {"referral"},
        )
        self.assertEqual(len(referral.commission_ids), 1)

    def test_overdue_invoice_loses_referral_discount_forever(self):
        referral = self._create_referral()
        invoice = self.referred_contract.recurring_create_invoice()
        invoice.write({"invoice_date_due": self.today - timedelta(days=1)})

        next_invoice = self.referred_contract.recurring_create_invoice()
        self.assertEqual(self._product_line(next_invoice).discount, 0.0)
        referral.invalidate_recordset()
        self.assertTrue(referral.referred_discount_lost)
        # The referrer commission continues while the contract is active.
        self.assertEqual(len(referral.commission_ids), 2)
        self.assertEqual(
            referral.referred_discount_lost_date,
            self.today,
        )
        self.assertFalse(referral.discount_rule_ids.filtered("active"))

        third_invoice = self.referred_contract.recurring_create_invoice()
        self.assertEqual(self._product_line(third_invoice).discount, 0.0)

    def test_max_invoices_limits_discount_and_commission(self):
        referral = self._create_referral(max_invoices=1)
        first_invoice = self.referred_contract.recurring_create_invoice()
        self.assertEqual(self._product_line(first_invoice).discount, 15.0)
        self.assertEqual(len(referral.commission_ids), 1)

        second_invoice = self.referred_contract.recurring_create_invoice()
        self.assertEqual(self._product_line(second_invoice).discount, 0.0)
        referral.invalidate_recordset()
        self.assertEqual(len(referral.commission_ids), 1)

    def test_promotion_wins_over_referral(self):
        referral = self._create_referral()
        contract_line = self.referred_contract.contract_line_ids[:1]
        promo = self.env["contract.invoice.discount"].create(
            {
                "name": "Promotion",
                "contract_line_id": contract_line.id,
                "discount": 20,
                "date_start": self.today,
                "date_end": self.today
                + relativedelta(months=1)
                - relativedelta(days=1),
                "max_invoices": 1,
                "source": "promotion",
            }
        )
        first_invoice = self.referred_contract.recurring_create_invoice()
        first_line = self._product_line(first_invoice)
        self.assertEqual(first_line.discount, 20.0)
        self.assertEqual(first_line.contract_discount_id, promo)
        self.assertEqual(referral.discount_rule_ids.applied_invoice_count, 0)

        promo.active = False
        second_invoice = self.referred_contract.recurring_create_invoice()
        second_line = self._product_line(second_invoice)
        self.assertEqual(second_line.discount, 15.0)
        self.assertEqual(second_line.contract_discount_source, "referral")

    def test_referrer_and_referred_must_be_different(self):
        with self.assertRaises(ValidationError):
            self._create_referral(referrer_id=self.referred_partner.id)

    def test_duplicate_active_referral_is_blocked(self):
        self._create_referral()
        with self.assertRaises(ValidationError):
            self._create_referral()

    def test_max_months_stops_discount_and_commission(self):
        referral = self._create_referral(max_months=1, max_invoices=0)
        first_invoice = self.referred_contract.recurring_create_invoice()
        self.assertEqual(self._product_line(first_invoice).discount, 15.0)
        self.assertEqual(len(referral.commission_ids), 1)

        second_invoice = self.referred_contract.recurring_create_invoice()
        self.assertEqual(self._product_line(second_invoice).discount, 0.0)
        referral.invalidate_recordset()
        self.assertEqual(len(referral.commission_ids), 1)

    def test_inactive_contract_stops_benefits(self):
        referral = self._create_referral()
        self.referred_contract.active = False
        invoice = self.referred_contract.recurring_create_invoice()
        self.assertEqual(self._product_line(invoice).discount, 0.0)
        referral.invalidate_recordset()
        self.assertFalse(referral.commission_ids)

    def test_refund_creates_negative_commission_adjustment(self):
        referral = self._create_referral()
        invoice = self.referred_contract.recurring_create_invoice()
        commission = self.env["contract.referral.commission"].search(
            [("referral_id", "=", referral.id)]
        )
        self.assertEqual(len(commission), 1)
        self.assertFalse(commission.is_adjustment)

        contract_line = self.referred_contract.contract_line_ids[:1]
        refund = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.referred_partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                            "name": "Refund",
                            "quantity": 1,
                            "price_unit": 100,
                            "contract_line_id": contract_line.id,
                        }
                    )
                ],
            }
        )
        refund.action_post()
        adjustment = self.env["contract.referral.commission"].search(
            [
                ("referral_id", "=", referral.id),
                ("invoice_id", "=", refund.id),
                ("is_adjustment", "=", True),
            ]
        )
        self.assertEqual(len(adjustment), 1)
        self.assertLess(adjustment.base_amount, 0)
        self.assertLess(adjustment.commission_amount, 0)

    def test_referral_commission_scope_reversal_and_reactivation(self):
        referral = self._create_referral(max_invoices=2)
        rule = referral.discount_rule_ids
        # Contract copy must not inherit referral link
        copied = self.referred_contract.copy()
        self.assertFalse(copied.contract_line_ids.invoice_discount_ids.filtered("referral_id"))

        # Deactivate & reactivate referral preserves existing discount rule
        referral.action_cancel()
        self.assertFalse(rule.active)
        referral.action_activate()
        self.assertTrue(rule.active)
        self.assertEqual(len(referral.discount_rule_ids), 1)

        # Invoice with extra non-contract line only commissions contract line
        invoice = self.referred_contract.recurring_create_invoice()
        commission = referral.commission_ids
        self.assertEqual(len(commission), 1)
        self.assertEqual(commission.base_amount, 85.0)

        # Reversing invoice marks original commission as reversed
        reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"reason": "Reversal", "journal_id": invoice.journal_id.id})
        )
        res = reversal.reverse_moves()
        credit_note = self.env["account.move"].browse(res["res_id"])
        if credit_note.state == "draft":
            credit_note.action_post()
        (invoice.line_ids + credit_note.line_ids).filtered(
            lambda l: l.account_id.account_type == "asset_receivable" and not l.reconciled
        ).reconcile()
        commission.invalidate_recordset()
        self.assertEqual(commission.state, "reversed")

    def test_refund_without_prior_commission_creates_no_adjustment(self):
        referral = self._create_referral(referrer_commission_percent=10)
        referral.action_cancel()
        contract_line = self.referred_contract.contract_line_ids[:1]
        refund = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.referred_partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                            "name": "Manual refund",
                            "quantity": 1,
                            "price_unit": 100,
                            "contract_line_id": contract_line.id,
                        }
                    )
                ],
            }
        )
        refund.action_post()
        self.assertFalse(referral.commission_ids)
