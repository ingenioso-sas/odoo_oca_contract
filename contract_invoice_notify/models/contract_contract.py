# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import logging

from markupsafe import Markup

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ContractContract(models.Model):
    _inherit = "contract.contract"

    send_notification_mode = fields.Selection(
        selection=[
            ("email", "Email"),
            ("whatsapp", "WhatsApp"),
            ("both", "Email + WhatsApp"),
        ],
        default="email",
        required=True,
        string="Invoice notification channel",
        help="Used when invoicing mode is 'Validate and send by email'.",
    )
    overdue_reminder_enabled = fields.Boolean(
        default=False,
        string="Overdue reminders",
        help="Send periodic digest reminders for overdue invoices of this "
        "contract (one digest per contract, never merges amounts).",
    )
    overdue_grace_days = fields.Integer(
        default=3,
        string="Grace days",
    )
    overdue_resend_after_days = fields.Integer(
        default=7,
        string="Resend every (days)",
    )
    overdue_max_reminders = fields.Integer(
        default=4,
        string="Max reminders",
        help="Max digest reminders per invoice. 0 = unlimited.",
    )

    def _get_invoice_email_template(self):
        self.ensure_one()
        if self.invoice_mail_template_id:
            return self.invoice_mail_template_id
        # Our template adds payment link + overdue info block.
        template = self.env.ref(
            "contract_invoice_notify.email_template_contract_invoice_notify",
            raise_if_not_found=False,
        )
        if not template:
            template = self.env.ref(
                "account.email_template_edi_invoice", raise_if_not_found=False
            )
        return template

    def _send_invoice_email(self, move):
        template = self._get_invoice_email_template()
        if not template:
            return False
        try:
            template.send_mail(move.id, force_send=False, raise_exception=False)
            return True
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Could not send invoice %s by email: %s", move.id, exc)
            return False

    def _send_invoice_whatsapp(self, move):
        mobile = (move.partner_id.mobile or move.partner_id.phone or "").strip()
        if not mobile:
            move.message_post(
                body=Markup(
                    _("WhatsApp skipped: customer %s has no mobile/phone.")
                    % move.partner_id.display_name
                )
            )
            return False
        message = move._get_whatsapp_text()
        pdf_base64 = None
        filename = f"{move.name or 'invoice'}.pdf"
        try:
            pdf_content, _ext = self.env["ir.actions.report"]._render_qweb_pdf(
                "account.account_invoices", [move.id]
            )
            pdf_base64 = base64.b64encode(pdf_content).decode()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Could not render invoice PDF %s: %s", move.id, exc)
        driver = self.env["contract.whatsapp.driver"]
        # Use queue_job when available so cron is never blocked by the API.
        if "queue.job" in self.env and not self.env.context.get("no_whatsapp_delay"):
            try:
                driver.with_delay().send_whatsapp(
                    mobile, message, pdf_base64, filename
                )
                return True
            except Exception as exc:  # noqa: BLE001
                _logger.warning("Could not queue WhatsApp: %s", exc)
        return bool(driver.send_whatsapp(mobile, message, pdf_base64, filename))

    def _auto_validate_invoices(self, moves):
        """Unified post + notify (overrides contract base to add WhatsApp).

        Keeps accounting untouched: overdue invoices are only REPORTED in
        the message, never merged into the new invoice (decision punto 5).
        """
        for contract in self:
            contract_moves = moves & contract._get_related_invoices()
            if not contract_moves or contract.invoicing_mode == "draft":
                continue
            draft_moves = contract_moves.filtered(lambda m: m.state == "draft")
            if not draft_moves:
                continue
            try:
                draft_moves.action_post()
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "Could not auto-validate invoices %s for contract %s: %s",
                    draft_moves.ids,
                    contract.display_name,
                    exc,
                )
                contract.message_post(
                    body=Markup(_("Automatic validation failed: %s") % exc)
                )
                continue
            if contract.invoicing_mode != "validate_send":
                continue
            mode = contract.send_notification_mode or "email"
            for move in draft_moves.filtered(lambda m: m.state == "posted"):
                if mode in ("email", "both"):
                    contract._send_invoice_email(move)
                if mode in ("whatsapp", "both"):
                    contract.with_context(
                        no_whatsapp_delay=self.env.context.get(
                            "no_whatsapp_delay", False
                        )
                    )._send_invoice_whatsapp(move)
                summary = move._get_overdue_summary()
                extra = ""
                if summary["count"]:
                    extra = _(
                        " (%(count)s overdue: %(names)s, residual %(total)s)"
                    ) % {
                        "count": summary["count"],
                        "names": summary["names"],
                        "total": summary["total_residual"],
                    }
                move.message_post(
                    body=Markup(
                        _("Invoice auto-validated and notified (%(mode)s) "
                          "from contract %(contract)s%(extra)s")
                        % {
                            "mode": mode,
                            "contract": contract._get_html_link(),
                            "extra": extra,
                        }
                    )
                )

    def _get_overdue_reminder_candidates(self):
        """Digest per contract: overdue + grace/resend/max eligible invoices.

        Called by the daily cron and by the email template, so both use the
        same rule. Never merges amounts, only lists documents.
        """
        self.ensure_one()
        pending = self._get_related_invoices().filtered(
            lambda m: m.move_type == "out_invoice"
            and m.state == "posted"
            and m.payment_state not in ("paid", "in_payment")
        )
        return pending.filtered(
            lambda m: m._is_overdue_reminder_due(
                self.overdue_grace_days,
                self.overdue_resend_after_days,
                self.overdue_max_reminders,
            )
        ).sorted("invoice_date_due")

    def _get_overdue_pay_all_url(self, invoices):
        self.ensure_one()
        if hasattr(self, "_create_pay_all_link") and invoices:
            try:
                return self._create_pay_all_link()
            except Exception:  # noqa: BLE001
                pass
        # Fallback: portal of the oldest overdue invoice.
        try:
            return invoices[:1].get_portal_url() if invoices else ""
        except Exception:  # noqa: BLE001
            return ""

    def _get_overdue_whatsapp_text(self, invoices):
        self.ensure_one()
        total = sum(invoices.mapped("amount_residual"))
        cur = invoices[:1].currency_id.name if invoices else self.currency_id.name
        names = ", ".join(invoices.mapped("name"))
        url = self._get_overdue_pay_all_url(invoices)
        lines = [
            f"Hola {self.partner_id.display_name},",
            f"Contrato {self.name}: tienes {len(invoices)} factura(s) vencida(s) "
            f"({names}) por {total} {cur}.",
        ]
        if url:
            lines.append(f"Págalas todas aquí: {url}")
        return "\n".join(lines)

    def _send_overdue_digest(self, invoices=None):
        """Send one digest per contract via configured channel."""
        self.ensure_one()
        if not self.overdue_reminder_enabled:
            return False
        if self.partner_id.opt_out_overdue_reminder if hasattr(
            self.partner_id, "opt_out_overdue_reminder"
        ) else False:
            return False
        invoices = invoices or self._get_overdue_reminder_candidates()
        if not invoices:
            return False
        mode = self.send_notification_mode or "email"
        if mode in ("email", "both"):
            template = self.env.ref(
                "contract_invoice_notify.email_template_contract_overdue_digest",
                raise_if_not_found=False,
            )
            if template:
                try:
                    template.send_mail(
                        self.id, force_send=False, raise_exception=False
                    )
                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "Could not send overdue digest for %s: %s",
                        self.display_name,
                        exc,
                    )
        if mode in ("whatsapp", "both"):
            mobile = (self.partner_id.mobile or self.partner_id.phone or "").strip()
            if mobile:
                message = self._get_overdue_whatsapp_text(invoices)
                driver = self.env["contract.whatsapp.driver"]
                if "queue.job" in self.env and not self.env.context.get(
                    "no_whatsapp_delay"
                ):
                    try:
                        driver.with_delay().send_whatsapp(mobile, message)
                    except Exception as exc:  # noqa: BLE001
                        _logger.warning("Could not queue overdue WhatsApp: %s", exc)
                        driver.send_whatsapp(mobile, message)
                else:
                    driver.send_whatsapp(mobile, message)
            else:
                self.message_post(
                    body=Markup(
                        _("Overdue WhatsApp skipped: no mobile for %s.")
                        % self.partner_id.display_name
                    )
                )
        invoices._mark_overdue_reminder_sent()
        self.message_post(
            body=Markup(
                _("Overdue digest sent (%(mode)s): %(names)s") % {
                    "mode": mode,
                    "names": ", ".join(invoices.mapped("name")),
                }
            )
        )
        for move in invoices:
            move.message_post(
                body=Markup(
                    _("Overdue reminder sent from contract %s.")
                    % self._get_html_link()
                )
            )
        return True

    @api.model
    def cron_overdue_reminders(self):
        """Daily cron: one digest per contract with eligible overdue invoices."""
        contracts = self.search([("overdue_reminder_enabled", "=", True)])
        count = 0
        for contract in contracts:
            try:
                candidates = contract._get_overdue_reminder_candidates()
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "Overdue scan failed for %s: %s", contract.display_name, exc
                )
                continue
            if not candidates:
                continue
            try:
                if contract._send_overdue_digest(candidates):
                    count += 1
            except Exception as exc:  # noqa: BLE001 - keep cron robust
                _logger.warning(
                    "Overdue digest failed for %s: %s", contract.display_name, exc
                )
        _logger.info("Overdue digests sent for %s contract(s).", count)
        return True

    def action_resend_last_invoice_notification(self):
        """Manual resend for support (uses same channel + payment link)."""
        self.ensure_one()
        invoices = self._get_related_invoices().filtered(
            lambda m: m.state == "posted"
        ).sorted("invoice_date", reverse=True)[:1]
        if not invoices:
            return False
        move = invoices[0]
        mode = self.send_notification_mode or "email"
        if mode in ("email", "both"):
            self._send_invoice_email(move)
        if mode in ("whatsapp", "both"):
            self._send_invoice_whatsapp(move)
        return True
