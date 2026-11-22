# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    last_overdue_reminder_date = fields.Date(
        copy=False,
        readonly=True,
        string="Last overdue reminder",
    )
    overdue_reminder_count = fields.Integer(
        copy=False,
        readonly=True,
        default=0,
        string="Overdue reminders sent",
    )

    def _is_overdue_reminder_due(self, grace_days, resend_after_days, max_reminders):
        """Check grace + resend interval + max attempts for one invoice."""
        self.ensure_one()
        if (
            self.state != "posted"
            or self.move_type != "out_invoice"
            or self.payment_state in ("paid", "in_payment", "reversed", "invoicing_legacy")
            or self.amount_residual <= 0
        ):
            return False
        if not self.invoice_date_due:
            return False
        today = fields.Date.context_today(self)
        if (today - self.invoice_date_due).days < (grace_days or 0):
            return False
        if (max_reminders or 0) and self.overdue_reminder_count >= max_reminders:
            return False
        if self.last_overdue_reminder_date and (resend_after_days or 0):
            if (today - self.last_overdue_reminder_date).days < resend_after_days:
                return False
        return True

    def _mark_overdue_reminder_sent(self):
        today = fields.Date.context_today(self)
        for move in self:
            move.write(
                {
                    "last_overdue_reminder_date": today,
                    "overdue_reminder_count": move.overdue_reminder_count + 1,
                }
            )

    def _get_contract_overdue_invoices(self):
        """Pending posted invoices of same commercial partner and company, excl. self.

        Used only for INFORMATION in the last invoice (no consolidation).
        """
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id or self.partner_id
        domain = [
            ("company_id", "=", self.company_id.id),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            (
                "payment_state",
                "not in",
                ("paid", "in_payment", "reversed", "invoicing_legacy"),
            ),
            ("amount_residual", ">", 0),
            ("commercial_partner_id", "=", partner.id),
            ("id", "!=", self.id),
        ]
        return self.env["account.move"].search(domain, order="invoice_date_due asc")

    def _get_overdue_summary(self):
        self.ensure_one()
        overdue = self._get_contract_overdue_invoices()
        same_currency_overdue = overdue.filtered(
            lambda m: m.currency_id == self.currency_id
        )
        return {
            "count": len(overdue),
            "total_residual": sum(same_currency_overdue.mapped("amount_residual")),
            "currency": self.currency_id,
            "names": ", ".join(overdue.mapped("name")),
        }

    def _get_payment_portal_url(self):
        """Absolute portal URL with access token.

        Must be absolute (not get_portal_url() alone, which is relative):
        the link is sent as plain text over WhatsApp, where there is no
        base domain to resolve against. Also used by the email template.
        """
        self.ensure_one()
        try:
            return self.get_base_url().rstrip("/") + self.get_portal_url()
        except Exception:  # noqa: BLE001
            return ""

    def _get_notification_statement_url(self, channel_code=None):
        """Hook for statement glue modules.

        The base contract module has no statement dependency, so it returns
        an empty string. The glue overrides it to return the direct link.
        """
        self.ensure_one()
        return ""
