# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    pending_invoice_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_pending_invoices",
        string="Pending invoices",
    )
    pending_invoices_count = fields.Integer(
        compute="_compute_pending_invoices",
        string="Pending count",
    )
    pending_invoices_total = fields.Monetary(
        compute="_compute_pending_invoices",
        currency_field="currency_id",
        string="Pending total",
    )

    @api.depends()
    def _compute_pending_invoices(self):
        for contract in self:
            pending = contract._get_pending_invoices()
            contract.pending_invoice_ids = [(6, 0, pending.ids)]
            contract.pending_invoices_count = len(pending)
            contract.pending_invoices_total = sum(pending.mapped("amount_residual"))

    def _get_pending_invoices(self):
        """Posted customer invoices, not fully paid. Never merges amounts."""
        self.ensure_one()
        return self._get_related_invoices().filtered(
            lambda m: m.move_type == "out_invoice"
            and m.state == "posted"
            and m.payment_state not in ("paid", "in_payment")
        ).sorted("invoice_date_due")

    def _get_pay_all_provider(self):
        Provider = self.env.get("payment.provider")
        if not Provider:
            return self.env["payment.provider"].browse()
        return Provider.search(
            [("state", "in", ("enabled", "test")), ("is_published", "=", True)],
            limit=1,
        )

    def _create_pay_all_link(self):
        """Return a payment URL covering all pending invoices.

        Prefers payment.link (multi-invoice when supported), falls back to
        a single payment.transaction, and finally to the first invoice
        portal URL so portal never breaks without PSP.
        """
        self.ensure_one()
        pending = self._get_pending_invoices()
        if not pending:
            return ""
        if pending and len(pending.currency_id) > 1:
            # Group by currency is out of scope: pay per currency batch.
            pending = pending.filtered(
                lambda m: m.currency_id == self.currency_id
            ) or pending
        amount = sum(pending.mapped("amount_residual"))
        if amount <= 0:
            return pending[0]._get_payment_portal_url() if hasattr(
                pending[0], "_get_payment_portal_url"
            ) else pending[0].get_portal_url()
        provider = self._get_pay_all_provider()
        # 1) payment.link when available
        PaymentLink = self.env.get("payment.link")
        if PaymentLink is not None:
            try:
                vals = {
                    "amount": amount,
                    "currency_id": pending[0].currency_id.id,
                    "partner_id": self.partner_id.id,
                    "description": f"Contrato {self.name}: {', '.join(pending.mapped('name'))}",
                }
                link = PaymentLink.create(vals)
                # Link invoices when the field exists (Odoo 17 payment.link
                # supports related documents depending on version).
                if "invoice_ids" in link._fields:
                    link.write({"invoice_ids": [(6, 0, pending.ids)]})
                url = link._generate_link() if hasattr(link, "_generate_link") else ""
                if url:
                    return url
                if getattr(link, "link", False):
                    return link.link
            except Exception:  # noqa: BLE001 - fallback below
                pass
        # 2) payment.transaction covering several invoices
        try:
            Tx = self.env["payment.transaction"]
            tx_vals = {
                "amount": amount,
                "currency_id": pending[0].currency_id.id,
                "partner_id": self.partner_id.id,
                "reference": f"{self.name}/{','.join(pending.mapped('name'))}"[:200],
            }
            if provider:
                tx_vals["provider_id"] = provider.id
            if "invoice_ids" in Tx._fields:
                tx_vals["invoice_ids"] = [(6, 0, pending.ids)]
            tx = Tx.create(tx_vals)
            if hasattr(tx, "get_portal_url"):
                try:
                    return tx.get_portal_url()
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass
        # 3) Fallback: first invoice portal (native Pay Now per invoice)
        try:
            return pending[0].get_portal_url()
        except Exception:  # noqa: BLE001
            return ""
