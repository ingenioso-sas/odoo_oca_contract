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
    free_trial_duration = fields.Integer(
        string="Duración de la prueba",
        default=0,
        help="Duración de la prueba gratuita desde la fecha de inicio del "
        "servicio. 0 = sin prueba gratuita. Se prorratea entre las facturas "
        "que cubran ese rango.",
    )
    free_trial_unit = fields.Selection(
        selection=[
            ("days", "Días"),
            ("months", "Meses"),
        ],
        string="Unidad de la prueba",
        default="months",
        required=True,
        help="Unidad de la duración de la prueba gratuita.",
    )
    free_trial_discount = fields.Float(
        string="Descuento de prueba (%)",
        digits="Discount",
        default=100.0,
        help="Porcentaje de descuento aplicado durante la prueba gratuita. "
        "Normalmente 100.",
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

    @api.constrains("free_trial_duration")
    def _check_free_trial_duration(self):
        for record in self:
            if record.free_trial_duration < 0:
                raise ValidationError(
                    self.env._("La duración de la prueba no puede ser negativa.")
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
