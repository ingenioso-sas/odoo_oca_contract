# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Contract Invoice Regenerate",
    "summary": "Recalculate contract dates and regenerate deleted contract invoices",
    "version": "19.0.1.0.1",
    "category": "Contract Management",
    "license": "AGPL-3",
    "author": "PayOnline Ing",
    "website": "https://www.odoo.com",
    "depends": [
        "contract_invoice_period",
        "account",
    ],
    "data": [
        "security/security.xml",
        "views/contract_line_views.xml",
        "wizards/regenerate_contract_invoice_views.xml",
    ],
    "installable": True,
    "application": False,
}
