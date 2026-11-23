# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_contract_invoices(self):
        if self.env.context.get("contract_allow_posted_invoice_delete"):
            return
        posted = self.filtered(
            lambda move: move.state == "posted"
            and move.invoice_line_ids.contract_line_id
        )
        if posted:
            raise UserError(
                self.env._(
                    "No puede eliminar una factura publicada vinculada a un "
                    "contrato. Cancele la factura o emita una nota crédito. "
                    "Para reemplazarla use 'Regenerar factura' en la línea "
                    "del contrato."
                )
            )

    def unlink(self):
        """Keep the contract line dates in sync after deleting draft invoices."""
        if not self.env.context.get("contract_skip_recalculate"):
            contract_lines = (
                self.filtered(lambda move: move.state != "posted")
                .invoice_line_ids.contract_line_id
            )
        else:
            contract_lines = self.env["contract.line"]
        result = super().unlink()
        for line in contract_lines:
            try:
                line._recalculate_invoice_dates()
            except Exception:  # noqa: BLE001 - never block the deletion
                _logger.warning(
                    "Could not recalculate dates for contract line %s after "
                    "deleting invoices.",
                    line.id,
                    exc_info=True,
                )
        return result
