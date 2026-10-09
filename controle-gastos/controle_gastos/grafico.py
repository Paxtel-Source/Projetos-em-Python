"""Gráfico de gastos por categoria com matplotlib."""

from decimal import Decimal
from pathlib import Path


def gerar_grafico(gastos: dict[str, Decimal], titulo: str, destino: Path,
                  mostrar: bool = False) -> Path:
    """Salva um gráfico de barras horizontais com os gastos de cada categoria.

    O matplotlib é importado só aqui dentro: assim o resto do programa
    funciona mesmo que ele não esteja instalado.
    """
    try:
        import matplotlib
        if not mostrar:
            matplotlib.use("Agg")  # gera a imagem sem precisar abrir janela
        import matplotlib.pyplot as plt
    except ImportError:
        raise RuntimeError(
            "O matplotlib nao esta instalado. Rode: pip install -r requirements.txt"
        ) from None

    if not gastos:
        raise ValueError("Nao ha despesas neste mes para gerar o grafico.")

    # Inverte para que a maior categoria fique no topo do gráfico
    categorias = list(gastos.keys())[::-1]
    valores = [float(v) for v in gastos.values()][::-1]
    total = sum(valores)

    fig, ax = plt.subplots(figsize=(8, 0.6 * len(categorias) + 1.8))
    barras = ax.barh(categorias, valores, color="#4C72B0")

    for barra, valor in zip(barras, valores):
        rotulo = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        ax.text(barra.get_width(), barra.get_y() + barra.get_height() / 2,
                f"  {rotulo} ({valor / total:.0%})", va="center", fontsize=9)

    ax.set_title(titulo, fontsize=13, fontweight="bold")
    ax.set_xlabel("Valor gasto (R$)")
    ax.set_xlim(0, max(valores) * 1.35)  # espaço para os rótulos
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()

    fig.savefig(destino, dpi=120)
    if mostrar:
        plt.show()
    plt.close(fig)
    return destino
