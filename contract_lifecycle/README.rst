================================
Contract Lifecycle
================================

Permite pausar, reanudar y finalizar contratos de servicio reutilizando las
piezas OCA de ciclo de vida por línea.

- **Pausa planificada:** fecha de inicio y fecha de reanudación.
- **Pausa indefinida:** el contrato queda pausado hasta que se reanude
  manualmente.
- **Reanudación:** crea la línea sucesora y conserva el servicio restante.
- **Finalización:** terminación definitiva con motivo y fecha.

La pausa bloquea la generación de facturas. Si el contrato ya estaba facturado
por un período que no se prestará, se genera una nota de crédito.

Los descuentos y beneficios por referido se conservan al reanudar: se copian a
la línea sucesora, se ajustan las fechas y se mantiene el saldo de facturas.
Los meses máximos del referido se congelan durante la pausa.

Uso
===

1. Abrir un contrato en curso.
2. Usar **Pausar contrato**.
3. Indicar fecha de inicio y elegir pausa con fecha de reanudación o pausa
   indefinida.
4. Seleccionar motivo y comentario.
5. El contrato deja de facturar.
6. Si la pausa es indefinida, usar **Reanudar contrato** e indicar la fecha.
7. Si la pausa es planificada, el contrato se reanuda automáticamente al
   terminar la fecha indicada.
8. Para finalizar definitivamente, usar **Terminar contrato**.

La terminación es definitiva: no se puede reactivar el mismo contrato.

Configuración
=============

- Configurar los motivos de pausa en **Contabilidad > Configuración >
  Contratos > Motivos de pausa**.
- Asignar el grupo de gerentes de contabilidad a los usuarios que pueden
  pausar, reanudar o terminar contratos.
- El módulo activa la opción OCA de nota de crédito al detener una línea
  facturada.

Créditos
========

Autores
-------

* Odoo Community Association (OCA)

This module is part of the `OCA/contract <https://github.com/OCA/contract>`_
project on GitHub.
