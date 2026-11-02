# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Contract Portal Payment",
    "summary": "Portal: pending invoices per contract + single pay-all link. "
    "No debt consolidation.",
    "version": "17.0.1.0.0",
    "category": "Contract Management",
    "website": "https://github.com/OCA/contract",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["contract", "portal", "account", "payment"],
    "data": [
        "views/contract_portal_templates.xml",
    ],
    "installable": True,
}
