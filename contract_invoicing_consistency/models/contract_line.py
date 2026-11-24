# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ContractLine(models.Model):
    _inherit = "contract.line"

    @api.constrains(
        "recurring_next_date",
        "next_period_date_start",
        "recurring_invoicing_type",
        "recurring_invoicing_offset",
        "recurring_rule_type",
        "recurring_interval",
        "date_start",
        "date_end",
        "last_date_invoiced",
    )
    def _check_next_invoice_date_matches_period(self):
        """Reject invoice dates that leave the next period without days.

        ``contract_recurring_mixin`` back-calculates the next period end from
        ``recurring_next_date``. For example, a post-paid line with invoice
        date 1 November would produce the period 1 November - 31 October.
        This constraint makes that state impossible and explains the expected
        date instead.
        """
        for line in self:
            if line.display_type and not line.is_recurring_note:
                continue
            if getattr(line, "is_canceled", False):
                continue
            period_start = line.next_period_date_start
            period_end = line.next_period_date_end
            if not period_start or not period_end:
                continue
            if period_end >= period_start:
                continue
            effective_type = line.recurring_invoicing_type or "post-paid"
            type_label = dict(
                line._fields["recurring_invoicing_type"].selection
            ).get(effective_type) or effective_type
            if not line.recurring_invoicing_type:
                type_label = _(
                    "%(label)s (sin tipo configurado)", label=type_label
                )
            suggested = line.get_next_invoice_date(
                period_start,
                effective_type,
                line.recurring_invoicing_offset,
                line.recurring_rule_type,
                line.recurring_interval,
                max_date_end=line.date_end,
            )
            raise ValidationError(
                _(
                    "La próxima fecha de factura %(next)s no es coherente "
                    "para la línea '%(line)s'. El período %(start)s - "
                    "%(end)s con tipo %(type)s requiere una fecha de "
                    "factura %(suggested)s. Ajuste la fecha o el tipo de "
                    "facturación.",
                    next=(
                        fields.Date.to_string(line.recurring_next_date)
                        if line.recurring_next_date
                        else _("vacía")
                    ),
                    line=line.name or line.display_name,
                    start=fields.Date.to_string(period_start),
                    end=fields.Date.to_string(period_end),
                    type=type_label,
                    suggested=(
                        fields.Date.to_string(suggested)
                        if suggested
                        else _("posterior al fin del período")
                    ),
                )
            )
