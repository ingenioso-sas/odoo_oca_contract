# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api
from odoo.fields import Command

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Map the old email/whatsapp/both mode to channel records."""
    if not version:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'contract_invoice_notify_legacy'
        """
    )
    if not cr.fetchone():
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Channel = env["contract.notification.channel"].sudo()
    Contract = env["contract.contract"].sudo()
    Override = env["contract.notification.template"].sudo()
    MailTemplate = env["mail.template"].sudo()
    email = Channel.search([("code", "=", "email")], limit=1)
    whatsapp = Channel.search([("code", "=", "whatsapp")], limit=1)

    cr.execute(
        """
        SELECT id, send_notification_mode, whatsapp_template_id
          FROM contract_invoice_notify_legacy
        """
    )
    for contract_id, mode, wa_template_id in cr.fetchall():
        contract = Contract.browse(contract_id).exists()
        if not contract:
            continue
        mode = mode or "email"
        channel_ids = []
        if mode in ("email", "both") and email:
            channel_ids.append(email.id)
        if mode in ("whatsapp", "both") and whatsapp:
            channel_ids.append(whatsapp.id)
        if not channel_ids and email:
            channel_ids = [email.id]
        contract.write(
            {"notification_channel_ids": [Command.set(channel_ids)]}
        )
        mail_template = (
            MailTemplate.browse(wa_template_id).exists()
            if wa_template_id
            else MailTemplate
        )
        if mail_template and whatsapp:
            existing = Override.search(
                [
                    ("contract_id", "=", contract.id),
                    ("channel_id", "=", whatsapp.id),
                    ("purpose", "=", "invoice_notification"),
                ],
                limit=1,
            )
            if not existing:
                Override.create(
                    {
                        "contract_id": contract.id,
                        "channel_id": whatsapp.id,
                        "purpose": "invoice_notification",
                        "template_id": mail_template.id,
                    }
                )

    cr.execute("DROP TABLE IF EXISTS contract_invoice_notify_legacy")

    # Contract templates: migrate the old notification mode to the M2M.
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'contract_invoice_notify_template_legacy'
        """
    )
    if cr.fetchone():
        ContractTemplate = env["contract.template"].sudo()
        cr.execute(
            """
            SELECT id, send_notification_mode
              FROM contract_invoice_notify_template_legacy
            """
        )
        for template_id, mode in cr.fetchall():
            template = ContractTemplate.browse(template_id).exists()
            if not template:
                continue
            mode = mode or "email"
            channel_ids = []
            if mode in ("email", "both") and email:
                channel_ids.append(email.id)
            if mode in ("whatsapp", "both") and whatsapp:
                channel_ids.append(whatsapp.id)
            if not channel_ids and email:
                channel_ids = [email.id]
            template.write(
                {"notification_channel_ids": [Command.set(channel_ids)]}
            )
        cr.execute(
            "DROP TABLE IF EXISTS contract_invoice_notify_template_legacy"
        )
