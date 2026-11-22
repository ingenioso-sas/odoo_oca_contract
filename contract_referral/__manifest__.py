# Copyright 2026 PayOnline Ing
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Contract Referral",
    "summary": "Referral discounts for referred customers and commissions "
    "for referrers",
    "version": "19.0.1.1.0",
    "category": "Contract Management",
    "website": "https://github.com/OCA/contract",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["contract_invoice_discount", "account"],
    "data": [
        "security/ir.model.access.csv",
        "security/contract_referral_security.xml",
        "data/ir_cron.xml",
        "views/contract_referral_views.xml",
        "views/contract_referral_commission_views.xml",
        "views/contract_line_views.xml",
    ],
    "installable": True,
}
