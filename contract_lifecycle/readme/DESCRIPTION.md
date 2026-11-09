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
