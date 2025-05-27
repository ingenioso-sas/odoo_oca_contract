from odoo import api, fields, models

class SaleSubscriptionTemplate(models.Model):
    _inherit = "sale.subscription.template"
    _name = "sale.subscription.template"
    
    send_notification_mode = fields.Selection(
        default="whatsapp",
        string="Notificiation mode",
        selection=[
            ("whatsapp", "Whatsapp"),
            ("email", "Email"),
            ("both", "Whatsapp & Email"),          
        ],
    )