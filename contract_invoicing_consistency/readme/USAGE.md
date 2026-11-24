# Usage

## Validación de la próxima fecha de factura

Al guardar una línea recurrente, Odoo valida que:

```text
próximo fin de período >= próximo inicio de período
```

Si la fecha de factura deja el período sin días, se muestra un error con la
fecha esperada. Por ejemplo:

- línea **Pospago**, período `1 nov – 30 nov`: la fecha de factura debe ser
  `1 dic` (o posterior), no `1 nov`;
- línea **Prepago**, período `1 nov – 30 nov`: la fecha de factura debe ser
  `1 nov` (o el inicio del período), no una fecha anterior.

## Advertencia de tipos mezclados

Si el contrato tiene líneas Prepago y Pospago, el formulario del contrato
muestra una advertencia con los nombres de las líneas de cada tipo.

Se facturarán en fechas distintas. Si se desea una sola factura por período,
todas las líneas deben compartir el mismo tipo de facturación.
