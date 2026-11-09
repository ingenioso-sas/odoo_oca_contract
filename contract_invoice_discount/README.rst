================================
Contract Invoice Discount
================================

Programa descuentos porcentuales temporales en las facturas generadas desde
un contrato.

Cada descuento se define como una regla con fechas, un máximo de facturas y
un porcentaje. Al generar la factura, el módulo calcula el descuento efectivo
del período, lo escribe en el campo estándar ``discount`` de la línea y guarda
una foto del motivo y la vigencia.

Solo se aplica el descuento más alto entre:

- el descuento base de la línea del contrato;
- las reglas temporales activas;
- los descuentos por referido, si el módulo de referidos está instalado.

El descuento se prorratea por días cuando el período facturado se cruza
parcialmente con la vigencia de la regla.

Uso
===

1. Abrir una línea de contrato.
2. Ir a la pestaña **Descuentos de factura**.
3. Crear una regla con nombre, porcentaje, fecha de inicio, fecha de fin y
   máximo de facturas (0 = sin límite).
4. Generar la factura desde el contrato.

La factura muestra la columna estándar **Descuento** y, debajo de la
descripción de la línea, el nombre y la vigencia del descuento aplicado.

En la plantilla del contrato, la línea tiene los campos de promoción:
nombre, porcentaje, duración en meses y máximo de facturas. Al crear un
contrato desde la plantilla, esos valores se convierten en una regla de
descuento en la línea del contrato.

Configuración
=============

No requiere configuración global. Los descuentos se configuran por línea de
contrato o por línea de plantilla.

Créditos
========

Autores
-------

* Odoo Community Association (OCA)

This module is part of the `OCA/contract <https://github.com/OCA/contract>`_
project on GitHub.
