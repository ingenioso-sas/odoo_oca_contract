# Documentación técnica: `contract_invoice_notify`

## Propósito

Auto-valida facturas de contrato y las notifica por uno o varios canales.

El módulo base no conoce el estado de cuenta. Expone un driver y un hook para
que un glue agregue el enlace del estado de cuenta y use una plataforma de
canales.

## Dependencias

```python
depends = ["contract", "mail"]
```

## Modelos

### `contract.notification.channel`

Canal de notificación:

- `code` (único);
- `name`;
- `sequence`;
- `active`.

El canal es un dato. Los glues agregan canales nuevos sin modificar la
selección de contrato.

### `contract.notification.template`

Override por contrato:

- `contract_id`;
- `channel_id`;
- `purpose` (`invoice_notification`, `overdue_digest`);
- `template_id` (`mail.template`).
  - `invoice_notification` must use model `account.move`.
  - `overdue_digest` must use model `contract.contract`.
  - An invalid override is ignored and the default template is used.

### `contract.notification.driver`

Modelo abstracto con:

```python
def send(
    self,
    contract,
    record,
    purpose,
    channel_code,
    template=None,
    context=None,
): ...
```

La implementación base solo envía email. Un glue puede heredar y delegar en
su plataforma de canales.

## Contrato

Campos:

- `notification_channel_ids`: M2M a `contract.notification.channel`.
- `notification_template_ids`: overrides por canal y propósito.
- `overdue_*`: configuración del recordatorio.

Métodos:

- `_get_notification_channels()`.
- `_get_notification_template(record, purpose, channel_code)`.
- `_get_notification_context(...)`.
- `_get_notification_statement_url(record, channel_code)`.
- `_send_notification(record, purpose, channel_code)`.
- `_auto_validate_invoices(moves)`.
- `_send_overdue_digest(invoices=None)`.
- `action_resend_last_invoice_notification()`.

`_auto_validate_invoices` y `_send_overdue_digest` iteran los canales
configurados. Si Email y WhatsApp están seleccionados, se envían ambos.

## Enlace del estado de cuenta

`account.move._get_notification_statement_url(channel_code=None)` y
`contract.contract._get_notification_statement_url(channel_code=None)`
devuelven vacío en el módulo base.

El glue `contract_invoice_notify_customer_statement` los sobrescribe para
crear o reutilizar un token y devolver la URL. Las plantillas usan:

```xml
<t t-set="statement_url" t-value="object._get_notification_statement_url()" />
<t t-if="statement_url">...</t>
```

No se usan reemplazos de texto.

## Recordatorio de vencidas

- Un digest por contrato (el cron prefiltra facturas vencidas pendientes antes de evaluar contratos).
- Se envía por todos los canales configurados (si los canales asignados están archivados no vuelve silenciosamente a email).
- Solo se marca la factura si al menos un canal tuvo éxito.
- No consolida montos.
- Respeta `opt_out_overdue_reminder` en `partner_id`, `commercial_partner_id` e `invoice_partner_id`.

## Migración

`migrations/19.0.2.0.0/`:

- copia `send_notification_mode` y `whatsapp_template_id` antes de eliminar
  los campos;
- mapea `email` / `whatsapp` / `both` a `notification_channel_ids`;
- crea `contract.notification.template` para el antiguo
  `whatsapp_template_id`;
- migra también el modo del `contract.template`.

## Limitaciones

- Las plantillas de contrato (`contract.template`) ya no tienen
  `whatsapp_template_id`. Los overrides de plantilla se configuran por
  contrato en `notification_template_ids`. La migración conserva el modo de
  canales de la plantilla, no el override de plantilla.
- El driver base solo envía email; los demás canales requieren un glue.

## Pruebas

```bash
odoo -d <db> -u contract_invoice_notify --test-enable \
  --test-tags /contract_invoice_notify --stop-after-init
```
