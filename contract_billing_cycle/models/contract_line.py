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

    def _get_first_anchor_invoice_date(self):
        self.ensure_one()
        if not self.date_start:
            return False
        first_anchor = self._get_next_anchor_date(
            self.date_start, self.contract_id.billing_anchor_day or 1
        )
        if not first_anchor:
            return False
        return (
            first_anchor
            - relativedelta(days=1)
            + relativedelta(days=self.recurring_invoicing_offset or 0)
        )

    def _get_first_full_period_start(self):
        self.ensure_one()
        if not self.date_start:
            return False
        anchor_day = self.contract_id.billing_anchor_day or 1
        if self._get_anchor_date(self.date_start, anchor_day) == self.date_start:
            return self.date_start
        return self._get_next_anchor_date(self.date_start, anchor_day)

    def _get_free_trial_end(self, start, periods):
        self.ensure_one()
        if not start or periods <= 0:
            return False
        period_start = start
        period_end = False
        for _index in range(periods):
            period_end = self.get_next_period_date_end(
                period_start,
                self.recurring_rule_type,
                self.recurring_interval,
                max_date_end=self.date_end,
            )
            if not period_end:
                break
            period_start = period_end + relativedelta(days=1)
        return period_end

    @api.depends(
        "date_start",
        "date_end",
        "recurring_rule_type",
        "recurring_interval",
        "recurring_invoicing_type",
        "contract_id.billing_anchor_day",
        "contract_id.free_trial_periods",
    )
    def _compute_free_trial_dates(self):
        for line in self:
            periods = line.contract_id.free_trial_periods or 0
            if periods <= 0 or not line._supports_billing_anchor():
                line.free_trial_start = False
                line.free_trial_end = False
                continue
            start = line._get_first_full_period_start()
            line.free_trial_start = start
            line.free_trial_end = line._get_free_trial_end(start, periods)

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
            periods = contract.free_trial_periods or 0
            discount = contract.free_trial_discount or 0.0
            is_successor = bool(
                getattr(line, "predecessor_contract_line_id", False)
            )
            if line.last_date_invoiced:
                continue
            if (
                periods <= 0
                or discount <= 0
                or not line._supports_billing_anchor()
                or is_successor
            ):
                line._deactivate_free_trial_discount()
                continue
            start = line._get_first_full_period_start()
            end = line._get_free_trial_end(start, periods)
            if not start or not end or end < start:
                line._deactivate_free_trial_discount()
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
            rule = line.free_trial_discount_id
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
            else False
        )
        if not date_start:
            return
        anchor = contract.billing_anchor_day or 1
        first_anchor = self._get_next_anchor_date(date_start, anchor)
        if not first_anchor:
            return
        offset = self._get_default_recurring_invoicing_offset(
            invoicing_type, rule_type
        )
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
