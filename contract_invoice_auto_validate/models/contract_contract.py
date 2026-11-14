# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Legacy bridge: unified auto-validation now lives in contract.contract.

This module is kept for backward compatibility only. New installs should
use contract.invoicing_mode (draft/validate/validate_send) per contract or
template instead of the global company flag.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ContractContract(models.Model):
    _inherit = "contract.contract"

    def _recurring_create_invoice(self, date_ref=False):
        moves = super()._recurring_create_invoice(date_ref=date_ref)
        # Legacy fallback: only act on contracts still in draft mode whose
        # company keeps the old global flag. Contracts already handled by
        # _auto_validate_invoices (validate/validate_send) are skipped to
        # avoid a double action_post().
        legacy_moves = self.env["account.move"]
        for contract in self.filtered(lambda c: c.invoicing_mode == "draft"):
            contract_moves = moves & contract._get_related_invoices()
            draft_moves = contract_moves.filtered(
                lambda m: m.state == "draft" and m.invoice_line_ids
            )
            if draft_moves and contract.company_id.auto_post_contract_invoice:
                legacy_moves |= draft_moves
        if legacy_moves:
            _logger.warning(
                "contract_invoice_auto_validate legacy fallback posting %s. "
                "Migrate company flag to contract.invoicing_mode instead.",
                legacy_moves.ids,
            )
            try:
                legacy_moves.action_post()
            except Exception as exc:  # noqa: BLE001 - keep cron robust
                _logger.warning("Legacy auto-post failed: %s", exc)
        return moves
