# AGENTS.md — `contract_invoice_period`

## Reglas

- No cambiar `invoice_date` ni la fecha contable para representar el período.
- El período se calcula una sola vez, antes de que el contrato actualice
  `last_date_invoiced`.
- Guardar el período en la factura y en la línea; no depender de los
  marcadores `#START#` / `#END#`.
- La cabecera agrega el período de las líneas de producto:
  - inicio = mínimo;
  - fin = máximo.
- Las líneas de sección y nota no llevan período.
- Las facturas manuales sin contrato deben quedar con los campos vacíos.
- Mantener el módulo separado de notificaciones, WhatsApp y estado de cuenta.

## Archivos clave

- `models/contract_line.py`: agrega el período a los valores de la línea de
  factura antes de que el contrato avance.
- `models/account_move_line.py`: campos de período en la línea.
- `models/account_move.py`: campos de contrato y período en la cabecera.
- `views/account_move_views.xml`: formulario, listado y búsqueda.
- `report/report_invoice.xml`: bloque de período en el PDF.
- `tests/test_contract_invoice_period.py`: prepago, pospago, prorrateo,
  múltiples líneas y factura manual.
