# PSP futuro — interfaz lista (Fase 4)

No se crea `payment_*` hasta que entregues el PSP. El flujo ya está
desacoplado:

1. `contract.contract._get_pay_all_provider()` busca
   `payment.provider` publicado (`state enabled/test`, `is_published True`).
   Solo configura el provider en Contabilidad → Pagos → Proveedores.
2. `contract.contract._create_pay_all_link()` usa en orden:
   `payment.link` → `payment.transaction(invoice_ids=[...])` → fallback a
   `account.move.get_portal_url()` (Pay Now nativo por factura).
3. `contract_invoice_notify` usa `account.move.get_portal_url()` en email y
   WhatsApp, por lo que el botón de pago aparece solo cuando el PSP está
   activo. Sin PSP, el enlace muestra la factura sin botón de pago.

## Cuando entregues el PSP, crear `payment_<psp>` aparte:

- `depends: [payment]`
- `models/payment_provider.py`: hereda `payment.provider`, implementa
  `_get_supported_currencies()`, `_send_payment_request()`.
- `models/payment_transaction.py`: hereda `payment.transaction`, implementa
  `_get_tx_from_notification_data()`, `_process_notification_data()`.
- Icono + `payment_icon`, pruebas con credenciales test, webhook público.
- No tocar `contract*`. Solo instalar y publicar el provider; el portal y
  las notificaciones lo detectan solos.

Ejemplo base: OCA/payment `payment_demo` o cualquier `payment_stripe` de
Odoo EE como plantilla.
