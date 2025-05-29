# Copyright 2023 Domatix - Carlos Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
import base64
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
import html2text
#import html2plaintext
from odoo.addons.all_in_one_whatsapp_integration.wizard.whatsapp_mode_message import WhatsappModeMessage
from odoo.exceptions import UserError

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
            mobile = invoice.partner_id.mobile
            if mobile:
                whatsapp_message_mode = WhatsappModeMessage(self.env)
                mail_template = self.template_id.invoice_mail_template_id
                mail_template_values = mail_template.with_context(
                    tpl_partners_only=True
                )._generate_template([invoice.id], render_fields=["body_html"])
                html_message = mail_template_values.get(invoice.id, {}).get("body_html", "")
                plain_text_message =  html2text.html2text(html_message)

                # Generar PDF de forma segura desde el reporte
                contenido_binario, _ = self.env["ir.actions.report"]._render_qweb_pdf(
                "account.account_invoices", invoice.id
                )
                # Trasnformarlo a base64  para enviarlo via whatsapp
                base64_limpio = base64.b64encode(contenido_binario).decode('utf-8')
                whatsapp_message_mode.action_send_attachment_document_message(invoice.partner_id.mobile,f"{invoice.name}.pdf", plain_text_message, base64_limpio)            
                # Mensaje del boot 
                self.message_post(
                    body=html_message,
                    subject="Factura enviada por WhatsApp",
                    message_type="comment"
                )
            else:
                raise UserError(("El cliente no tiene número de teléfono para enviar el mensaje por WhatsApp."))
