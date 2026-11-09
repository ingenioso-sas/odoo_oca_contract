Programa descuentos porcentuales temporales en las facturas generadas desde
un contrato.

Cada descuento se define como una regla con fechas, un máximo de facturas y
un porcentaje. Al generar la factura, el módulo calcula el descuento efectivo
del período, lo escribe en el campo estándar `discount` de la línea y guarda
una foto del motivo y la vigencia.

Solo se aplica el descuento más alto entre:

- el descuento base de la línea del contrato;
- las reglas temporales activas;
- los descuentos por referido, si el módulo de referidos está instalado.

El descuento se prorratea por días cuando el período facturado se cruza
parcialmente con la vigencia de la regla.
