# AGENTS.md — `contract_lifecycle`

## Reglas

- La pausa es de contrato, aunque OCA detiene líneas.
- Usar `contract_line_successor` para detener/planificar sucesoras.
- Usar `contract_termination` para la finalización definitiva.
- La terminación es irreversible: no reactivar el mismo contrato.
- La pausa bloquea la facturación con `is_paused` y el dominio del cron.
- Si ya se facturó el período pausado, generar nota de crédito.
- Copiar las reglas de descuento a la línea sucesora y conservar el saldo de
  facturas.
- Extender la duración de los beneficios de pausa según `pause_policy`.
- Congelar los meses máximos del referido con `paused_days`.
- No generar comisiones durante la pausa; las notas de crédito generan ajustes
  negativos.
- No recalcular facturas históricas.

## Archivos clave

- `models/contract_contract.py`: pausa, reanudación, terminación y copia de
  reglas.
- `models/contract_pause.py`: historial de pausas y cierre de pausas
  planificadas.
- `models/contract_invoice_discount.py`: política de pausa del descuento.
- `wizards/`: asistentes de pausa y reanudación.
- `views/contract_views.xml`: botones, estado e historial.
- `views/contract_portal_templates.xml`: estado en el portal.
