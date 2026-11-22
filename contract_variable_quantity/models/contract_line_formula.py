# Copyright 2016 Tecnativa - Pedro M. Baeza
# Copyright 2018 Tecnativa - Carlos Dauden
# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, exceptions, fields, models
from odoo.tools.safe_eval import safe_eval


class _DryRunRollback(Exception):
    """Sentinel used to roll back any side effects of formula validation."""


class ContractLineFormula(models.Model):
    _name = "contract.line.qty.formula"
    _description = "Contract Line Formula"

    name = fields.Char(required=True, translate=True)
    code = fields.Text(required=True, default="result = 0")

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.is_system():
            raise exceptions.AccessError(
                self.env._("Only system administrators can create quantity formulas.")
            )
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.is_system():
            raise exceptions.AccessError(
                self.env._("Only system administrators can modify quantity formulas.")
            )
        return super().write(vals)

    def unlink(self):
        if not self.env.is_system():
            raise exceptions.AccessError(
                self.env._("Only system administrators can delete quantity formulas.")
            )
        return super().unlink()

    @api.constrains("code")
    def _check_code(self):
        today = fields.Date.context_today(self)
        for rec in self:
            eval_context = {
                "env": rec.env,
                "context": rec.env.context,
                "user": rec.env.user,
                "line": rec.env["contract.line"],
                "contract": rec.env["contract.contract"],
                "quantity": 0,
                "period_first_date": today,
                "period_last_date": today,
                "invoice_date": today,
            }
            try:
                with rec.env.cr.savepoint(flush=False):
                    safe_eval((rec.code or "").strip(), eval_context, mode="exec")
                    raise _DryRunRollback()
            except _DryRunRollback:
                pass
            except Exception as e:
                raise exceptions.ValidationError(
                    self.env._("Error evaluating code.\nDetails: %s", e)
                ) from e
            if "result" not in eval_context:
                raise exceptions.ValidationError(
                    self.env._("No valid result returned.")
                )
            result = eval_context["result"]
            if isinstance(result, bool) or not isinstance(result, (int, float)):
                raise exceptions.ValidationError(
                    self.env._("Formula 'result' must be a numeric value (int or float).")
                )
