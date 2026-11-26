# Portfolio Rebalance

Simulador de rebalanceo de una cartera de acciones en Python. Registra precios, calcula la distribución actual y propone operaciones para recuperar la asignación inicial.

## Ejecutar el proyecto

Con [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado, ejecuta estos comandos desde la raíz del repositorio.

```bash
uv sync --locked
uv run --locked python -m portfolio
uv run --locked python -m unittest discover -s tests -v
```

`uv` usa Python 3.15.2, fijado en `.python-version`, y prepara el entorno `.venv`. Las pruebas usan `unittest` y el proyecto no tiene dependencias externas.

## Cómo funciona

| Clase | Responsabilidad |
| --- | --- |
| `Stock` | Registra cotizaciones con fecha y devuelve el precio más reciente. |
| `Position` | Conserva las unidades compradas. `Position.buy` las calcula dividiendo el monto invertido por el precio vigente. |
| `Portfolio` | Fija la asignación objetivo en `from_positions`, calcula los pesos vigentes y devuelve las órdenes propuestas en `rebalance`. |
| `Order` | Indica ticker, lado, unidades y monto de cada operación propuesta. |

`Portfolio.from_positions(...)` usa el valor de mercado de las posiciones al momento de crear el portafolio. Para simular el paso del tiempo, crea la cartera primero y luego registra precios nuevos en los mismos objetos `Stock`.

Para rebalancear, el portafolio multiplica cada peso objetivo por el valor total vigente. Resta el valor actual de la posición y divide la diferencia por el precio del activo. Una diferencia positiva genera una compra y una negativa, una venta. Las órdenes se pueden calcular varias veces sin modificar las posiciones.

Los precios y aportes se ingresan como `Decimal`. Las unidades, los pesos y los montos calculados usan `Fraction` para representar fracciones exactas. El ejemplo redondea únicamente al mostrar la salida. El modelo supone una sola moneda, unidades fraccionarias y compras financiadas con las ventas. El cálculo omite el efectivo y las comisiones.

### Ejemplo

Se invierten $400 en META y $600 en AAPL, con ambas cotizaciones a $100. Cuando los precios pasan a $120 y $80, respectivamente, las dos posiciones quedan en $480.

| Ticker | Peso objetivo | Peso actual | Orden propuesta |
| --- | ---: | ---: | --- |
| META | 40% | 50% | Vender 0,8 acciones por $96 |
| AAPL | 60% | 50% | Comprar 1,2 acciones por $96 |

## Flujo de trabajo

`main` es la rama principal. Cada cambio se prepara en una rama corta y se propone mediante un pull request hacia `main`. GitHub Actions ejecuta las pruebas al abrir o actualizar un PR hacia `main` y en cada push a esa rama.
