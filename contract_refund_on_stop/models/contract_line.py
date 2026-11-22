# Copyright 2025 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import Command, models
from odoo.exceptions import ValidationError


class ContractLine(models.Model):
    _inherit = "contract.line"

    def stop(self, date_end, manual_renew_needed=False, post_message=True):
        if not all(self.mapped("is_stop_allowed")):
            raise ValidationError(self.env._("Stop not allowed for this line"))
        for rec in self:
            if (
                rec.display_type
                or not rec.company_id.enable_contract_line_refund_on_stop
                or not rec.last_date_invoiced
                or rec.last_date_invoiced <= date_end
            ):
                continue
            if date_end < rec.date_start:
                to_refund_start_date = rec.date_start
                new_last_date_invoiced = False
            else:
                to_refund_start_date = date_end + relativedelta(days=1)
                new_last_date_invoiced = date_end
            to_refund_end_date = rec.last_date_invoiced
            if to_refund_start_date <= to_refund_end_date:
                rec._create_refund_on_stop(
                    to_refund_start_date=to_refund_start_date,
                    to_refund_end_date=to_refund_end_date,
                )
            rec.last_date_invoiced = new_last_date_invoiced
        return super().stop(
            date_end, manual_renew_needed=manual_renew_needed, post_message=post_message
        )

    def _create_refund_on_stop(self, to_refund_start_date, to_refund_end_date):
        self.ensure_one()
        refund_vals = self._prepare_refund_on_stop_vals(
            to_refund_start_date, to_refund_end_date
        )
        if not refund_vals.get("invoice_line_ids"):
            return self.env["account.move"]
        refund = (
            self.env["account.move"]
            .with_company(self.company_id)
            .create(refund_vals)
        )
        if refund and self.contract_id:
            self.contract_id.message_post(
                body=Markup(
                    self.env._("Draft credit note created on stop: %s")
                )
                % refund._get_html_link(title=refund.display_name)
            )
        return refund

    def _prepare_refund_on_stop_vals(self, to_refund_start_date, to_refund_end_date):
        self.ensure_one()
        refund_vals = self.contract_id._prepare_invoice(to_refund_start_date)
        move_type = (
            "in_refund" if refund_vals["move_type"] == "in_invoice" else "out_refund"
        )
        refund_vals["move_type"] = move_type
        line_vals = self._prepare_refund_on_stop_line(
            to_refund_start_date, to_refund_end_date
        )
        if line_vals.get("quantity", 0) > 0:
            refund_vals["invoice_line_ids"] = [Command.create(line_vals)]
        else:
            refund_vals["invoice_line_ids"] = []
        return refund_vals

    def _prepare_refund_on_stop_line(self, to_refund_start_date, to_refund_end_date):
        self.ensure_one()
        line_vals = self.with_context(
            contract_refund_period=(to_refund_start_date, to_refund_end_date),
            skip_zero_qty_check=True,
        )._prepare_invoice_line()
        line_vals.pop("company_id", None)
        line_vals.pop("company_currency_id", None)
        line_vals["name"] = self._get_refund_on_stop_line_name(
            to_refund_start_date, to_refund_end_date
        )
        line_vals["quantity"] = self._get_refund_on_stop_quantity(
            to_refund_start_date, to_refund_end_date
        )
        return line_vals

    def _get_refund_on_stop_line_name(self, to_refund_start_date, to_refund_end_date):
        lang = self.env["res.lang"].search(
            [("code", "=", self.contract_id.partner_id.lang)]
        )
        date_format = lang.date_format or "%m/%d/%Y"
        return self.env._(
            "Refund for period %(to_refund_start_date)s %(to_refund_end_date)s",
            to_refund_start_date=to_refund_start_date.strftime(date_format),
            to_refund_end_date=to_refund_end_date.strftime(date_format),
        )

    def _get_refund_on_stop_quantity(self, to_refund_start_date, to_refund_end_date):
        """
        Compute the total refund quantity for a contract line.

        This method calculates the prorated quantity to be refunded when a contract
        line is stopped before the end of the last invoiced period.

        The computation is done **period by period**, to properly handle cases where
        the refund interval spans multiple theoretical billing periods. For each
        period, the prorated quantity is computed based on the refund start and end
        dates, and then accumulated to obtain the total refund quantity.

        :param date to_refund_start_date: Start date of the refund period.
        :param date to_refund_end_date: End date of the refund period.
        :return: Total prorated refund quantity.
        :rtype: float
        """
        self.ensure_one()
        quantity = 0
        while to_refund_start_date <= to_refund_end_date:
            next_period_date_end = min(
                (
                    to_refund_start_date
                    + self.get_relative_delta(
                        self.recurring_rule_type, self.recurring_interval
                    )
                    - relativedelta(days=1)
                ),
                to_refund_end_date,
            )
            invoice_date = self.get_next_invoice_date(
                to_refund_start_date,
                self.recurring_invoicing_type,
                self.recurring_invoicing_offset,
                self.recurring_rule_type,
                self.recurring_interval,
                max_date_end=next_period_date_end,
            )
            quantity += self.quantity * self.compute_prorated(
                to_refund_start_date, next_period_date_end, invoice_date
            )
            to_refund_start_date = next_period_date_end + relativedelta(days=1)
        return quantity
