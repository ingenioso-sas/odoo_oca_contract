# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Contract Invoice Discount",
    "summary": "Scheduled percentage discounts on contract invoices",
    "version": "19.0.1.0.0",
    "category": "Contract Management",
    "website": "https://github.com/OCA/contract",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["contract", "account"],
    "data": [
        "security/ir.model.access.csv",
        "security/contract_invoice_discount_security.xml",
        "views/contract_invoice_discount_views.xml",
        "views/contract_template_line_views.xml",
        "views/contract_line_views.xml",
        "views/account_move_views.xml",
        "report/report_invoice.xml",
    ],
    "installable": True,
}
