# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from markupsafe import Markup

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ContractContract(models.Model):
    _inherit = "contract.contract"

    notification_channel_ids = fields.Many2many(
        string="Notification Channels",
        comodel_name="contract.notification.channel",
        default=lambda self: self._default_notification_channel_ids(),
        help="Channels used for invoice notifications and overdue digests. "
        "Selecting email and WhatsApp sends both.",
    )
    notification_template_ids = fields.One2many(
        string="Notification Template Overrides",
        comodel_name="contract.notification.template",
        inverse_name="contract_id",
        copy=True,
        help="Optional per-contract template overrides by channel and purpose.",
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

    @api.model
    def _default_notification_channel_ids(self):
        channel = self.env.ref(
            "contract_invoice_notify.notification_channel_email",
            raise_if_not_found=False,
        )
        return channel or self.env["contract.notification.channel"]

    @api.onchange("contract_template_id")
    def _onchange_contract_template_id(self):
        super()._onchange_contract_template_id()
        tmpl = self.contract_template_id
        if tmpl:
            self.notification_channel_ids = tmpl.notification_channel_ids
            self.overdue_reminder_enabled = tmpl.overdue_reminder_enabled
            self.overdue_grace_days = tmpl.overdue_grace_days
            self.overdue_resend_after_days = tmpl.overdue_resend_after_days
            self.overdue_max_reminders = tmpl.overdue_max_reminders

    # === TEMPLATES === #

    def _get_invoice_email_template(self):
        self.ensure_one()
        if self.invoice_mail_template_id:
            return self.invoice_mail_template_id
        template = self.env.ref(
            "contract_invoice_notify.email_template_contract_invoice_notify",
            raise_if_not_found=False,
        )
        if not template:
            template = self.env.ref(
                "account.email_template_edi_invoice", raise_if_not_found=False
            )
        return template or self.env["mail.template"]

    def _get_overdue_email_template(self):
        self.ensure_one()
        return (
            self.env.ref(
                "contract_invoice_notify.email_template_contract_overdue_digest",
                raise_if_not_found=False,
            )
            or self.env["mail.template"]
        )

    def _get_explicit_notification_template(self, record, purpose, channel_code):
        """Return only an explicit per-contract template override (no default fallback)."""
        self.ensure_one()
        override = self.notification_template_ids.filtered(
            lambda line: line.channel_id.code == channel_code
            and line.purpose == purpose
        )[:1]
        if override:
            expected_model = (
                "account.move"
                if purpose == "invoice_notification"
                else "contract.contract"
            )
            template = override.template_id
            if template.model_id.model == expected_model:
                return template
        if (
            channel_code == "email"
            and purpose == "invoice_notification"
            and self.invoice_mail_template_id
        ):
            return self.invoice_mail_template_id
        return self.env["mail.template"]

    def _get_notification_template(self, record, purpose, channel_code):
        self.ensure_one()
        override = self.notification_template_ids.filtered(
            lambda line: line.channel_id.code == channel_code
            and line.purpose == purpose
        )[:1]
        if override:
            expected_model = (
                "account.move"
                if purpose == "invoice_notification"
                else "contract.contract"
            )
            template = override.template_id
            if template.model_id.model == expected_model:
                return template
            _logger.warning(
                "Ignoring notification template override %s for contract %s: "
                "expected model %s, got %s.",
                template.display_name,
                self.display_name,
                expected_model,
                template.model_id.model,
            )
        if channel_code == "email":
            if purpose == "invoice_notification":
                return self._get_invoice_email_template()
            if purpose == "overdue_digest":
                return self._get_overdue_email_template()
        if channel_code == "whatsapp" and purpose == "invoice_notification":
            return (
                self.env.ref(
                    "contract_invoice_notify."
                    "whatsapp_template_contract_invoice",
                    raise_if_not_found=False,
                )
                or self.env["mail.template"]
            )
        return self.env["mail.template"]

    # === NOTIFICATION DISPATCH === #

    def _get_notification_channels(self):
        self.ensure_one()
        configured = self.with_context(active_test=False).notification_channel_ids
        if configured:
            return configured.filtered("active")
        return self.env["contract.notification.channel"].search(
            [("code", "=", "email"), ("active", "=", True)], limit=1
        )

    def _get_notification_context(
        self, record, purpose, channel_code, invoices=None
    ):
        self.ensure_one()
        statement_url = ""
        getter = getattr(record, "_get_notification_statement_url", None)
        if getter:
            statement_url = getter(channel_code=channel_code)
        return {
            "contract": self,
            "record": record,
            "purpose": purpose,
            "channel_code": channel_code,
            "invoices": invoices or self.env["account.move"],
            "statement_url": statement_url,
        }

    def _get_notification_statement_url(self, channel_code=None):
        """Hook for statement glue modules."""
        self.ensure_one()
        return ""

    def _send_notification(self, record, purpose, channel_code, invoices=None):
        self.ensure_one()
        template = self._get_notification_template(
            record, purpose, channel_code
        )
        context = self._get_notification_context(
            record, purpose, channel_code, invoices=invoices
        )
        return self.env["contract.notification.driver"].send(
            self,
            record,
            purpose,
            channel_code,
            template=template,
            context=context,
        )

    # === INVOICE NOTIFICATION === #

    def _auto_validate_invoices(self, moves):
        """Unified post + notify for the configured channels.

        Keeps accounting untouched: overdue invoices are only REPORTED in
        the message, never merged into the new invoice.
        """
        for contract in self:
            contract_moves = moves & contract._get_related_invoices()
            if not contract_moves or contract.invoicing_mode == "draft":
                continue
            draft_moves = contract_moves.filtered(lambda m: m.state == "draft")
            if not draft_moves:
                continue
            try:
                with self.env.cr.savepoint():
                    draft_moves.action_post()
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "Could not auto-validate invoices %s for contract %s: %s",
                    draft_moves.ids,
                    contract.display_name,
                    exc,
                )
                contract.message_post(
                    body=Markup(self.env._("Automatic validation failed: %s")) % exc
                )
                continue
            if (
                contract.invoicing_mode != "validate_send"
                or contract.contract_type != "sale"
            ):
                continue
            channels = contract._get_notification_channels()
            for move in draft_moves.filtered(
                lambda m: m.state == "posted" and m.move_type == "out_invoice"
            ):
                results = {}
                for channel in channels:
                    try:
                        with self.env.cr.savepoint():
                            results[channel.code] = contract._send_notification(
                                move, "invoice_notification", channel.code
                            )
                    except Exception as exc:  # noqa: BLE001
                        _logger.warning(
                            "Could not notify invoice %s via %s: %s",
                            move.name,
                            channel.code,
                            exc,
                        )
                        results[channel.code] = False
                summary = move._get_overdue_summary()
                extra = ""
                if summary["count"]:
                    extra = self.env._(
                        " (%(count)s overdue: %(names)s, residual %(total)s)",
                        count=summary["count"],
                        names=summary["names"],
                        total=summary["total_residual"],
                    )
                notified = ", ".join(
                    code for code, sent in results.items() if sent
                ) or self.env._("no channel")
                move.message_post(
                    body=Markup(
                        self.env._(
                            "Invoice auto-validated and notified "
                            "(%(mode)s) from contract %(contract)s%(extra)s"
                        )
                    )
                    % {
                        "mode": notified,
                        "contract": contract._get_html_link(),
                        "extra": extra,
                    }
                )

    # === OVERDUE DIGEST === #

    def _get_overdue_reminder_candidates(self):
        """Digest per contract: overdue + grace/resend/max eligible invoices.

        Called by the daily cron and by the email template, so both use the
        same rule. Never merges amounts, only lists documents.
        """
        self.ensure_one()
        pending = self._get_related_invoices().filtered(
            lambda m: m.move_type == "out_invoice"
            and m.state == "posted"
            and m.payment_state
            not in ("paid", "in_payment", "reversed", "invoicing_legacy")
            and m.amount_residual > 0
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
        try:
            if not invoices:
                return ""
            inv = invoices[:1]
            return inv.get_base_url().rstrip("/") + inv.get_portal_url()
        except Exception:  # noqa: BLE001
            return ""

    def _is_overdue_reminder_opted_out(self):
        self.ensure_one()
        partners = self.partner_id | self.commercial_partner_id | self.invoice_partner_id
        return any(
            getattr(partner, "opt_out_overdue_reminder", False)
            for partner in partners
            if partner
        )

    def _send_overdue_digest(self, invoices=None):
        """Send one digest per contract through the configured channels."""
        self.ensure_one()
        if not self.overdue_reminder_enabled:
            return False
        if self._is_overdue_reminder_opted_out():
            return False
        invoices = invoices or self._get_overdue_reminder_candidates()
        if not invoices:
            return False

        successes = []
        for channel in self._get_notification_channels():
            if self._send_notification(
                self, "overdue_digest", channel.code, invoices=invoices
            ):
                successes.append(channel.code)

        if successes:
            invoices._mark_overdue_reminder_sent()
            self.message_post(
                body=Markup(
                    self.env._("Overdue digest sent (%(mode)s): %(names)s")
                )
                % {
                    "mode": ", ".join(successes),
                    "names": ", ".join(invoices.mapped("name")),
                }
            )
            for move in invoices:
                move.message_post(
                    body=Markup(
                        self.env._("Overdue reminder sent from contract %s.")
                    )
                    % self._get_html_link()
                )
            return True

        self.message_post(
            body=Markup(
                self.env._(
                    "Overdue digest not sent: no configured channel succeeded "
                    "for %s."
                )
            )
            % ", ".join(invoices.mapped("name"))
        )
        return False

    @api.model
    def cron_overdue_reminders(self):
        """Daily cron: one digest per contract with eligible overdue invoices."""
        today = fields.Date.context_today(self)
        grouped_lines = self.env["account.move.line"]._read_group(
            domain=[
                ("contract_line_id.contract_id.overdue_reminder_enabled", "=", True),
                ("contract_line_id.contract_id.contract_type", "=", "sale"),
                ("move_id.move_type", "=", "out_invoice"),
                ("move_id.state", "=", "posted"),
                (
                    "move_id.payment_state",
                    "not in",
                    ("paid", "in_payment", "reversed", "invoicing_legacy"),
                ),
                ("move_id.amount_residual", ">", 0),
                ("move_id.invoice_date_due", "<=", today),
            ],
            groupby=["contract_line_id"],
        )
        candidate_lines = self.env["contract.line"].union(
            *[row[0] for row in grouped_lines if row[0]]
        )
        contracts = candidate_lines.mapped("contract_id").filtered(
            lambda c: c.overdue_reminder_enabled and c.contract_type == "sale"
        )
        count = 0
        in_test_mode = self.env.registry.in_test_mode()
        for contract in contracts:
            contract = contract.with_company(contract.company_id)
            try:
                with self.env.cr.savepoint():
                    candidates = contract._get_overdue_reminder_candidates()
                    if candidates and contract._send_overdue_digest(candidates):
                        count += 1
                if not in_test_mode:
                    self.env.cr.commit()
            except Exception as exc:  # noqa: BLE001 - keep cron robust
                _logger.warning(
                    "Overdue digest failed for %s: %s", contract.display_name, exc
                )
        _logger.info("Overdue digests sent for %s contract(s).", count)
        return True

    def action_resend_last_invoice_notification(self):
        """Manual resend for support (uses the configured channels)."""
        self.ensure_one()
        invoices = (
            self._get_related_invoices()
            .filtered(lambda m: m.state == "posted" and m.move_type == "out_invoice")
            .sorted(
                lambda m: (
                    m.invoice_date
                    or (m.create_date.date() if m.create_date else fields.Date.today()),
                    m.id,
                ),
                reverse=True,
            )[:1]
        )
        if not invoices:
            return False
        move = invoices[0]
        successes = []
        for channel in self._get_notification_channels():
            if self._send_notification(move, "invoice_notification", channel.code):
                successes.append(channel.code)
        if successes:
            move.message_post(
                body=Markup(
                    self.env._(
                        "Manual invoice notification resent (%(mode)s) from contract %(contract)s."
                    )
                )
                % {"mode": ", ".join(successes), "contract": self._get_html_link()}
            )
            return True
        return False
