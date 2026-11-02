# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Contract Invoice Notify",
    "summary": "Auto-validate + notify contract invoices by email/WhatsApp "
    "with payment link and overdue summary. No debt consolidation.",
    "version": "17.0.1.0.0",
    "category": "Contract Management",
    "website": "https://github.com/OCA/contract",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["contract", "mail"],
    "data": [
        "data/mail_template.xml",
        "data/ir_cron.xml",
        "views/contract_views.xml",
        "views/contract_template_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
}
