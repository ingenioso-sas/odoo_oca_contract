# Usage

## Regenerar la última factura eliminada

1. Abra el contrato y entre a la línea recurrente.
2. Pulse **Regenerar factura**.
3. El asistente propone:
   - el período siguiente al último período facturado;
   - la fecha de factura original (en pospago, el día siguiente al fin del
     período).
4. Revise o ajuste el período y la fecha de factura.
5. Marque **Publicar factura** si desea publicarla inmediatamente.
6. Pulse **Regenerar factura**.

La factura se crea con el período y la fecha indicados. Las fechas de la
línea se recalculan con las facturas existentes, por lo que la programación
queda consistente.

## Recalcular fechas sin regenerar

Si solo necesita corregir `last_date_invoiced` y `recurring_next_date`:

1. Abra la línea del contrato.
2. Pulse **Recalcular fechas**.

Las fechas se toman de las facturas en borrador y publicadas que sigan
existiendo.

## Borrado de facturas

- Las facturas **publicadas** vinculadas a un contrato no se pueden eliminar.
  Cancele la factura o emita una nota crédito. Si necesita reemplazarla, use
  **Regenerar factura**.
- Al eliminar una factura en **borrador**, las fechas de la línea se
  recalculan automáticamente.

## Permisos

El botón y el asistente están disponibles para el grupo
**Contrato: Regenerar facturas**, que se agrega a los administradores de
Ajustes.
