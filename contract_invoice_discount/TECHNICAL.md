# Documentación técnica: `contract_invoice_discount`

## Propósito

Aplicar descuentos porcentuales temporales a las facturas de contrato sin
duplicar líneas y conservando el histórico en la factura.

## Modelo `contract.invoice.discount`

Campos principales:

- `contract_line_id`;
- `name`;
- `discount`;
- `start_mode` (`fixed_date` / `contract_start` / `next_invoice`);
- `date_start` / `date_end`;
- `max_invoices`;
- `source`;
- `pause_policy` (`service` / `calendar`);
- `active`;
- `applied_invoice_count` y `remaining_invoices`.

El estado se calcula como programado, activo, vencido, agotado o inactivo.

## Modo de inicio

`start_mode` define cómo se obtiene `date_start` al crear la regla:

- `fixed_date`: usa la fecha ingresada manualmente.
- `contract_start`: usa `contract_line_id.date_start`.
- `next_invoice`: usa el primer día del próximo período a facturar,
  calculado con `_get_period_to_invoice()`.

La fecha resuelta se guarda en `date_start`. No se recalcula en cada factura
para no interferir con `pause_policy`. Si la línea del contrato cambia, se
puede volver a aplicar con `action_recompute_date_start`.

Las reglas creadas desde una plantilla usan `contract_start`. Las reglas de
referido y las copias por sucesión conservan su fecha explícita con
`fixed_date`.

## Cálculo

`contract.line._get_invoice_discount(period_start, period_end)`:

1. Toma el descuento base de la línea.
2. Recorre las reglas activas.
3. Descarta las que no cumplen condiciones o no se cruzan con el período.
4. Calcula el porcentaje prorrateado por días.
5. Devuelve el mayor descuento y la regla ganadora.

`_prepare_invoice_line()` escribe el descuento en el campo estándar
`discount` y guarda en la línea de factura:

- `contract_discount_id`;
- `contract_discount_name`;
- `contract_discount_percent`;
- `contract_discount_until`;
- `contract_discount_source`.

## Plantillas

La línea de plantilla tiene campos de promoción. Al crear un contrato desde
la plantilla, `_convert_contract_lines()` crea la regla con fechas relativas
al inicio de la línea del contrato.

## Compatibilidad

- Prepago y pospago.
- Prorrateo por días.
- Varias reglas: gana la de mayor porcentaje.
- Facturas manuales: sin reglas, sin descuento temporal.
- Histórico: la factura conserva el descuento aplicado aunque la regla cambie.
- Pausa: `pause_policy=service` desplaza las fechas al reanudar.

## Limitaciones

- Solo porcentajes, no montos fijos.
- No se recalculan facturas históricas.
- La comisión del referente se implementa en `contract_referral`.
