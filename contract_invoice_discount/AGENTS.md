# AGENTS.md — `contract_invoice_discount`

## Reglas

- El campo `contract.line.discount` sigue siendo el descuento base.
- Los descuentos temporales viven en `contract.invoice.discount`.
- Solo se aplica el descuento más alto; no se suman.
- El descuento se calcula antes de que el contrato avance
  `last_date_invoiced`.
- Se prorratea por días si el período se cruza parcialmente.
- La línea de factura guarda una foto del descuento aplicado; no depender de
  la regla actual para el histórico.
- Las líneas de sección y nota no llevan descuento.
- No cambiar `invoice_date` ni la fecha contable.
- La promoción de plantilla se define en la línea de plantilla y se copia al
  crear el contrato.

## Archivos clave

- `models/contract_invoice_discount.py`: regla, vigencia, máximo de facturas y
  cálculo prorrateado.
- `models/contract_line.py`: selección del mayor descuento y escritura en la
  línea de factura.
- `models/contract_contract.py`: copia de la promoción desde la plantilla.
- `models/account_move_line.py`: foto del descuento aplicado.
- `views/contract_line_views.xml`: pestaña de descuentos.
- `views/contract_template_line_views.xml`: promoción en la plantilla.
- `report/report_invoice.xml`: motivo y vigencia en el PDF.
