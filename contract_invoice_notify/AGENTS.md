# AGENTS.md — `contract_invoice_notify`

## Reglas

- No agregar lógica de canales al contrato: usar
  `contract.notification.channel` y el driver.
- No volver a `send_notification_mode` ni a valores combinados `both`.
- Para enviar por Email y WhatsApp, seleccionar ambos canales.
- No agregar lógica del estado de cuenta al módulo base.
- El enlace del estado de cuenta se expone con
  `_get_notification_statement_url()`, no con reemplazos de texto.
- Los glues implementan `contract.notification.driver`.
- El recordatorio de vencidas usa los mismos canales que la notificación.
- No consolidar deuda: solo listar facturas vencidas.
- Respetar `opt_out_overdue_reminder`.
- Mantener migraciones directas y subir la versión al modificar campos o
  datos.

## Archivos clave

- `models/contract_contract.py`: canales, plantillas y envío.
- `models/contract_notification_channel.py`: canales.
- `models/contract_notification_template.py`: overrides.
- `models/contract_notification_driver.py`: driver base.
- `data/contract_notification_channel_data.xml`: canales email/whatsapp.
- `views/contract_views.xml`: configuración en el contrato.
