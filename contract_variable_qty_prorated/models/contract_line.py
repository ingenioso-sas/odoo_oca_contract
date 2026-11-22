# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    def compute_prorated(self, period_first_date, period_last_date, invoice_date):
        self.ensure_one()
        effective_invoice_date = invoice_date
        if (
            self.recurring_invoicing_type == "post-paid"
            and self.date_end
            and period_last_date == self.date_end
            and period_first_date
            and period_last_date
        ):
            theoretical_invoice_date = self.get_next_invoice_date(
                period_first_date,
                self.recurring_invoicing_type,
                self.recurring_invoicing_offset,
                self.recurring_rule_type,
                self.recurring_interval,
                max_date_end=False,
            )
            if (
                theoretical_invoice_date
                and invoice_date
                and theoretical_invoice_date > invoice_date
            ):
                effective_invoice_date = theoretical_invoice_date
        return self._compute_prorated(
            period_first_date,
            period_last_date,
            effective_invoice_date,
            self.recurring_rule_type,
            self.recurring_interval,
            self.recurring_invoicing_type,
        )

    @api.model
    def _compute_prorated(
        self,
        period_first_date,
        period_last_date,
        invoice_date,
        recurring_rule_type,
        recurring_interval,
        recurring_invoicing_type,
    ):
        def _invoiced_days(next_date, last_date):
            return (next_date - last_date).days + 1

        if (
            not period_first_date
            or not period_last_date
            or not invoice_date
            or period_last_date < period_first_date
            or recurring_interval <= 0
        ):
            return 0.0

        relative_delta = self.get_relative_delta(
            recurring_rule_type, recurring_interval
        )
        # Guard full-cycle periods against relativedelta clamping (e.g. Jan 31 / Feb 29)
        if recurring_rule_type == "monthlylastday":
            month_delta = self.get_relative_delta("monthly", recurring_interval)
            if (
                period_first_date.day == 1
                and period_first_date + month_delta - relativedelta(days=1)
                == period_last_date
            ):
                return 1.0
        elif (
            period_first_date + relative_delta - relativedelta(days=1)
            == period_last_date
        ):
            return 1.0

        theoretical_next_date = invoice_date
        if (
            recurring_rule_type == "monthlylastday"
            and recurring_invoicing_type == "post-paid"
        ):
            relative_delta = self.get_relative_delta("monthly", recurring_interval)
            theoretical_next_date += self.get_relative_delta("daily", 1)

        if recurring_invoicing_type == "pre-paid":
            if recurring_rule_type == "monthlylastday":
                theoretical_next_date += relative_delta
                theoretical_last_date = theoretical_next_date - relative_delta
                theoretical_next_date -= self.get_relative_delta("daily", 1)
            else:
                theoretical_last_date = invoice_date
                theoretical_next_date = (
                    invoice_date + relative_delta - self.get_relative_delta("daily", 1)
                )
        else:
            theoretical_last_date = theoretical_next_date - relative_delta
            theoretical_next_date -= self.get_relative_delta("daily", 1)
        theo_days = _invoiced_days(theoretical_next_date, theoretical_last_date)
        if theo_days <= 0:
            return 0.0
        return _invoiced_days(period_last_date, period_first_date) / theo_days
