================================
Contract Invoice Period
================================

Registra en la factura el período que realmente se está facturando cuando se
genera desde un contrato.

El módulo agrega datos estructurados de solo lectura en la factura y en sus
líneas:

- fecha de facturación del contrato, tomada de ``recurring_next_date``;
- inicio y fin del período facturado.

Esto evita depender de ``invoice_date``, que es la fecha del documento contable
y no necesariamente el período del servicio. También evita depender de los
marcadores ``#START#`` / ``#END#`` de la descripción, que son texto libre y no
se pueden buscar ni reportar.

La información se guarda en la factura porque, una vez creada, el contrato
avanza ``last_date_invoiced`` y el período anterior se pierde.

Uso
===

1. Instalar ``contract_invoice_period``.
2. Generar una factura desde un contrato, ya sea con el botón del contrato o
   con el cron de facturación recurrente.
3. Abrir la factura. En el bloque de fechas aparecen, solo para facturas de
   contrato:

   - **Contrato**;
   - **Fecha de facturación del contrato**;
   - **Inicio del período facturado**;
   - **Fin del período facturado**.

4. El PDF de la factura muestra la fecha de facturación del contrato y el
   período facturado.
5. En el listado de facturas se pueden activar las columnas de período y
   filtrar por **Facturas de contrato**.
6. En la pestaña de líneas de la factura se pueden activar las columnas
   **Fecha de facturación del contrato**, **Inicio del período facturado** y
   **Fin del período facturado**.

Las facturas creadas manualmente, sin líneas de contrato, quedan con estos
campos vacíos.

Configuración
=============

No requiere configuración.

El módulo depende de ``contract`` y ``account``. No cambia ``invoice_date`` ni
la fecha contable de la factura; solo agrega campos informativos de período.

Notas técnicas
==============

- ``contract.line._prepare_invoice_line()`` calcula el período antes de que el
  contrato actualice ``last_date_invoiced``.
- ``account.move.line`` guarda el período exacto de cada línea.
- ``account.move`` agrega el período de las líneas de producto: mínimo inicio y
  máximo fin.
- Las líneas de sección y nota no llevan período.
- Las facturas históricas no se reconstruyen; quedan con los campos vacíos.

Créditos
========

Autores
-------

* Odoo Community Association (OCA)

Mantenedores
------------

Este módulo es mantenido por la comunidad OCA.

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is part of the `OCA/contract <https://github.com/OCA/contract>`_
project on GitHub.
