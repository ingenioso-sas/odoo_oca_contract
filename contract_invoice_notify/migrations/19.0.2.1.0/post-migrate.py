# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os

from lxml import etree

from odoo import SUPERUSER_ID, api


def _refresh_templates(env, module, filename, xmlids):
    """Rewrite the noupdate mail templates from their XML definition.

    The templates are declared with ``noupdate="1"`` so user changes are
    preserved on upgrade. When the module itself adds new content to the
    template (for example the customer statement link), upgrades would keep
    the old body forever. This migration refreshes only the body and subject
    of the templates owned by the module.
    """
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", filename
    )
    document = etree.parse(path)
    for record in document.getroot().xpath("//record[@model='mail.template']"):
        xmlid = record.get("id")
        if xmlid not in xmlids:
            continue
        template = env.ref(
            "%s.%s" % (module, xmlid), raise_if_not_found=False
        )
        if not template:
            continue
        values = {}
        for field in record.iterchildren("field"):
            name = field.get("name")
            if name not in ("body_html", "subject"):
                continue
            if field.get("type") == "html":
                values[name] = "".join(
                    etree.tostring(child, method="html", encoding="unicode")
                    for child in field
                )
            else:
                values[name] = field.text or ""
        if values:
            template.write(values)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    _refresh_templates(
        env,
        "contract_invoice_notify",
        "mail_template.xml",
        {
            "email_template_contract_invoice_notify",
            "email_template_contract_overdue_digest",
            "whatsapp_template_contract_invoice",
        },
    )
