# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.fields import Command

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

    def _channel(self, code):
        return self.env["contract.notification.channel"].search(
            [("code", "=", code)], limit=1
        )

    def test_validate_posts_without_sending(self):
        self.contract.write({"invoicing_mode": "validate"})
        self._prepare_line()
        invoices = self.contract.recurring_create_invoice()
        self.assertTrue(invoices)
        self.assertEqual(set(invoices.mapped("state")), {"posted"})

    def test_validate_send_email_adds_overdue_info(self):
        email = self._channel("email")
        self.contract.write(
            {
                "invoicing_mode": "validate_send",
                "notification_channel_ids": [Command.set([email.id])],
            }
        )
        self._prepare_line()
        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
            return_value=1,
        ):
            invoices = self.contract.recurring_create_invoice()
        self.assertEqual(set(invoices.mapped("state")), {"posted"})
        move = invoices[0]
        # Overdue helper must exclude itself and only count posted pending.
        self.assertNotIn(move.id, move._get_contract_overdue_invoices().ids)
        template = self.contract._get_invoice_email_template()
        body = template._render_field(
            "body_html", [move.id], compute_lang=True
        )[move.id]
        self.assertIn(move.name, body)
        # Links must be absolute.
        self.assertTrue(
            move._get_payment_portal_url().startswith("http"),
            "payment portal URL must be absolute",
        )
        self.assertIn(move._get_payment_portal_url(), body)

    def test_validate_send_whatsapp_no_phone_does_not_break(self):
        whatsapp = self._channel("whatsapp")
        self.contract.write(
            {
                "invoicing_mode": "validate_send",
                "notification_channel_ids": [Command.set([whatsapp.id])],
            }
        )
        self.contract.partner_id.write({"phone": False})
        self._prepare_line()
        invoices = self.contract.recurring_create_invoice()
        self.assertEqual(set(invoices.mapped("state")), {"posted"})

    def test_validate_send_whatsapp_uses_contract_template(self):
        whatsapp = self._channel("whatsapp")
        template = self.env["mail.template"].create(
            {
                "name": "WA custom",
                "model_id": self.env.ref("account.model_account_move").id,
                "subject": "custom",
                "lang": "{{ object.partner_id.lang }}",
                "body_html": (
                    "<p>AVISO PERSONALIZADO "
                    "<t t-out=\"object.name\" /> "
                    "<a t-att-href=\"object._get_payment_portal_url()\">link</a></p>"
                ),
            }
        )
        self.contract.write(
            {
                "invoicing_mode": "validate_send",
                "notification_channel_ids": [Command.set([whatsapp.id])],
                "notification_template_ids": [
                    Command.create(
                        {
                            "channel_id": whatsapp.id,
                            "purpose": "invoice_notification",
                            "template_id": template.id,
                        }
                    )
                ],
            }
        )
        self.contract.partner_id.write({"phone": "+573001234567"})
        self._prepare_line()
        invoices = self.contract.recurring_create_invoice()
        self.assertEqual(set(invoices.mapped("state")), {"posted"})
        selected = self.contract._get_notification_template(
            invoices[0], "invoice_notification", "whatsapp"
        )
        self.assertEqual(selected, template)
        body = selected._render_field(
            "body_html", [invoices[0].id], compute_lang=True
        )[invoices[0].id]
        self.assertIn("AVISO PERSONALIZADO", body)
        self.assertIn(invoices[0].name, body)
        self.assertIn(invoices[0]._get_payment_portal_url(), body)

    def test_overdue_digest_per_contract_respects_grace_resend_max(self):
        email = self._channel("email")
        self.contract.write(
            {
                "invoicing_mode": "validate",
                "notification_channel_ids": [Command.set([email.id])],
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
        with patch(
            "odoo.addons.mail.models.mail_template.MailTemplate.send_mail",
            return_value=1,
        ):
            self.assertTrue(self.contract._send_overdue_digest())
        move.invalidate_recordset()
        self.assertEqual(move.overdue_reminder_count, 1)
        self.assertEqual(move.last_overdue_reminder_date, fields.Date.today())
        # Max reached -> excluded even if still overdue
        self.assertEqual(self.contract._get_overdue_reminder_candidates().ids, [])
        # Opt-out blocks sending
        move.write({"overdue_reminder_count": 0, "last_overdue_reminder_date": False})
        self.contract.partner_id.write({"opt_out_overdue_reminder": True})
        self.assertFalse(self.contract._send_overdue_digest())
