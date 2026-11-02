# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


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
        if self.state != "posted" or self.payment_state in ("paid", "in_payment"):
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
        self.write(
            {
                "last_overdue_reminder_date": today,
                "overdue_reminder_count": self.overdue_reminder_count + 1,
            }
        )

    def _get_contract_overdue_invoices(self):
        """Pending posted invoices of same commercial partner, excl. self.

        Used only for INFORMATION in the last invoice (no consolidation).
        """
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id or self.partner_id
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "not in", ("paid", "in_payment")),
            ("commercial_partner_id", "=", partner.id),
            ("id", "!=", self.id),
        ]
        return self.env["account.move"].search(domain, order="invoice_date_due asc")

    def _get_overdue_summary(self):
        self.ensure_one()
        overdue = self._get_contract_overdue_invoices()
        return {
            "count": len(overdue),
            "total_residual": sum(overdue.mapped("amount_residual")),
            "currency": self.currency_id,
            "names": ", ".join(overdue.mapped("name")),
        }

    def _get_payment_portal_url(self):
        """Portal URL with access token; shows Pay Now when PSP configured."""
        self.ensure_one()
        try:
            return self.get_portal_url()
        except Exception:  # noqa: BLE001
            return ""

    def _get_whatsapp_text(self):
        self.ensure_one()
        base_url = self._get_payment_portal_url()
        summary = self._get_overdue_summary()
        lines = [
            f"Hola {self.partner_id.display_name},",
            f"Tu factura {self.name} por {self.amount_total} {self.currency_id.name} "
            f"ya está disponible.",
            f"Puedes verla y pagarla aquí: {base_url}" if base_url else "",
        ]
        if summary["count"]:
            lines.append(
                f"Además tienes {summary['count']} factura(s) pendiente(s) "
                f"({summary['names']}) por "
                f"{summary['total_residual']} {self.currency_id.name}. "
                "Puedes pagarlas todas desde tu portal."
            )
        return "\n".join([line for line in lines if line])
