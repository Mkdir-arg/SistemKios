# Reportes

### REQ-REP-001 · Los reportes son del Super Admin
**Estado:** implementado · **Dónde:** [core/views.py](../../apps/core/views.py)

`/reportes/`. El vendedor recibe un aviso y vuelve al inicio.

**Por qué:** el vendedor ve su jornada y su caja
([REQ-CAJ-009](04-caja-y-jornada.md#req-caj-009--mi-jornada-muestra-el-estado-de-la-caja-en-vivo));
la comparación entre puntos y entre vendedores es del dueño.

### REQ-REP-002 · El período por defecto es hoy y el mes calendario en curso
**Estado:** implementado · **Dónde:** [core/views.py](../../apps/core/views.py)

El reporte no pide fechas: muestra el total y la cantidad de ventas de **hoy** y del **mes
corriente** (desde el día 1). Solo cuenta ventas en estado `confirmada`.

**Por qué:** es la pregunta que el dueño hace todos los días. Los rangos arbitrarios son
[REQ-REP-006](#req-rep-006--filtrar-los-reportes-por-rango-de-fechas).

### REQ-REP-003 · Se ve la venta del mes por punto y por medio de pago
**Estado:** implementado · **Dónde:** [core/views.py](../../apps/core/views.py), [core/reportes.html](../../templates/core/reportes.html)

- **Por punto:** total y cantidad de ventas, ordenado de mayor a menor, con barra comparativa
  contra el punto que más vendió.
- **Por medio de pago:** suma de los `Pago` de ventas confirmadas del mes, agrupada por medio.

**Por qué:** el corte por punto dice dónde está el negocio; el de medios de pago dice cuánta
plata es efectivo (y por lo tanto cuánta pasa por la caja física).

### REQ-REP-004 · El reporte marca el stock bajo mínimo
**Estado:** implementado · **Dónde:** [core/views.py](../../apps/core/views.py)

Lista los `StockPunto` con `stock_minimo > 0` y `cantidad <= stock_minimo`, con producto y
punto, ordenados por la cantidad que queda.

Ver [REQ-STK-005](03-stock.md#req-stk-005--el-stock-mínimo-dispara-el-aviso-de-faltante).

### REQ-REP-005 · Las horas por vendedor se calculan sobre las jornadas del mes
**Estado:** implementado · **Dónde:** [core/views.py](../../apps/core/views.py)

Suma la duración de cada jornada iniciada en el mes. **Una jornada abierta cuenta hasta
ahora**, así que el número de hoy se mueve durante el turno.

**Por qué:** sirve para liquidar horas y para ver si el local estuvo atendido. Contar la
jornada abierta hasta el momento es lo que hace que el dato sirva durante el día — y también
lo que vuelve importante a
[REQ-CAJ-010](04-caja-y-jornada.md#req-caj-010--el-super-admin-no-puede-cerrar-una-jornada-olvidada):
una jornada que quedó abierta infla las horas.

## Pendientes

### REQ-REP-006 · Filtrar los reportes por rango de fechas
**Estado:** pendiente

Hoy los períodos están fijos ([REQ-REP-002](#req-rep-002--el-período-por-defecto-es-hoy-y-el-mes-calendario-en-curso)).
Falta elegir desde/hasta y poder filtrar por punto.

### REQ-REP-007 · Exportar los reportes
**Estado:** pendiente

Falta bajar los cuadros a CSV para poder trabajarlos aparte (por ejemplo, para el contador).

### REQ-REP-008 · Ranking de productos vendidos
**Estado:** pendiente

El dato está en `DetalleVenta` y no se muestra: qué se vende más y qué no rota, por punto y por
período. Es lo que hace falta para decidir qué comprar.
