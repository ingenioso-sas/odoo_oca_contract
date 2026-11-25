# Usage

## Configurar el ciclo de facturación

En el contrato, pestaña **Ciclo de facturación**:

- **Día de facturación**: día del mes en que se emite la factura pospaga.
  Por defecto, 1. Si el mes no tiene ese día, se usa el último día del mes.
- **Duración de la prueba**: duración de la prueba gratuita desde la fecha de
  inicio del servicio. 0 = sin prueba.
- **Unidad de la prueba**: días o meses.
- **Descuento de prueba (%)**: porcentaje del descuento. Normalmente 100.
- **Omitir facturas en cero**: si se marca, no se crea la factura cuando el
  total es cero. Las fechas del contrato avanzan igualmente.

Los mismos campos están disponibles en la plantilla del contrato y se copian
al crear un contrato desde la plantilla.

## Ejemplo: inicio el 15 de octubre, facturar el 1

Contrato mensual pospago, día de facturación 1:

```text
Primer período:  15 oct – 31 oct
Primera factura: 1 nov
Importe:         precio mensual × 17/31
Siguiente:       1 nov – 30 nov, factura 1 dic
```

El precio se prorratea y la cantidad permanece en 1.

## Ejemplo: prueba de un mes desde el inicio del servicio

Contrato mensual pospago, inicio 15 de octubre, día 1, prueba de **1 mes**:

```text
Prueba: 15 oct – 14 nov

Factura 1 nov: 15 oct – 31 oct → 100% descuento
Factura 1 dic: 1 nov – 30 nov   → 14 días gratis, 16 días cobrados
Factura 1 ene: 1 dic – 31 dic   → cobro completo
```

La prueba se cuenta desde el **inicio del servicio**, no desde el primer
período completo. Si cae en el pasado, se aplica igual sobre las facturas que
cubran ese rango; no se desplaza al futuro.

La segunda factura se prorratea porque la prueba cubre solo una parte del
período:

```text
Descuento: 100% × 14/30 = 46.67%
Cobro:     100% × 16/30 = 53.33%
```

## Ejemplo: prueba de 30 días

```text
Prueba: 15 oct – 13 nov

Factura 1 nov: 15 oct – 31 oct → 100% descuento
Factura 1 dic: 1 nov – 30 nov   → 13 días gratis, 17 días cobrados
```

## Recalcular fechas

La acción **Recalcular fechas** de la línea respeta el día de facturación
configurado. Si no hay facturas, calcula la próxima fecha desde el inicio del
contrato; si hay facturas, calcula el siguiente día de facturación después del
último período facturado.

## Facturas en cero

- **Omitir facturas en cero desmarcado** (por defecto): la factura con importe
  cero se crea.
- **Omitir facturas en cero marcado**: la factura no se crea; las fechas del
  contrato avanzan. Si la prueba continúa en el siguiente período, esa factura
  conserva el descuento prorrateado que le corresponda.

## Límites

- El ciclo de facturación y la prueba gratuita aplican a líneas **pospago**
  con recurrencia por línea.
- Para líneas prepago se mantiene el comportamiento estándar del contrato.
- La prueba no se extiende automáticamente al pausar el contrato.
