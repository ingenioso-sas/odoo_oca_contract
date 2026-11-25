# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from dateutil.relativedelta import relativedelta

from odoo import _, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class ContractLine(models.Model):
    _inherit = "contract.line"

    # === ACCESS === #

    def _check_regenerate_access(self):
        self.ensure_one()
        if not self.env.user.has_group(
            "contract_invoice_regenerate.group_contract_invoice_regenerate"
        ):
            raise AccessError(
                _("Solo los administradores pueden regenerar facturas de contrato.")
            )

    # === INVOICE PERIOD HELPERS === #

    def _get_contract_invoice_lines(self):
        """Return the draft/posted invoice lines that belong to this line."""
        self.ensure_one()
        return self.env["account.move.line"].search(
            [
                ("contract_line_id", "=", self.id),
                ("display_type", "in", (False, "product")),
                ("move_id.move_type", "in", ("out_invoice", "in_invoice")),
                ("move_id.state", "in", ("draft", "posted")),
            ]
        )

    def _get_invoice_line_period(self, invoice_line):
        """Return the billing period of an invoice line.

        ``contract_invoice_period`` stores the period in structured fields.
        Old invoices created before that module do not have them, so this
        method falls back to the contract billing date or the invoice date.
        """
        self.ensure_one()
        if invoice_line.contract_period_start and invoice_line.contract_period_end:
            return (
                invoice_line.contract_period_start,
                invoice_line.contract_period_end,
            )
        move = invoice_line.move_id
        billing_date = (
            invoice_line.contract_billing_date
            or move.contract_billing_date
            or move.invoice_date
            or move.date
        )
        if not billing_date:
            return False, False
        offset = self.recurring_invoicing_offset or 0
        if self.recurring_invoicing_type == "pre-paid":
            period_start = billing_date - relativedelta(days=offset)
            period_end = self.get_next_period_date_end(
                period_start,
                self.recurring_rule_type,
                self.recurring_interval,
                max_date_end=self.date_end,
            )
        else:
            period_end = billing_date - relativedelta(days=offset)
            period_start = (
                period_end
                - self.get_relative_delta(
                    self.recurring_rule_type, self.recurring_interval
                )
                + relativedelta(days=1)
            )
            if period_start > period_end:
                period_start = period_end
        return period_start, period_end

    def _get_invoice_lines_for_period(self, period_start, period_end):
        """Return invoice lines that overlap the given period."""
        self.ensure_one()
        result = self.env["account.move.line"]
        for invoice_line in self._get_contract_invoice_lines():
            line_start, line_end = self._get_invoice_line_period(invoice_line)
            if (
                line_start
                and line_end
                and line_start <= period_end
                and line_end >= period_start
            ):
                result |= invoice_line
        return result

    def _get_last_invoiced_period_end(self):
        """Return the end of the last period already invoiced."""
        self.ensure_one()
        period_ends = []
        for invoice_line in self._get_contract_invoice_lines():
            _period_start, period_end = self._get_invoice_line_period(
                invoice_line
            )
            if period_end:
                period_ends.append(period_end)
        return max(period_ends) if period_ends else False

    def _get_recalculated_next_invoice_date(self, next_period_start):
        """Return the next invoice date, respecting an optional billing anchor."""
        self.ensure_one()
        anchor_getter = getattr(self, "_get_anchor_invoice_date", None)
        if anchor_getter:
            anchor_date = anchor_getter(next_period_start)
            if anchor_date:
                return anchor_date
        return self.get_next_invoice_date(
            next_period_start,
            self.recurring_invoicing_type,
            self.recurring_invoicing_offset,
            self.recurring_rule_type,
            self.recurring_interval,
            max_date_end=self.date_end,
        )

    def _get_recalculated_invoice_dates(self):
        """Return the dates that match the current contract invoices."""
        self.ensure_one()
        last_date_invoiced = self._get_last_invoiced_period_end()
        next_period_start = (
            last_date_invoiced + relativedelta(days=1)
            if last_date_invoiced
            else self.date_start
        )
        if not next_period_start:
            return last_date_invoiced, False
        recurring_next_date = self._get_recalculated_next_invoice_date(
            next_period_start
        )
        return last_date_invoiced, recurring_next_date

    def _recalculate_invoice_dates(self):
        """Synchronize the contract dates with the existing invoices."""
        self.ensure_one()
        last_date_invoiced, recurring_next_date = (
            self._get_recalculated_invoice_dates()
        )
        self.write(
            {
                "last_date_invoiced": last_date_invoiced,
                "recurring_next_date": recurring_next_date,
            }
        )
        return last_date_invoiced, recurring_next_date

    # === ACTIONS === #

    def action_recalculate_invoice_dates(self):
        """Recalculate the dates from the invoices that still exist."""
        self.ensure_one()
        self._check_regenerate_access()
        if self.display_type and not self.is_recurring_note:
            raise UserError(
                _(
                    "Solo las líneas recurrentes de producto permiten "
                    "recalcular fechas."
                )
            )
        last_date_invoiced, recurring_next_date = (
            self._recalculate_invoice_dates()
        )
        last_label = (
            last_date_invoiced.isoformat()
            if last_date_invoiced
            else _("Ninguna")
        )
        next_label = (
            recurring_next_date.isoformat()
            if recurring_next_date
            else _("Ninguna")
        )
        self.contract_id.message_post(
            body=_(
                "Fechas recalculadas desde las facturas existentes: "
                "última fecha facturada %(last)s, próxima factura %(next)s.",
                last=last_label,
                next=next_label,
            )
        )
        return True

    def action_regenerate_invoice(self):
        """Open the wizard to recreate the next missing period."""
        self.ensure_one()
        self._check_regenerate_access()
        if self.display_type and not self.is_recurring_note:
            raise UserError(
                _(
                    "Solo las líneas recurrentes de producto permiten "
                    "regenerar facturas."
                )
            )
        last_date_invoiced, _next_date = (
            self._get_recalculated_invoice_dates()
        )
        period_start = (
            last_date_invoiced + relativedelta(days=1)
            if last_date_invoiced
            else self.date_start
        )
        if not period_start:
            raise UserError(
                _("La línea del contrato no tiene fecha de inicio para regenerar.")
            )
        period_end = self.get_next_period_date_end(
            period_start,
            self.recurring_rule_type,
            self.recurring_interval,
            max_date_end=self.date_end,
        )
        if not period_end:
            raise UserError(
                _("La línea del contrato no tiene un período pendiente por facturar.")
            )
        invoice_date = self.get_next_invoice_date(
            period_start,
            self.recurring_invoicing_type,
            self.recurring_invoicing_offset,
            self.recurring_rule_type,
            self.recurring_interval,
            max_date_end=self.date_end,
        )
        if not invoice_date:
            invoice_date = period_end
        return {
            "type": "ir.actions.act_window",
            "name": _("Regenerate contract invoice"),
            "res_model": "contract.regenerate.invoice",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_contract_line_id": self.id,
                "default_period_start": period_start,
                "default_period_end": period_end,
                "default_invoice_date": invoice_date,
            },
        }

    # === INVOICE PREPARATION === #

    def _get_period_to_invoice(
        self, last_date_invoiced, recurring_next_date, stop_at_date_end=True
    ):
        """Return the explicit period while regenerating an invoice."""
        override = self.env.context.get("contract_invoice_period_override")
        if override:
            return (
                override["period_start"],
                override["period_end"],
                override["invoice_date"],
            )
        return super()._get_period_to_invoice(
            last_date_invoiced,
            recurring_next_date,
            stop_at_date_end=stop_at_date_end,
        )

    def _prepare_invoice_line(self):
        """Allow an explicit period when regenerating an invoice."""
        vals = super()._prepare_invoice_line()
        override = self.env.context.get("contract_invoice_period_override")
        if vals and override:
            vals.update(
                {
                    "contract_period_start": override["period_start"],
                    "contract_period_end": override["period_end"],
                    "contract_billing_date": override["invoice_date"],
                }
            )
        return vals
