# Documentación técnica: `contract_invoice_period`

## Propósito

Conservar en la factura el período que el contrato facturó.

El contrato calcula el período en `contract.line._get_period_to_invoice()`,
pero hasta ahora solo lo usaba para reemplazar marcadores en la descripción y
luego avanzaba `last_date_invoiced`. Con este módulo el período queda grabado
en la factura y en sus líneas.

## Dependencias

```python
depends = ["contract", "account"]
```

## Campos

### `account.move.line`

| Campo | Tipo | Origen |
|---|---|---|
| `contract_billing_date` | Date | `contract.line.recurring_next_date` |
| `contract_period_start` | Date | `_get_period_to_invoice()[0]` |
| `contract_period_end` | Date | `_get_period_to_invoice()[1]` |

### `account.move`

| Campo | Tipo | Cálculo |
|---|---|---|
| `contract_id` | Many2one | Contrato único de las líneas |
| `contract_billing_date` | Date | Mínimo de las líneas |
| `contract_period_start` | Date | Mínimo de las líneas |
| `contract_period_end` | Date | Máximo de las líneas |

Los campos de cabecera son calculados y almacenados. Se recalculan si cambian
las líneas. Solo consideran líneas de producto, no secciones ni notas.

## Flujo

1. `contract.contract._prepare_recurring_invoices_values()` obtiene las líneas
   a facturar.
2. `contract.line._prepare_invoice_line()` calcula el período con
   `last_date_invoiced` y `recurring_next_date` y lo agrega a los valores de la
   línea.
3. `account.move` se crea con las líneas y calcula los campos de cabecera.
4. Después, el contrato actualiza `last_date_invoiced`. El período facturado ya
   quedó guardado en la factura.

## Compatibilidad

- Prepago y pospago.
- Prórroga/limitación por `date_end`.
- Varias líneas con períodos distintos.
- Facturas manuales sin contrato: campos vacíos.
- No modifica `invoice_date` ni el comportamiento contable.

## Limitaciones

- Las facturas históricas creadas antes de instalar el módulo no se pueden
  reconstruir de forma fiable; quedan con los campos vacíos.
- La cabecera muestra el mínimo/máximo cuando hay períodos distintos. El
  detalle exacto está en cada línea.
