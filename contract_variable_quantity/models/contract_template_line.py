# Copyright 2016 Tecnativa - Pedro M. Baeza
# Copyright 2018 Tecnativa - Carlos Dauden
# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ContractTemplateLine(models.Model):
    _inherit = "contract.template.line"

    qty_type = fields.Selection(
        selection=[("fixed", "Fixed quantity"), ("variable", "Variable quantity")],
        required=True,
        default="fixed",
        string="Qty. type",
    )
    qty_formula_id = fields.Many2one(
        comodel_name="contract.line.qty.formula",
        string="Qty. formula",
        ondelete="restrict",
    )

    @api.constrains("qty_type", "qty_formula_id", "display_type")
    def _check_qty_formula_required(self):
        for line in self:
            if (
                not line.display_type
                and line.qty_type == "variable"
                and not line.qty_formula_id
            ):
                raise ValidationError(
                    self.env._(
                        "A quantity formula is required when quantity type is "
                        "set to Variable quantity."
                    )
                )
