# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import calendar

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    billing_anchor_day = fields.Integer(
        related="contract_id.billing_anchor_day",
        readonly=True,
    )
    free_trial_discount_id = fields.Many2one(
        comodel_name="contract.invoice.discount",
        string="Free Trial Discount",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    free_trial_start = fields.Date(
        string="Free Trial Start",
        compute="_compute_free_trial_dates",
    )
    free_trial_end = fields.Date(
        string="Free Trial End",
        compute="_compute_free_trial_dates",
    )

    # === BILLING ANCHOR HELPERS === #

    def _supports_billing_anchor(self):
        self.ensure_one()
        return bool(
            not self.display_type
            and self.contract_id.line_recurrence
            and self.recurring_invoicing_type == "post-paid"
            and self.recurring_rule_type
            in ("monthly", "quarterly", "semesterly", "yearly")
            and self.date_start
            and self.contract_id.billing_anchor_day
        )

    def _should_apply_billing_anchor(self):
        self.ensure_one()
        return self._supports_billing_anchor() and not self.last_date_invoiced

    @api.model
    def _get_anchor_date(self, date, anchor_day):
        if not date:
            return False
        last_day = calendar.monthrange(date.year, date.month)[1]
        return date.replace(day=min(anchor_day or 1, last_day))

    @api.model
    def _get_next_anchor_date(self, date, anchor_day):
        if not date:
            return False
        candidate = self._get_anchor_date(date, anchor_day)
        if candidate > date:
            return candidate
        next_month = date.replace(day=1) + relativedelta(months=1)
        return self._get_anchor_date(next_month, anchor_day)

    @api.model
    def _get_anchor_date_on_or_after(self, date, anchor_day):
        if not date:
            return False
        candidate = self._get_anchor_date(date, anchor_day)
        if candidate >= date:
            return candidate
        next_month = date.replace(day=1) + relativedelta(months=1)
        return self._get_anchor_date(next_month, anchor_day)

    def _get_anchor_invoice_date(self, next_period_start):
        """Return the invoice date aligned to the billing anchor.

        For the first period the invoice date is the next anchor after the
        period start. If the service starts exactly on the anchor and the
        recurrence period is longer than one month, the first period is a
        full recurrence period instead.

        For later periods the standard recurrence date is kept when it is
        already an anchor, or moved to the next anchor when the billing day
        changed.
        """
        self.ensure_one()
        if not next_period_start or not self._supports_billing_anchor():
            return False
        if self.date_end and next_period_start > self.date_end:
            return False
        anchor_day = self.contract_id.billing_anchor_day or 1
        offset = self.recurring_invoicing_offset or 0
        if not self.last_date_invoiced:
            is_anchor_start = (
                self._get_anchor_date(next_period_start, anchor_day)
                == next_period_start
            )
            is_monthly_interval_one = (
                self.recurring_rule_type == "monthly"
                and self.recurring_interval == 1
            )
            if is_anchor_start and not is_monthly_interval_one:
                return self.get_next_invoice_date(
                    next_period_start,
                    self.recurring_invoicing_type,
                    offset,
                    self.recurring_rule_type,
                    self.recurring_interval,
                    max_date_end=self.date_end,
                )
            next_anchor = self._get_next_anchor_date(
                next_period_start, anchor_day
            )
            if not next_anchor:
                return False
            if (
                self.date_end
                and next_anchor - relativedelta(days=1) > self.date_end
            ):
                return False
            return (
                next_anchor
                - relativedelta(days=1)
                + relativedelta(days=offset)
            )
        standard_invoice_date = self.get_next_invoice_date(
            next_period_start,
            self.recurring_invoicing_type,
            offset,
            self.recurring_rule_type,
            self.recurring_interval,
            max_date_end=self.date_end,
        )
        if not standard_invoice_date:
            return False
        anchor_invoice_date = self._get_anchor_date_on_or_after(
            standard_invoice_date, anchor_day
        )
        if not anchor_invoice_date:
            return False
        if (
            self.date_end
            and anchor_invoice_date - relativedelta(days=offset) > self.date_end
        ):
            return False
        return anchor_invoice_date

    def _get_first_anchor_invoice_date(self):
        self.ensure_one()
        return self._get_anchor_invoice_date(self.date_start)

    def _get_free_trial_dates(self):
        """Return the trial range from the service start."""
        self.ensure_one()
        if not self.date_start:
            return False, False
        duration = self.contract_id.free_trial_duration or 0
        if duration <= 0:
            return False, False
        unit = self.contract_id.free_trial_unit or "months"
        delta = (
            relativedelta(days=duration)
            if unit == "days"
            else relativedelta(months=duration)
        )
        start = self.date_start
        end = start + delta - relativedelta(days=1)
        if self.date_end and end > self.date_end:
            end = self.date_end
        return start, end

    @api.depends(
        "date_start",
        "date_end",
        "recurring_invoicing_type",
        "contract_id.free_trial_duration",
        "contract_id.free_trial_unit",
    )
    def _compute_free_trial_dates(self):
        for line in self:
            if not line._supports_billing_anchor():
                line.free_trial_start = False
                line.free_trial_end = False
                continue
            start, end = line._get_free_trial_dates()
            line.free_trial_start = start
            line.free_trial_end = end

    # === RECURRENCE === #

    @api.depends(
        "next_period_date_start",
        "recurring_invoicing_type",
        "recurring_invoicing_offset",
        "recurring_rule_type",
        "recurring_interval",
        "date_end",
        "date_start",
        "last_date_invoiced",
        "contract_id.billing_anchor_day",
    )
    def _compute_recurring_next_date(self):
        super()._compute_recurring_next_date()
        for line in self:
            if line._should_apply_billing_anchor():
                line.recurring_next_date = line._get_first_anchor_invoice_date()

    # === INVOICE PREPARATION === #

    def _uses_prorated_quantity_formula(self):
        self.ensure_one()
        formula = getattr(self, "qty_formula_id", False)
        if not formula:
            return False
        return formula == self.env.ref(
            "contract_variable_qty_prorated."
            "contract_variable_qty_prorated",
            raise_if_not_found=False,
        )

    def _prepare_invoice_line(self):
        """Prorate the price when the period is partial.

        Quantity stays at 1 and the unit price is adjusted, so other
        discounts still apply on top of the prorated amount.
        """
        if self.contract_id.free_trial_duration and not self.display_type:
            self._sync_free_trial_discount()
        vals = super()._prepare_invoice_line()
        if not vals or self.display_type:
            return vals
        if self._uses_prorated_quantity_formula():
            return vals
        period_start, period_end, invoice_date = self._get_period_to_invoice(
            self.last_date_invoiced, self.recurring_next_date
        )
        if not period_start or not period_end or not invoice_date:
            return vals
        ratio = self.compute_prorated(
            period_start, period_end, invoice_date
        )
        if ratio <= 0:
            vals["price_unit"] = 0.0
            return vals
        if ratio < 1:
            vals["price_unit"] = vals.get("price_unit", 0.0) * ratio
            name = vals.get("name") or ""
            note = self.env._(
                " (prorrateado %(percent)s)", percent=f"{ratio:.2%}"
            )
            vals["name"] = f"{name}{note}".strip()
        return vals

    # === FREE TRIAL === #

    def _deactivate_free_trial_discount(self):
        if self.free_trial_discount_id:
            self.free_trial_discount_id.with_context(
                skip_free_trial_sync=True
            ).write({"active": False})

    def _sync_free_trial_discount(self):
        if self.env.context.get("skip_free_trial_sync"):
            return
        for line in self:
            contract = line.contract_id
            duration = contract.free_trial_duration or 0
            discount = contract.free_trial_discount or 0.0
            is_successor = bool(
                getattr(line, "predecessor_contract_line_id", False)
            )
            if (
                duration <= 0
                or discount <= 0
                or not line._supports_billing_anchor()
                or is_successor
            ):
                line._deactivate_free_trial_discount()
                continue
            start, end = line._get_free_trial_dates()
            if not start or not end or end < start:
                line._deactivate_free_trial_discount()
                continue
            rule = line.free_trial_discount_id
            if (
                rule
                and rule.active
                and rule.is_free_trial
                and rule.discount == discount
                and rule.date_start == start
                and rule.date_end == end
            ):
                continue
            vals = {
                "name": self.env._("Prueba gratuita"),
                "contract_line_id": line.id,
                "discount": discount,
                "start_mode": "fixed_date",
                "date_start": start,
                "date_end": end,
                "max_invoices": 0,
                "source": "promotion",
                "pause_policy": "calendar",
                "active": True,
                "is_free_trial": True,
            }
            if rule:
                rule.with_context(skip_free_trial_sync=True).write(vals)
            else:
                rule = (
                    self.env["contract.invoice.discount"]
                    .sudo()
                    .with_context(skip_free_trial_sync=True)
                    .create(vals)
                )
                line.with_context(skip_free_trial_sync=True).write(
                    {"free_trial_discount_id": rule.id}
                )

    # === CRUD === #

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for raw_vals in vals_list:
            vals = dict(raw_vals)
            self._apply_billing_anchor_to_vals(vals)
            prepared.append(vals)
        lines = super().create(prepared)
        lines._sync_free_trial_discount()
        return lines

    @api.model
    def _apply_billing_anchor_to_vals(self, vals):
        """Set the first invoice date before the line is created.

        The next invoice date is a computed field that can be provided in the
        create values. In that case Odoo does not recompute it, and the
        consistency constraint would see the wrong date. This method applies
        the billing anchor to the values before the insert.
        """
        if vals.get("display_type") or vals.get("last_date_invoiced"):
            return
        contract_id = vals.get("contract_id")
        if not contract_id:
            return
        contract = self.env["contract.contract"].browse(contract_id)
        invoicing_type = (
            vals.get("recurring_invoicing_type")
            or contract.recurring_invoicing_type
            or "pre-paid"
        )
        rule_type = (
            vals.get("recurring_rule_type")
            or contract.recurring_rule_type
            or "monthly"
        )
        if invoicing_type != "post-paid" or rule_type not in (
            "monthly",
            "quarterly",
            "semesterly",
            "yearly",
        ):
            return
        date_start = (
            fields.Date.to_date(vals.get("date_start"))
            if vals.get("date_start")
            else contract.date_start
        )
        if not date_start:
            return
        interval = int(
            vals.get("recurring_interval")
            or contract.recurring_interval
            or 1
        )
        if "date_end" in vals:
            date_end = (
                fields.Date.to_date(vals["date_end"])
                if vals["date_end"]
                else False
            )
        else:
            date_end = contract.date_end
        anchor = contract.billing_anchor_day or 1
        offset = self._get_default_recurring_invoicing_offset(
            invoicing_type, rule_type
        )
        is_anchor_start = self._get_anchor_date(date_start, anchor) == date_start
        is_monthly_interval_one = rule_type == "monthly" and interval == 1
        if is_anchor_start and not is_monthly_interval_one:
            next_date = self.get_next_invoice_date(
                date_start,
                invoicing_type,
                offset,
                rule_type,
                interval,
                max_date_end=date_end,
            )
            if next_date:
                vals["recurring_next_date"] = next_date
            return
        first_anchor = self._get_next_anchor_date(date_start, anchor)
        if not first_anchor:
            return
        if date_end and first_anchor - relativedelta(days=1) > date_end:
            return
        vals["recurring_next_date"] = (
            first_anchor
            - relativedelta(days=1)
            + relativedelta(days=offset)
        )


    def write(self, vals):
        res = super().write(vals)
        if any(
            key in vals
            for key in (
                "date_start",
                "date_end",
                "recurring_rule_type",
                "recurring_interval",
                "recurring_invoicing_type",
                "contract_id",
            )
        ):
            self._sync_free_trial_discount()
        return res

    def copy_data(self, default=None):
        values_list = super().copy_data(default=default)
        for values in values_list:
            commands = values.get("invoice_discount_ids")
            if not commands:
                continue
            values["invoice_discount_ids"] = [
                command
                for command in commands
                if not (
                    isinstance(command, (list, tuple))
                    and len(command) == 3
                    and isinstance(command[2], dict)
                    and command[2].get("is_free_trial")
                )
            ]
        return values_list
