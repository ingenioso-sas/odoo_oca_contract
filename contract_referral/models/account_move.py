# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        result = super()._post(soft=soft)
        try:
            with self.env.cr.savepoint():
                self.sudo()._create_referral_commissions()
                self.sudo()._create_referral_commission_adjustments()
        except Exception:  # noqa: BLE001 - never block invoice posting
            _logger.exception("Could not create referral commissions")
        return result

    def _create_referral_commissions(self):
        commission_model = self.env["contract.referral.commission"]
        for invoice in self.filtered(
            lambda move: move.move_type == "out_invoice"
            and move.state == "posted"
        ):
            contracts = invoice.invoice_line_ids.contract_line_id.contract_id
            for contract in contracts:
                referrals = self.env["contract.referral"].search(
                    [
                        ("referred_contract_id", "=", contract.id),
                        ("state", "=", "active"),
                    ]
                )
                for referral in referrals:
                    if not referral._can_create_commission(invoice):
                        continue
                    existing = commission_model.search(
                        [
                            ("referral_id", "=", referral.id),
                            ("invoice_id", "=", invoice.id),
                        ],
                        limit=1,
                    )
                    if existing:
                        continue
                    commission_model.create(
                        {
                            "referral_id": referral.id,
                            "invoice_id": invoice.id,
                            "base_amount": referral._get_commission_base_amount(
                                invoice
                            ),
                            "commission_percent": (
                                referral.referrer_commission_percent
                            ),
                        }
                    )

    def _create_referral_commission_adjustments(self):
        """Reverse commissions when a referred invoice is refunded."""
        commission_model = self.env["contract.referral.commission"]
        for refund in self.filtered(
            lambda move: move.move_type == "out_refund"
            and move.state == "posted"
        ):
            contracts = refund.invoice_line_ids.contract_line_id.contract_id
            for contract in contracts:
                referral = self.env["contract.referral"].search(
                    [("referred_contract_id", "=", contract.id)],
                    limit=1,
                )
                if (
                    not referral
                    or referral.referrer_commission_percent <= 0
                ):
                    continue
                existing = commission_model.search(
                    [
                        ("referral_id", "=", referral.id),
                        ("invoice_id", "=", refund.id),
                    ],
                    limit=1,
                )
                if existing:
                    continue
                base_amount = referral._get_commission_base_amount(refund)
                commission_model.create(
                    {
                        "referral_id": referral.id,
                        "invoice_id": refund.id,
                        "base_amount": -base_amount,
                        "commission_percent": (
                            referral.referrer_commission_percent
                        ),
                        "is_adjustment": True,
                    }
                )
