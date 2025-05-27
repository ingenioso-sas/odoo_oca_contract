# Copyright 2023 Domatix - Carlos Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "subscription_whatsapp",
    "summary": "Generate recurring whatsapp message for invoices recurring.",
    "version": "17.0.1.0.0",
    "development_status": "Beta",
    "category": "Extra Tools",
    "website": "https://www.ingenioso.co",
    "autor": "IngeniosoSAS",
    "company": "IngeniosoSAS",
    "maintainer": "IngeniosoSAS",
    "license": "AGPL-3",
    "depends": ["all_in_one_whatsapp_integration", "subscription_oca"],
    "data": [
        "views/sale_subscription_template_views.xml",
        #"data/ir_cron.xml",
        #"data/sale_subscription_data.xml",
        #"wizard/close_subscription_wizard.xml",
        #"security/ir.model.access.csv",
    ],
    "installable": True,
    "application": True,
}
