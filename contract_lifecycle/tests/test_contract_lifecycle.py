# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import new_test_user

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestContractLifecycle(TestContractBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.enable_contract_line_refund_on_stop = True

    def setUp(self):
        super().setUp()
        self.today = fields.Date.context_today(self)
        self.referred_partner = self.env["res.partner"].create(
            {"name": "Lifecycle Customer", "email": "lifecycle@example.com"}
        )
        self.contract = self._create_contract()
        self.pause_reason = self.env["contract.pause.reason"].create(
            {"name": "Temporary pause"}
        )
        self.terminate_reason = self.env["contract.terminate.reason"].create(
            {"name": "End of service"}
        )

    def _line_vals(self, **overrides):
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
        vals.update(overrides)
        return vals

    def _create_contract(self, **line_overrides):
        return self.env["contract.contract"].create(
            {
                "name": "Lifecycle Contract",
                "partner_id": self.referred_partner.id,
                "pricelist_id": self.pricelist.id,
                "line_recurrence": True,
                "invoicing_mode": "validate",
                "contract_line_ids": [
                    Command.create(self._line_vals(**line_overrides))
                ],
            }
        )

    def _product_line(self, contract=None):
        contract = contract or self.contract
        return contract.contract_line_ids.filtered(
            lambda line: not line.display_type
        )[:1]

    def _add_promo(
        self, contract_line, max_invoices=2, pause_policy="service"
    ):
        return self.env["contract.invoice.discount"].create(
            {
                "name": "Promotion",
                "contract_line_id": contract_line.id,
                "discount": 20,
                "date_start": self.today,
                "date_end": self.today
                + relativedelta(months=6)
                - relativedelta(days=1),
                "max_invoices": max_invoices,
                "source": "promotion",
                "pause_policy": pause_policy,
            }
        )

    def _create_referral(self, contract=None):
        contract = contract or self.contract
        referrer = self.env["res.partner"].create({"name": "Referrer"})
        return self.env["contract.referral"].create(
            {
                "company_id": self.env.company.id,
                "referrer_id": referrer.id,
                "referred_id": self.referred_partner.id,
                "referred_contract_id": contract.id,
                "start_date": self.today,
                "max_months": 6,
                "max_invoices": 2,
                "referrer_commission_percent": 10,
                "referred_discount_percent": 15,
                "commission_base": "untaxed",
                "state": "active",
            }
        )

    def _invoices(self):
        return self.env["account.move"].search(
            [
                ("partner_id", "=", self.referred_partner.id),
                ("move_type", "=", "out_invoice"),
            ]
        )

    def test_pause_and_resume_wizards_allow_account_manager(self):
        manager = new_test_user(
            self.env,
            login="lifecycle_manager",
            groups="base.group_user,account.group_account_manager",
        )
        pause_wizard = (
            self.env["contract.pause.wizard"]
            .with_user(manager)
            .create(
                {
                    "contract_id": self.contract.id,
                    "start_date": self.today,
                    "is_indefinite": True,
                    "reason_id": self.pause_reason.id,
                }
            )
        )
        pause_wizard.action_pause()

        resume_wizard = (
            self.env["contract.resume.wizard"]
            .with_user(manager)
            .create(
                {
                    "contract_id": self.contract.id,
                    "pause_id": self.contract.current_pause_id.id,
                    "resume_date": self.today + timedelta(days=5),
                }
            )
        )
        resume_wizard.action_resume()

    def test_planned_pause_blocks_invoices_and_resumes(self):
        line = self._product_line()
        self._add_promo(line)
        pause_start = self.today + timedelta(days=10)
        pause_end = self.today + timedelta(days=40)

        pause = self.contract._pause_contract(
            pause_start, pause_end, False, self.pause_reason, "planned"
        )

        # Future scheduled pause must not mark the contract paused yet.
        self.assertEqual(pause.state, "scheduled")
        self.assertFalse(self.contract.is_paused)
        self.assertEqual(self.contract.lifecycle_state, "running")
        self.assertTrue(line.successor_contract_line_id)
        self.assertEqual(line.date_end, pause_start - timedelta(days=1))
        successor = line.successor_contract_line_id
        self.assertEqual(successor.date_start, pause_end + timedelta(days=1))
        successor_rule = successor.invoice_discount_ids
        self.assertEqual(successor_rule.max_invoices, 2)
        pause_days = (pause_end - pause_start).days + 1
        self.assertEqual(
            successor_rule.date_start,
            self.today + timedelta(days=pause_days),
        )
        self.assertEqual(
            successor_rule.date_end,
            self.today
            + relativedelta(months=6)
            - relativedelta(days=1)
            + timedelta(days=pause_days),
        )
        self.assertFalse(
            line.invoice_discount_ids.filtered(lambda rule: rule.active)
        )

        # Once pause_start arrives, the scheduled pause activates and blocks invoicing.
        self.env["contract.pause"]._activate_scheduled_pauses(pause_start)
        self.assertEqual(pause.state, "active")
        self.assertTrue(self.contract.is_paused)
        self.assertEqual(self.contract.lifecycle_state, "paused")
        self.contract._cron_recurring_create(pause_start + timedelta(days=5))
        self.assertFalse(self._invoices())

        self.env["contract.pause"]._close_planned_pauses(
            pause_end + timedelta(days=1)
        )
        self.assertFalse(self.contract.is_paused)
        self.assertEqual(pause.state, "resumed")
        self.assertEqual(self.contract.lifecycle_state, "running")

        self.contract._cron_recurring_create(pause_end + timedelta(days=2))
        invoices = self._invoices()
        self.assertEqual(len(invoices), 1)
        self.assertEqual(
            invoices.invoice_line_ids.mapped("contract_line_id"),
            line | successor,
        )
        successor_inv_line = invoices.invoice_line_ids.filtered(
            lambda inv_line: inv_line.contract_line_id == successor
        )
        self.assertEqual(successor_inv_line.discount, 20.0)

    def test_calendar_pause_policy_keeps_discount_dates(self):
        line = self._product_line()
        promo = self._add_promo(line, pause_policy="calendar")
        original_start = promo.date_start
        original_end = promo.date_end
        pause_start = self.today + timedelta(days=10)
        pause_end = self.today + timedelta(days=40)

        self.contract._pause_contract(
            pause_start, pause_end, False, self.pause_reason, "planned"
        )

        successor = line.successor_contract_line_id
        successor_rule = successor.invoice_discount_ids
        self.assertEqual(successor_rule.date_start, original_start)
        self.assertEqual(successor_rule.date_end, original_end)
        self.assertFalse(promo.active)

    def test_indefinite_pause_can_be_resumed(self):
        line = self._product_line()
        self._add_promo(line)
        pause_start = self.today + timedelta(days=10)
        pause = self.contract._pause_contract(
            pause_start, False, True, self.pause_reason, "indefinite"
        )

        self.assertEqual(pause.state, "scheduled")
        self.env["contract.pause"]._activate_scheduled_pauses(pause_start)
        self.assertTrue(self.contract.is_paused)
        self.assertFalse(line.successor_contract_line_id)
        self.contract._cron_recurring_create(pause_start + timedelta(days=5))
        self.assertFalse(self._invoices())

        resume_date = self.today + timedelta(days=40)
        self.contract._resume_contract(pause, resume_date)
        self.assertFalse(self.contract.is_paused)
        self.assertEqual(pause.state, "resumed")
        self.assertTrue(line.successor_contract_line_id)
        successor = line.successor_contract_line_id
        self.assertEqual(successor.date_start, resume_date)
        self.assertTrue(successor.invoice_discount_ids)
        self.assertFalse(
            line.invoice_discount_ids.filtered(lambda rule: rule.active)
        )

        self.contract._cron_recurring_create(resume_date + timedelta(days=1))
        invoices = self._invoices()
        self.assertEqual(len(invoices), 1)
        successor_inv_line = invoices.invoice_line_ids.filtered(
            lambda inv_line: inv_line.contract_line_id == successor
        )
        self.assertEqual(successor_inv_line.discount, 20.0)

    def test_planned_pause_freezes_referral_and_keeps_remaining_invoices(self):
        first_invoice = self.contract.recurring_create_invoice()
        self.assertTrue(first_invoice)
        line = self._product_line()
        referral = self._create_referral()
        rule = referral.discount_rule_ids
        self.assertEqual(rule.applied_invoice_count, 0)

        # Consume one invoiced period after the referral is created.
        next_invoice = self.contract.recurring_create_invoice()
        self.assertTrue(next_invoice)
        referral.invalidate_recordset()
        rule.invalidate_recordset()
        self.assertEqual(rule.applied_invoice_count, 1)

        pause_start = self.today + timedelta(days=50)
        pause_end = pause_start + timedelta(days=30)
        self.contract._pause_contract(
            pause_start, pause_end, False, self.pause_reason, "pause"
        )
        referral.invalidate_recordset()

        self.assertEqual(referral.paused_days, 31)
        successor_rule = line.successor_contract_line_id.invoice_discount_ids
        self.assertEqual(successor_rule.max_invoices, 1)
        self.assertEqual(successor_rule.referral_id, referral)

    def test_pause_creates_credit_note_for_invoiced_period(self):
        self.assertTrue(self.contract.recurring_create_invoice())
        pause_start = self.today + timedelta(days=10)
        pause_end = self.today + timedelta(days=40)
        self.contract._pause_contract(
            pause_start, pause_end, False, self.pause_reason, "credit"
        )
        refund = self.env["account.move"].search(
            [
                ("partner_id", "=", self.referred_partner.id),
                ("move_type", "=", "out_refund"),
            ]
        )
        self.assertTrue(refund)
        self.assertEqual(refund.state, "draft")

    def test_terminate_wizard_has_reasons_and_allows_creating_one(self):
        self.assertTrue(
            self.env.ref(
                "contract_lifecycle.contract_terminate_reason_end_of_service"
            ).exists()
        )
        arch = self.env["contract.contract.terminate"].get_view(view_type="form")[
            "arch"
        ]
        self.assertNotIn('widget="selection"', arch)

    def test_termination_is_final_and_finishes_referral(self):
        referral = self._create_referral()
        line = self._product_line()
        self.contract._terminate_contract(
            self.terminate_reason,
            "final",
            self.today + timedelta(days=5),
        )
        referral.invalidate_recordset()
        self.assertTrue(self.contract.is_terminated)
        self.assertEqual(self.contract.lifecycle_state, "terminated")
        self.assertEqual(referral.state, "finished")
        self.assertFalse(referral.discount_rule_ids.filtered("active"))
        self.assertFalse(line._can_be_invoiced(self.today + timedelta(days=10)))
        with self.assertRaises(UserError):
            self.contract.action_cancel_contract_termination()

    def test_pause_on_invoiced_start_date_and_post_resume_invoicing(self):
        line = self._product_line()
        first_invoice = self.contract.recurring_create_invoice()
        self.assertTrue(first_invoice)
        # Pause starting on the already-invoiced date_start
        pause = self.contract._pause_contract(
            self.today, False, True, self.pause_reason, "same day pause"
        )
        self.assertTrue(line.is_canceled)
        self.assertFalse(line.last_date_invoiced)
        resume_date = self.today + timedelta(days=10)
        self.contract._resume_contract(pause, resume_date)
        self.assertFalse(self.contract.is_paused)
        next_inv = self.contract.recurring_create_invoice()
        self.assertTrue(next_inv)
        # Contract recurring_next_date must advance past the resumed invoice
        self.assertGreater(self.contract.recurring_next_date, resume_date)
