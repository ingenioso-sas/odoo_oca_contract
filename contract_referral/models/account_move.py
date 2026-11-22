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
                        ("company_id", "=", invoice.company_id.id),
                        ("state", "=", "active"),
                    ]
                )
                for referral in referrals:
                    if not referral._can_create_commission(invoice):
                        continue
                    base_amount = referral._get_commission_base_amount(invoice)
                    if base_amount <= 0:
                        continue
                    existing = commission_model.search(
                        [
                            ("referral_id", "=", referral.id),
                            ("invoice_id", "=", invoice.id),
                        ],
                        limit=1,
                    )
                    if existing:
                        if existing.state in ("draft", "cancelled"):
                            existing.write(
                                {
                                    "base_amount": base_amount,
                                    "commission_percent": (
                                        referral.referrer_commission_percent
                                    ),
                                }
                            )
                        continue
                    commission_model.create(
                        {
                            "referral_id": referral.id,
                            "invoice_id": invoice.id,
                            "base_amount": base_amount,
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
            if refund.reversed_entry_id:
                orig_commissions = commission_model.search(
                    [
                        ("invoice_id", "=", refund.reversed_entry_id.id),
                        ("is_adjustment", "=", False),
                        ("state", "!=", "cancelled"),
                    ]
                )
                for orig in orig_commissions:
                    referral = orig.referral_id
                    if commission_model.search_count(
                        [
                            ("referral_id", "=", referral.id),
                            ("invoice_id", "=", refund.id),
                        ]
                    ):
                        continue
                    refund_base = referral._get_commission_base_amount(refund)
                    capped_base = min(abs(refund_base), abs(orig.base_amount))
                    if capped_base <= 0 or orig.commission_percent <= 0:
                        continue
                    commission_model.create(
                        {
                            "referral_id": referral.id,
                            "invoice_id": refund.id,
                            "base_amount": -capped_base,
                            "commission_percent": orig.commission_percent,
                            "is_adjustment": True,
                        }
                    )
                continue

            contracts = refund.invoice_line_ids.contract_line_id.contract_id
            for contract in contracts:
                referrals = self.env["contract.referral"].search(
                    [
                        ("referred_contract_id", "=", contract.id),
                        ("company_id", "=", refund.company_id.id),
                    ],
                    order="id desc",
                )
                for referral in referrals:
                    if commission_model.search_count(
                        [
                            ("referral_id", "=", referral.id),
                            ("invoice_id", "=", refund.id),
                        ]
                    ):
                        continue
                    prior = commission_model.search(
                        [
                            ("referral_id", "=", referral.id),
                            ("is_adjustment", "=", False),
                            ("state", "!=", "cancelled"),
                        ]
                    )
                    if not prior:
                        continue
                    prior_adjustments = commission_model.search(
                        [
                            ("referral_id", "=", referral.id),
                            ("is_adjustment", "=", True),
                            ("state", "!=", "cancelled"),
                        ]
                    )
                    net_commissioned = sum(prior.mapped("base_amount")) + sum(
                        prior_adjustments.mapped("base_amount")
                    )
                    if net_commissioned <= 0:
                        continue
                    refund_base = referral._get_commission_base_amount(refund)
                    capped_base = min(abs(refund_base), net_commissioned)
                    percent = prior[0].commission_percent
                    if capped_base <= 0 or percent <= 0:
                        continue
                    commission_model.create(
                        {
                            "referral_id": referral.id,
                            "invoice_id": refund.id,
                            "base_amount": -capped_base,
                            "commission_percent": percent,
                            "is_adjustment": True,
                        }
                    )
                    break
