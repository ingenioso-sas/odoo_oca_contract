# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Pluggable WhatsApp driver.

No hard dependency on any WhatsApp provider. If
all_in_one_whatsapp_integration is installed it is used; otherwise the
message is logged + posted in chatter so cron never breaks. A future
payment_<psp>/whatsapp provider only needs to override _send_via_provider.
"""
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ContractWhatsappDriver(models.AbstractModel):
    _name = "contract.whatsapp.driver"
    _description = "Contract WhatsApp driver (pluggable)"

    @api.model
    def _send_via_provider(self, mobile, message, pdf_base64=None, filename=None):
        """Try real provider, return True if sent."""
        WhatsappMode = self.env.get("all.in.one.whatsapp.integration")
        # all_in_one_whatsapp_integration exposes a wizard model, not a
        # regular model; use its python helper if available.
        try:
            from odoo.addons.all_in_one_whatsapp_integration.wizard.whatsapp_mode_message import (  # noqa: E501
                WhatsappModeMessage,
            )
        except Exception:  # pragma: no cover - optional dependency
            return False
        try:
            helper = WhatsappModeMessage(self.env)
            if pdf_base64 and filename:
                helper.action_send_attachment_document_message(
                    mobile, filename, message, pdf_base64
                )
            else:
                helper.action_send_message(mobile, message)
            return True
        except Exception as exc:  # noqa: BLE001
            _logger.warning("WhatsApp provider failed for %s: %s", mobile, exc)
            return False

    @api.model
    def send_whatsapp(self, mobile, message, pdf_base64=None, filename=None):
        if not mobile:
            _logger.warning("WhatsApp skipped: no mobile number.")
            return False
        # Queue-friendly: caller decides with_delay; here just send/log.
        sent = self._send_via_provider(mobile, message, pdf_base64, filename)
        if not sent:
            _logger.info(
                "WhatsApp (logged, no provider) -> %s: %.200s", mobile, message
            )
        return sent
