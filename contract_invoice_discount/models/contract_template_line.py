# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ContractTemplateLine(models.Model):
    _inherit = "contract.template.line"

    promo_name = fields.Char(
        string="Promotion Name",
        default="Promotion",
        help="Name shown on the invoice when the promotional discount applies.",
    )
    promo_discount = fields.Float(
        string="Promotion Discount (%)",
        digits="Discount",
        default=0.0,
        help="Default promotional discount copied to new contracts created "
        "from this template line.",
    )
    promo_duration_months = fields.Integer(
        string="Promotion Duration (months)",
        default=0,
        help="Number of months the promotion lasts from the contract line "
        "start. 0 = no date limit.",
    )
    promo_max_invoices = fields.Integer(
        string="Promotion Max Invoices",
        default=0,
        help="Maximum number of invoices with the promotion. 0 = unlimited.",
    )

    @api.constrains(
        "promo_discount",
        "promo_duration_months",
        "promo_max_invoices",
    )
    def _check_promo(self):
        for line in self:
            if line.promo_discount < 0 or line.promo_discount > 100:
                raise ValidationError(
                    self.env._("Promotion discount must be between 0 and 100.")
                )
            if line.promo_duration_months < 0:
                raise ValidationError(
                    self.env._("Promotion duration cannot be negative.")
                )
            if line.promo_max_invoices < 0:
                raise ValidationError(
                    self.env._("Promotion max invoices cannot be negative.")
                )
            if (
                line.promo_discount
                and not line.promo_duration_months
                and not line.promo_max_invoices
            ):
                raise ValidationError(
                    self.env._(
                        "Define a promotion duration or a maximum number of "
                        "invoices."
                    )
                )
