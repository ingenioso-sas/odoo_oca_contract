# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ContractNotificationDriver(models.AbstractModel):
    """Pluggable contract notification driver.

    The base implementation only sends email. Glue modules override ``send``
    to delegate to their channel platform, without modifying the contract
    module.
    """

    _name = "contract.notification.driver"
    _description = "Contract Notification Driver"

    def send(
        self,
        contract,
        record,
        purpose,
        channel_code,
        template=None,
        context=None,
    ):
        """Send one notification and return whether it succeeded."""
        if channel_code != "email":
            _logger.info(
                "No driver configured for contract notification channel %s.",
                channel_code,
            )
            return False
        template = template or contract._get_notification_template(
            record, purpose, channel_code
        )
        if not template:
            return False
        try:
            template.send_mail(
                record.id, force_send=False, raise_exception=False
            )
            return True
        except Exception as exc:  # noqa: BLE001 - keep cron robust
            _logger.warning(
                "Could not send contract notification %s: %s", record, exc
            )
            return False
