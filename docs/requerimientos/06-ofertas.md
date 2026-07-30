# Ofertas

Los tests de esta área están en [ofertas/tests.py](../../apps/ofertas/tests.py) y son, por
ahora, los únicos del proyecto: es la parte con más reglas y la que no se puede romper sin
que se note en la plata.

## El motor

### REQ-OFE-001 · `cotizar` es la única fuente de verdad del precio
**Estado:** implementado · **Dónde:** [ofertas/services.py](../../apps/ofertas/services.py)

`cotizar(punto=…, items=…)` recibe qué producto y cuántas unidades, y devuelve una
`Cotizacion` con las líneas, los descuentos, la oferta que los causó y el total. La usan el
POS para mostrar y `registrar_venta` para grabar. Los precios que traiga el ítem se ignoran.

**Por qué:** con ofertas de por medio, cualquier segundo lugar donde se calcule un precio se
desincroniza. Un solo motor, dos consumidores.

### REQ-OFE-002 · Una oferta nunca sube el precio de lista
**Estado:** implementado · **Dónde:** [ofertas/models.py](../../apps/ofertas/models.py) (`descuento_del_grupo`) · **Verifica:** `NoSubeElPrecioTest`

Si el precio de la oferta es igual o mayor al de lista, el descuento es 0 y la oferta no se
aplica. Como los tipos de importe fijo valen igual en todos los puntos alcanzados, la misma
oferta puede aplicar en un punto y no en otro
([REQ-OFE-007](#req-ofe-007--las-ofertas-de-importe-fijo-usan-el-mismo-valor-en-todos-los-puntos)).

**Por qué:** una promo vieja contra un precio que bajó no puede terminar cobrándole más al
cliente que el cartel de la góndola.

### REQ-OFE-003 · Ante ofertas solapadas se aplica la más conveniente para el cliente
**Estado:** implementado · **Dónde:** [ofertas/services.py](../../apps/ofertas/services.py) (`_resolver`) · **Verifica:** `MejorParaElClienteTest`

En cada vuelta se elige la oferta que **más ahorra** con las unidades que quedan libres, se
consumen esas unidades y se repite hasta que ninguna pueda armar un grupo completo. Una
unidad la consume una sola oferta; el sobrante queda a precio de lista.

**Por qué:** el cliente no tiene que saber qué promo pedir. Y el vendedor no tiene que
elegir: elige el sistema, siempre para el mismo lado.

### REQ-OFE-004 · A igual ahorro gana la oferta más antigua
**Estado:** implementado · **Dónde:** [ofertas/services.py](../../apps/ofertas/services.py) · **Verifica:** `MejorParaElClienteTest::test_resultado_estable_para_el_mismo_carrito`

El criterio de desempate es el `pk` menor. El mismo carrito da siempre el mismo resultado.

**Por qué:** si el desempate fuera arbitrario, cotizar y confirmar podrían resolver distinto
y el cliente vería cambiar el total sin motivo.

### REQ-OFE-005 · Una oferta mal armada se ignora, no rompe la venta
**Estado:** implementado · **Dónde:** [ofertas/services.py](../../apps/ofertas/services.py), [ofertas/models.py](../../apps/ofertas/models.py) · **Verifica:** `TiposDeOfertaTest::test_combo_incompleto_no_aplica`

El motor saltea toda oferta sin ítems, con un producto sin precio en el punto, o cuyo grupo
necesita un producto que no está en el carrito. `errores_de_configuracion()` existe para
avisar en el ABM, pero **el motor no la usa**.

**Por qué:** entre cobrar sin una promo y no poder cobrar, se cobra. La promo mal cargada se
arregla después.

## Tipos de oferta

### REQ-OFE-006 · Hay cuatro tipos y el campo `valor` se lee según el tipo
**Estado:** implementado · **Dónde:** [ofertas/models.py](../../apps/ofertas/models.py) · **Verifica:** `TiposDeOfertaTest`

| Tipo | `valor` es | Ejemplo |
| --- | --- | --- |
| `precio_unitario` | el precio final de la unidad | alfajor a $800 |
| `porcentaje` | el % de descuento sobre el precio de lista | −15% |
| `precio_grupo` | el precio de todo el grupo | 2 x $1500, o alfajor + gaseosa a $1200 |
| `paga_n` | cuántas unidades se pagan del grupo | 3x2 (grupo de 3, valor 2) |

Qué productos y cuántas unidades forman el grupo lo definen los `OfertaItem` (único por
(oferta, producto), cantidad ≥ 1).

En `paga_n` **se pagan las unidades más caras**: las baratas van de regalo.

### REQ-OFE-007 · Las ofertas de importe fijo usan el mismo valor en todos los puntos
**Estado:** implementado · **Dónde:** [ofertas/models.py](../../apps/ofertas/models.py) · **Verifica:** `NoSubeElPrecioTest::test_misma_oferta_aplica_en_un_punto_y_no_en_el_otro`

`precio_unitario` y `precio_grupo` son un importe, no un descuento: valen igual en todos los
puntos alcanzados. Donde el precio de lista ya sea igual o menor, la oferta simplemente no
aplica. El `porcentaje`, en cambio, escala con el precio de cada punto.

**Por qué:** la promo se comunica con un cartel («alfajor a $800») y ese cartel dice lo mismo
en todos los locales.

### REQ-OFE-008 · El descuento de un combo se reparte entre sus líneas
**Estado:** implementado · **Dónde:** [ofertas/services.py](../../apps/ofertas/services.py) (`_repartir`) · **Verifica:** `MejorParaElClienteTest::test_la_suma_de_las_lineas_da_el_total`

El ahorro de un grupo se reparte entre sus productos **en proporción a lo que cada uno aporta
al precio de lista**, y el resto del redondeo va al producto que más pesa, de modo que la suma
de las líneas dé exactamente el total.

**Por qué:** el descuento tiene que quedar imputado a las líneas para que el detalle de la
venta cierre y para poder medir después qué producto se resignó.

## Vigencia y alcance

### REQ-OFE-009 · Una oferta vale por fechas y por punto
**Estado:** implementado · **Dónde:** [ofertas/models.py](../../apps/ofertas/models.py) · **Verifica:** `AlcanceYVigenciaTest`

- `desde` obligatorio, `hasta` opcional (**vacío = no vence**).
- `activa` la apaga sin borrarla ni perder el historial.
- Alcance `todos` (todos los puntos) o `seleccionados` (los puntos elegidos).
- `Oferta.objects.vigentes(punto, fecha)` es el filtro único de vigencia.
- `estado` deriva de todo eso: **vigente · programada · vencida · apagada**.

**Por qué:** las promos son de temporada y muchas veces se prueban en un local antes de
llevarlas al resto.

### REQ-OFE-010 · Una oferta puede tener tope de aplicaciones por venta
**Estado:** implementado · **Dónde:** [ofertas/models.py](../../apps/ofertas/models.py), [ofertas/services.py](../../apps/ofertas/services.py) · **Verifica:** `MejorParaElClienteTest::test_tope_por_venta`

`veces_max_por_venta` limita cuántos grupos de esa oferta entran en la misma venta. Vacío =
sin tope.

**Por qué:** evita que alguien limpie el stock promocionado en una sola compra.

### REQ-OFE-011 · La configuración de la oferta se valida en dos momentos
**Estado:** implementado · **Dónde:** [ofertas/models.py](../../apps/ofertas/models.py) · **Verifica:** `ConfiguracionTest`

- `clean()` valida lo que no depende de relaciones: rango de fechas y coherencia del `valor`
  según el tipo (porcentaje entre 0 y 100, precios no negativos, `paga_n` ≥ 1).
- `errores_de_configuracion()` valida lo que existe recién después de guardar: que haya
  ítems, que haya puntos si el alcance es `seleccionados`, y las reglas de forma de cada tipo
  (un precio especial va sobre un producto y una unidad; un precio por conjunto necesita 2
  unidades o más; `paga_n` va sobre un solo producto y tiene que ahorrar al menos una unidad).
- `puntos_sin_descuento()` avisa en qué puntos alcanzados la oferta no descontaría nada
  porque el precio de lista de ahí ya es igual o menor.

**Por qué:** los errores de forma son los que hacen que una promo «no aparezca» sin explicación.
Mejor avisarlos al cargarla que descubrirlos en el mostrador.

### REQ-OFE-012 · El POS muestra la promo con una etiqueta corta
**Estado:** implementado · **Dónde:** [ofertas/models.py](../../apps/ofertas/models.py) · **Verifica:** `ConfiguracionTest::test_etiquetas`

`Oferta.etiqueta` arma el texto: `2 x $1500`, `−15%`, `3x2`, `$800`, `combo $1200`. Si la
oferta entró varias veces en una línea, se prefija (`2× 2 x $1500`).

**Por qué:** el vendedor tiene que poder confirmarle al cliente qué promo se le aplicó sin
abrir nada.

## Pendientes

### REQ-OFE-013 · ABM de ofertas en la app
**Estado:** pendiente

No hay `views.py` ni `urls.py` en la app: hoy las ofertas se cargan desde el panel de Django.
Falta la pantalla de alta/edición con selección de productos y cantidades, alcance por punto,
vigencia, y el uso de `errores_de_configuracion()` y `puntos_sin_descuento()` como avisos
antes de guardar ([REQ-OFE-011](#req-ofe-011--la-configuración-de-la-oferta-se-valida-en-dos-momentos)).

### REQ-OFE-014 · Reporte de impacto de las ofertas
**Estado:** pendiente

El dato ya se guarda: `Venta.descuento_total`, `DetalleVenta.descuento` y la oferta por línea
([REQ-VEN-009](05-ventas-pos.md#req-ven-009--la-línea-guarda-el-precio-de-lista-el-descuento-y-la-oferta-que-lo-causó)).
Falta el reporte: cuánto se resignó por cada oferta y cuántas veces se aplicó, por punto y
por período.

### REQ-OFE-015 · Mostrarle al vendedor las ofertas vigentes de su punto
**Estado:** pendiente

`ofertas.services.ofertas_vigentes(punto)` ya existe y no la consume ninguna pantalla. Falta
el panel en el POS para poder responder «¿qué promos hay hoy?» sin memorizar nada.
