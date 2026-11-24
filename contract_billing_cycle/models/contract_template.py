# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ContractTemplate(models.Model):
    _inherit = "contract.template"

    billing_anchor_day = fields.Integer(
        string="Día de facturación",
        default=1,
        required=True,
        help="Día del mes en que se emite la factura pospaga. Por defecto, "
        "el día 1. Si el mes no tiene ese día, se usa el último día del mes.",
    )
    free_trial_periods = fields.Integer(
        string="Períodos completos gratis",
        default=0,
        help="Cantidad de períodos completos que se facturan con descuento "
        "de prueba. 0 = sin prueba gratuita. El período inicial parcial se "
        "cobra prorrateado.",
    )
    free_trial_discount = fields.Float(
        string="Descuento de prueba (%)",
        digits="Discount",
        default=100.0,
        help="Porcentaje de descuento aplicado a los períodos completos de "
        "prueba. Normalmente 100.",
    )
    skip_zero_invoices = fields.Boolean(
        string="Omitir facturas en cero",
        default=False,
        help="Si se marca, no se crea la factura cuando su total es cero, "
        "por ejemplo durante la prueba gratuita. Las fechas del contrato "
        "avanzan igualmente.",
    )

    @api.constrains("billing_anchor_day")
    def _check_billing_anchor_day(self):
        for record in self:
            if record.billing_anchor_day < 1 or record.billing_anchor_day > 31:
                raise ValidationError(
                    self.env._("El día de facturación debe estar entre 1 y 31.")
                )

    @api.constrains("free_trial_periods")
    def _check_free_trial_periods(self):
        for record in self:
            if record.free_trial_periods < 0:
                raise ValidationError(
                    self.env._("Los períodos de prueba no pueden ser negativos.")
                )

    @api.constrains("free_trial_discount")
    def _check_free_trial_discount(self):
        for record in self:
            if record.free_trial_discount < 0 or record.free_trial_discount > 100:
                raise ValidationError(
                    self.env._(
                        "El descuento de prueba debe estar entre 0 y 100."
                    )
                )
