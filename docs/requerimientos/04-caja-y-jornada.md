# Caja y jornada

## Jornada

### REQ-CAJ-001 · Vender exige una jornada abierta
**Estado:** implementado · **Dónde:** [caja/services.py](../../apps/caja/services.py), [ventas/views.py](../../apps/ventas/views.py)

La jornada es el turno de trabajo de un vendedor en un punto. Toda venta y todo movimiento
de caja cuelgan de ella. Sin jornada abierta, el POS redirige a abrirla y los endpoints de
venta devuelven 400.

**Por qué:** es lo que permite responder «¿quién vendió esto y en qué turno?» y cuadrar el
efectivo contra una persona y un rango de horas.

### REQ-CAJ-002 · Un vendedor tiene como máximo una jornada abierta
**Estado:** implementado · **Dónde:** [caja/models.py](../../apps/caja/models.py), [caja/services.py](../../apps/caja/services.py)

Lo garantiza la constraint `una_jornada_abierta_por_vendedor` (única sobre `vendedor` con
`estado='abierta'`) y además lo valida `abrir_jornada` con un mensaje claro.

**Por qué:** si hubiera dos, las ventas se repartirían entre turnos y ningún arqueo cerraría.

### REQ-CAJ-003 · La jornada se abre declarando el efectivo inicial
**Estado:** implementado · **Dónde:** [caja/views.py](../../apps/caja/views.py)

Al ingresar, el vendedor declara con cuánta plata arranca la caja (puede ser 0; no se
aceptan negativos) y de ahí va derecho al POS. Un vendedor sin punto asignado ve una
pantalla que se lo explica y no puede abrir jornada
([REQ-USR-002](01-puntos-y-usuarios.md#req-usr-002--un-vendedor-necesita-un-punto-el-super-admin-no-tiene-ninguno)).

### REQ-CAJ-004 · La jornada es solo de los vendedores
**Estado:** implementado · **Dónde:** [caja/views.py](../../apps/caja/views.py)

El Super Admin no abre jornada ni vende: las pantallas de caja lo devuelven al inicio con un
aviso.

**Por qué:** el dueño mira; el que atiende es responsable de una caja. Mezclarlos rompe la
trazabilidad del efectivo.

## Movimientos de caja

### REQ-CAJ-005 · Se registran ingresos y egresos de efectivo con motivo
**Estado:** implementado · **Dónde:** [caja/services.py](../../apps/caja/services.py), [caja/views.py](../../apps/caja/views.py)

Durante la jornada se pueden cargar movimientos (retiros, gastos, aportes) con tipo, monto
mayor a 0 y motivo. Sobre una jornada cerrada se rechazan.

**Por qué:** el efectivo se toca por fuera de las ventas (se paga un flete, el dueño retira).
Sin registrarlo, el arqueo siempre da diferencia.

## Arqueo

### REQ-CAJ-006 · El efectivo esperado se calcula, no se carga
**Estado:** implementado · **Dónde:** [caja/services.py](../../apps/caja/services.py)

`efectivo_esperado = monto inicial + ventas cobradas en efectivo + ingresos − egresos`.
Solo se cuentan las ventas **confirmadas** y solo los pagos con medio efectivo: tarjeta y
transferencia no están en el cajón.

**Por qué:** es el número contra el que se compara el conteo físico. Si se pudiera editar, no
serviría para nada.

### REQ-CAJ-007 · Al cerrar se compara lo contado con lo esperado y se informa la diferencia
**Estado:** implementado · **Dónde:** [caja/services.py](../../apps/caja/services.py), [caja/views.py](../../apps/caja/views.py)

El vendedor ingresa el efectivo contado; el sistema guarda `monto_final`, la hora de fin, y
avisa esperado / contado / diferencia. **La diferencia no bloquea el cierre**: se registra y
listo.

**Por qué:** una diferencia de $50 no puede dejar a un vendedor sin poder cerrar e irse a su
casa. El dato queda para que el dueño lo mire.

### REQ-CAJ-008 · Cerrar la jornada no cierra la sesión
**Estado:** implementado · **Dónde:** [caja/views.py](../../apps/caja/views.py)

Después del cierre se vuelve al inicio, con el resultado del arqueo en el mensaje.

### REQ-CAJ-009 · «Mi jornada» muestra el estado de la caja en vivo
**Estado:** implementado · **Dónde:** [caja/views.py](../../apps/caja/views.py), [caja/mi_jornada.html](../../templates/caja/mi_jornada.html)

Muestra el efectivo esperado, los movimientos cargados y la cantidad de ventas del turno, y
desde ahí se cierra con arqueo.

## Pendientes

### REQ-CAJ-010 · El Super Admin no puede cerrar una jornada olvidada
**Estado:** pendiente

Si un vendedor se va sin cerrar, la jornada queda abierta para siempre: bloquea su próximo
login normal ([REQ-CAJ-002](#req-caj-002--un-vendedor-tiene-como-máximo-una-jornada-abierta)) y
distorsiona el reporte de horas ([REQ-REP-005](08-reportes.md#req-rep-005--las-horas-por-vendedor-se-calculan-sobre-las-jornadas-del-mes)).
Falta que el Super Admin pueda cerrarla, dejando registrado que la cerró él.

### REQ-CAJ-011 · Ver el historial de jornadas cerradas
**Estado:** pendiente

Hoy la jornada cerrada solo se consulta desde el panel de Django. Falta el listado por punto
y fecha con el arqueo de cada una.
