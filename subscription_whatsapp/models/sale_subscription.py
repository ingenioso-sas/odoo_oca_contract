# Copyright 2023 Domatix - Carlos Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from datetime import date, datetime
import base64
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
import html2text
#import html2plaintext
from odoo.exceptions import AccessError
from odoo.addons.all_in_one_whatsapp_integration.wizard.whatsapp_mode_message import WhatsappModeMessage

logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"
    
    def send_Invoice(self,invoice):
        if not invoice:            
            return 
        
        send_mode = self.template_id.send_notification_mode
        #invoice = self.invoice_ids.sorted('id', reverse=True)[:1]
        if send_mode in ['email', 'both']:
            # invoice.with_context(force_send=True)._generate_pdf_and_send_invoice(mail_template)
            super().send_Invoice(invoice)
                         
        if send_mode in ['whatsapp', 'both']:
            whatsapp_message_mode = WhatsappModeMessage(self.env)

            
            mail_template = self.template_id.invoice_mail_template_id
            mail_template_values = mail_template.with_context(
                tpl_partners_only=True                
            )._generate_template([invoice.id], render_fields=["body_html"])
            html_message = mail_template_values.get(invoice.id, {}).get("body_html", "")
            plain_text_message =  html2text.html2text(html_message)            
            contenido_binario = base64.b64decode(invoice.invoice_pdf_report_file, validate=True)
            base64_limpio = base64.b64encode(contenido_binario).decode('utf-8')
            whatsapp_message_mode.action_send_attachment_document_message(invoice.partner_id.mobile,f"{invoice.name}.pdf", plain_text_message, base64_limpio)            
