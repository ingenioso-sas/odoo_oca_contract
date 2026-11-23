# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


class ContractRegenerateInvoice(models.TransientModel):
    _name = "contract.regenerate.invoice"
    _description = "Regenerate Contract Invoice"

    contract_line_id = fields.Many2one(
        comodel_name="contract.line",
        string="Línea del contrato",
        required=True,
        ondelete="cascade",
    )
    contract_id = fields.Many2one(
        related="contract_line_id.contract_id",
        string="Contrato",
        readonly=True,
    )
    period_start = fields.Date(string="Inicio del período", required=True)
    period_end = fields.Date(string="Fin del período", required=True)
    invoice_date = fields.Date(string="Fecha de factura", required=True)
    post_invoice = fields.Boolean(
        string="Publicar factura",
        default=False,
        help="Publica la factura inmediatamente después de crearla.",
    )
    company_id = fields.Many2one(
        related="contract_line_id.company_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="contract_line_id.currency_id",
        readonly=True,
    )
    product_id = fields.Many2one(
        related="contract_line_id.product_id",
        string="Producto",
        readonly=True,
    )
    quantity = fields.Float(
        related="contract_line_id.quantity",
        readonly=True,
    )
    price_unit = fields.Float(
        related="contract_line_id.price_unit",
        readonly=True,
    )
    existing_invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Facturas existentes",
        compute="_compute_existing_invoices",
    )
    existing_invoice_names = fields.Char(
        string="Referencias de facturas existentes",
        compute="_compute_existing_invoices",
    )

    # === COMPUTES / ONCHANGES === #

    @api.depends("contract_line_id", "period_start", "period_end")
    def _compute_existing_invoices(self):
        for wizard in self:
            invoices = self.env["account.move"]
            if (
                wizard.contract_line_id
                and wizard.period_start
                and wizard.period_end
            ):
                invoices = (
                    wizard.contract_line_id._get_invoice_lines_for_period(
                        wizard.period_start, wizard.period_end
                    ).mapped("move_id")
                )
            wizard.existing_invoice_ids = invoices
            wizard.existing_invoice_names = ", ".join(
                invoices.mapped("display_name")
            )

    @api.onchange("period_start")
    def _onchange_period_start(self):
        line = self.contract_line_id
        if not line or not self.period_start:
            return
        period_end = line.get_next_period_date_end(
            self.period_start,
            line.recurring_rule_type,
            line.recurring_interval,
            max_date_end=line.date_end,
        )
        self.period_end = period_end
        if period_end:
            self.invoice_date = line.get_next_invoice_date(
                self.period_start,
                line.recurring_invoicing_type,
                line.recurring_invoicing_offset,
                line.recurring_rule_type,
                line.recurring_interval,
                max_date_end=line.date_end,
            ) or period_end

    @api.onchange("period_end")
    def _onchange_period_end(self):
        line = self.contract_line_id
        if not line or not self.period_end:
            return
        if line.recurring_invoicing_type == "post-paid":
            self.invoice_date = self.period_end + relativedelta(
                days=line.recurring_invoicing_offset or 0
            )
        elif self.period_start:
            self.invoice_date = self.period_start + relativedelta(
                days=line.recurring_invoicing_offset or 0
            )

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for wizard in self:
            if (
                wizard.period_start
                and wizard.period_end
                and wizard.period_start > wizard.period_end
            ):
                raise ValidationError(
                    self.env._(
                        "La fecha de inicio del período no puede ser posterior "
                        "a la fecha de fin."
                    )
                )
            line = wizard.contract_line_id
            if line.date_start and wizard.period_start < line.date_start:
                raise ValidationError(
                    self.env._(
                        "El período no puede iniciar antes de la fecha de "
                        "inicio de la línea del contrato."
                    )
                )
            if line.date_end and wizard.period_end > line.date_end:
                raise ValidationError(
                    self.env._(
                        "El período no puede terminar después de la fecha "
                        "de fin de la línea del contrato."
                    )
                )

    # === ACTIONS === #

    def action_regenerate_invoice(self):
        self.ensure_one()
        self.contract_line_id._check_regenerate_access()
        if self.existing_invoice_ids:
            raise UserError(
                self.env._(
                    "Ya existe una factura para este período: %(invoices)s.",
                    invoices=self.existing_invoice_names,
                )
            )
        line = self.contract_line_id
        invoice_vals = line.contract_id._prepare_invoice(self.invoice_date)
        line_vals = line.with_context(
            contract_invoice_period_override={
                "period_start": self.period_start,
                "period_end": self.period_end,
                "invoice_date": self.invoice_date,
            }
        )._prepare_invoice_line()
        if not line_vals:
            raise UserError(
                self.env._("La línea del contrato no se puede facturar.")
            )
        invoice_vals["invoice_line_ids"] = [Command.create(line_vals)]
        invoice = self.env["account.move"].create(invoice_vals)
        if self.post_invoice:
            invoice.action_post()
        line._recalculate_invoice_dates()
        body = Markup(
            self.env._(
                "Factura %(invoice)s regenerada para el período "
                "%(period_start)s - %(period_end)s."
            )
        ) % {
            "invoice": invoice._get_html_link(),
            "period_start": self.period_start,
            "period_end": self.period_end,
        }
        line.contract_id.message_post(body=body)
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Factura regenerada"),
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
            "target": "current",
        }
