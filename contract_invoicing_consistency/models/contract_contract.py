# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    mixed_invoicing_warning = fields.Text(
        string="Invoicing Type Warning",
        compute="_compute_mixed_invoicing_warning",
    )

    @api.depends(
        "contract_line_ids.recurring_invoicing_type",
        "contract_line_ids.display_type",
        "contract_line_ids.is_recurring_note",
    )
    def _compute_mixed_invoicing_warning(self):
        for contract in self:
            lines = contract.contract_line_ids.filtered(
                lambda line: (not line.display_type or line.is_recurring_note)
                and not getattr(line, "is_canceled", False)
            )
            pre_paid = lines.filtered(
                lambda line: line.recurring_invoicing_type == "pre-paid"
            )
            post_paid = lines.filtered(
                lambda line: line.recurring_invoicing_type != "pre-paid"
            )
            if not pre_paid or not post_paid:
                contract.mixed_invoicing_warning = False
                continue
            empty_type = lines.filtered(
                lambda line: not line.recurring_invoicing_type
            )
            warning = _(
                "Este contrato mezcla líneas Prepago y Pospago. "
                "Prepago: %(pre)s. Pospago: %(post)s. "
                "Se facturarán en fechas distintas; si desea una sola "
                "factura por período, unifique el tipo de facturación.",
                pre=self._mixed_invoicing_line_names(pre_paid),
                post=self._mixed_invoicing_line_names(post_paid),
            )
            if empty_type:
                warning = " ".join(
                    [
                        warning,
                        _(
                            "Líneas sin tipo configurado (se comportan como "
                            "Pospago): %(lines)s.",
                            lines=self._mixed_invoicing_line_names(empty_type),
                        ),
                    ]
                )
            contract.mixed_invoicing_warning = warning

    @api.model
    def _mixed_invoicing_line_names(self, lines):
        return ", ".join(line.name or line.display_name for line in lines) or _(
            "ninguna"
        )
