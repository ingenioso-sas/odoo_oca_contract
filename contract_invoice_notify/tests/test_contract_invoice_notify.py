# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta

from odoo import fields

from odoo.addons.contract.tests.test_contract import TestContractBase


class TestContractInvoiceNotify(TestContractBase):
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

    def test_validate_posts_without_sending(self):
        self.contract.write({"invoicing_mode": "validate"})
        self._prepare_line()
        invoices = self.contract.recurring_create_invoice()
        self.assertTrue(invoices)
        self.assertEqual(set(invoices.mapped("state")), {"posted"})

    def test_validate_send_email_adds_overdue_info(self):
        self.contract.write(
            {"invoicing_mode": "validate_send", "send_notification_mode": "email"}
        )
        self._prepare_line()
        invoices = self.contract.recurring_create_invoice()
        self.assertEqual(set(invoices.mapped("state")), {"posted"})
        move = invoices[0]
        # Overdue helper must exclude itself and only count posted pending.
        self.assertNotIn(move.id, move._get_contract_overdue_invoices().ids)
        text = move._get_whatsapp_text()
        self.assertIn(move.name, text)

    def test_validate_send_whatsapp_no_mobile_does_not_break(self):
        self.contract.write(
            {"invoicing_mode": "validate_send", "send_notification_mode": "whatsapp"}
        )
        self.contract.partner_id.write({"mobile": False, "phone": False})
        self._prepare_line()
        invoices = self.contract.with_context(no_whatsapp_delay=True).recurring_create_invoice()
        self.assertEqual(set(invoices.mapped("state")), {"posted"})

    def test_overdue_digest_per_contract_respects_grace_resend_max(self):
        self.contract.write(
            {
                "invoicing_mode": "validate",
                "send_notification_mode": "whatsapp",
                "overdue_reminder_enabled": True,
                "overdue_grace_days": 3,
                "overdue_resend_after_days": 7,
                "overdue_max_reminders": 1,
            }
        )
        self._prepare_line()
        invoices = self.contract.recurring_create_invoice()
        move = invoices[0]
        # Not overdue inside grace period
        move.write({"invoice_date_due": fields.Date.today()})
        self.assertEqual(self.contract._get_overdue_reminder_candidates().ids, [])
        # Overdue after grace period
        move.write(
            {
                "invoice_date_due": fields.Date.today() - timedelta(days=10),
                "last_overdue_reminder_date": False,
                "overdue_reminder_count": 0,
            }
        )
        self.assertIn(move.id, self.contract._get_overdue_reminder_candidates().ids)
        # Digest sends once and marks the invoice
        self.contract.with_context(no_whatsapp_delay=True)._send_overdue_digest()
        move.invalidate_recordset()
        self.assertEqual(move.overdue_reminder_count, 1)
        self.assertEqual(move.last_overdue_reminder_date, fields.Date.today())
        # Max reached -> excluded even if still overdue
        self.assertEqual(self.contract._get_overdue_reminder_candidates().ids, [])
        # Opt-out blocks sending
        move.write({"overdue_reminder_count": 0, "last_overdue_reminder_date": False})
        self.contract.partner_id.write({"opt_out_overdue_reminder": True})
        self.assertFalse(self.contract._send_overdue_digest())
