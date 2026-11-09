Registra en la factura el período que realmente se está facturando cuando se
genera desde un contrato.

El módulo agrega datos estructurados de solo lectura en la factura y en sus
líneas:

- fecha de facturación del contrato, tomada de `recurring_next_date`;
- inicio y fin del período facturado.

Esto evita depender de `invoice_date`, que es la fecha del documento contable
y no necesariamente el período del servicio. También evita depender de los
marcadores `#START#` / `#END#` de la descripción, que son texto libre y no se
pueden buscar ni reportar.

La información se guarda en la factura porque, una vez creada, el contrato
avanza `last_date_invoiced` y el período anterior se pierde.
