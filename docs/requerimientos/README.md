# Requerimientos — SistemKios

Este es el **mapa funcional del sistema**: cada regla de negocio que decidimos vive
acá, con su estado y el lugar del código donde está implementada.

No es documentación de código (para eso está el código, que ya se explica solo). Es
la memoria de **qué tiene que hacer el sistema y por qué**, para que al agregar algo
nuevo se vea de una qué reglas ya existen y con cuáles hay que no chocar.

## Índice

| Archivo | Qué cubre |
| --- | --- |
| [00-generales.md](00-generales.md) | Reglas transversales: multi-punto, roles, dinero, lector, infraestructura |
| [01-puntos-y-usuarios.md](01-puntos-y-usuarios.md) | Puntos, Depósito, usuarios, acceso |
| [02-catalogo-y-precios.md](02-catalogo-y-precios.md) | Productos, códigos de barras, precio por punto, servicios |
| [03-stock.md](03-stock.md) | Stock por punto, kardex, ingreso de mercadería, alta rápida |
| [04-caja-y-jornada.md](04-caja-y-jornada.md) | Jornada del vendedor, movimientos de caja, arqueo |
| [05-ventas-pos.md](05-ventas-pos.md) | POS, cotización, cobro, registro de la venta |
| [06-ofertas.md](06-ofertas.md) | Promociones y el motor de precios |
| [07-transferencias.md](07-transferencias.md) | Movimiento de stock entre puntos |
| [08-reportes.md](08-reportes.md) | Reportes del negocio |
| [09-tiempo-real.md](09-tiempo-real.md) | WebSockets, eventos y pantallas reactivas |

## Cómo se escribe un requerimiento

Un requerimiento es **una regla, en una oración**, más el por qué y dónde vive.
Si no se puede decir en una oración, son dos requerimientos.

```markdown
### REQ-AREA-000 · Título corto, afirmando qué hace el sistema
**Estado:** implementado · **Dónde:** [ventas/services.py](../../apps/ventas/services.py)

La regla, en presente y en concreto: qué hace el sistema, con qué límites.

**Por qué:** el motivo de negocio. Esto es lo que no se puede deducir del código.
```

Un ejemplo real, para calibrar el nivel de detalle:
[REQ-VEN-004](05-ventas-pos.md#req-ven-004--el-precio-de-la-venta-lo-resuelve-el-servidor).

Campos opcionales, cuando aportan:

- `**Verifica:**` el test que lo cubre (`apps/ofertas/tests.py::CotizarTests::test_x`).
- `**Depende de:**` otros REQ que este da por ciertos.
- `**Reemplaza a:**` el REQ que quedó viejo (el viejo pasa a `descartado`, no se borra).

### IDs

`REQ-<ÁREA>-<nnn>`, correlativo dentro del área y **nunca reutilizado**: si un
requerimiento se cae, su número queda marcado como descartado. El ID es un identificador
estable, no un orden de lectura: como los pendientes van al final de cada archivo, los
números no siguen el orden del texto.

`GEN` generales · `INF` infraestructura · `PTO` puntos · `USR` usuarios y acceso ·
`CAT` catálogo y precios · `STK` stock · `CAJ` caja y jornada · `VEN` ventas y POS ·
`OFE` ofertas · `TRF` transferencias · `REP` reportes · `RT` tiempo real

### Estados

| Estado | Significa |
| --- | --- |
| `implementado` | Está andando en el código apuntado. |
| `parcial` | Anda una parte; el bloque dice qué falta. |
| `pendiente` | Decidido pero sin código todavía. |
| `descartado` | Se dio de baja. Se deja escrito con el motivo, para no volver a discutirlo. |

Los pendientes se listan con `grep -rn "pendiente" docs/requerimientos/`.

## Regla de trabajo

**Cada cambio funcional actualiza este registro en el mismo commit.** Feature nueva
⇒ REQ nuevo. Cambio de una regla ⇒ se edita el REQ existente (y si el cambio invierte
la regla, el viejo pasa a `descartado` y se escribe uno nuevo que lo reemplaza).
Refactor sin cambio de comportamiento ⇒ solo se corrige el link de **Dónde**.

## Fuera de alcance (decidido)

No se hacen, y no hace falta volver a evaluarlas salvo que el negocio cambie:

- **Facturación AFIP / ARCA.** El sistema es de control interno; la facturación va por fuera.
- **Clientes y cuenta corriente.** La venta es anónima y se cobra en el momento.
- **Productos por peso.** Todo se vende por unidades enteras (ver [REQ-GEN-006](00-generales.md#req-gen-006--los-productos-se-venden-por-unidades-enteras)).
- **Variantes de producto** (talle, color). Cada variante, si aparece, es un producto con su código.
