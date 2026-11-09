================================
Contract Referral
================================

Gestiona referidos entre clientes de contrato.

Cada referido tiene dos beneficios independientes:

- **Descuento del referido:** porcentaje de descuento en las facturas del
  cliente que llegó por recomendación.
- **Comisión del referente:** porcentaje de la factura del referido que se
  registra como comisión para quien lo trajo.

Ambos beneficios tienen duración máxima en meses y máximo de facturas. Se
detienen cuando se cumple cualquiera de los dos límites.

Si el referido tiene una factura vencida, pierde el descuento para la
siguiente factura y no lo recupera. La comisión del referente se mantiene
mientras el contrato del referido siga activo, dentro de los límites
configurados.

Uso
===

1. Crear un referido desde **Contabilidad > Configuración > Contratos >
   Referidos**.
2. Seleccionar cliente referente, cliente referido, contrato del referido,
   porcentajes, base de comisión y límites.
3. Guardar. Se crean automáticamente las reglas de descuento en las líneas
   del contrato del referido.
4. Generar las facturas del contrato.

La factura del referido muestra el descuento y su motivo. Cuando la factura
se valida, se registra una comisión para el referente.

Las comisiones se consultan en **Contabilidad > Configuración > Contratos >
Comisiones por referido**.

Configuración
=============

No requiere configuración global. Por cada referido se define el porcentaje
de descuento, el porcentaje de comisión, la base de la comisión y los límites
de meses y facturas.

La comisión se calcula sobre el monto de la factura del referido después de
sus descuentos. Se puede elegir entre monto sin impuestos o monto total.

Créditos
========

Autores
-------

* Odoo Community Association (OCA)

This module is part of the `OCA/contract <https://github.com/OCA/contract>`_
project on GitHub.
