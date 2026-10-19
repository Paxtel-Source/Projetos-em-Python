"""Gráfico da variação de preço de um produto ao longo do tempo."""

from decimal import Decimal
from pathlib import Path

from .alertas import formatar_moeda
from .armazenamento import Registro


def gerar_grafico(nome: str, registros: list[Registro], destino: Path,
                  preco_alvo: Decimal | None = None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    if len(registros) < 2:
        raise ValueError("São precisas pelo menos 2 verificações para desenhar o gráfico.")

    datas = [r.data for r in registros]
    precos = [float(r.preco) for r in registros]
    menor = min(registros, key=lambda r: r.preco)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(datas, precos, color="#00A86B", linewidth=2.2, marker="o", markersize=4, drawstyle="steps-post")
    ax.fill_between(datas, precos, min(precos) * 0.97, color="#00A86B", alpha=0.08, step="post")

    if preco_alvo is not None:
        ax.axhline(float(preco_alvo), color="#C8410B", linestyle="--", linewidth=1.2)
        ax.text(datas[0], float(preco_alvo), f" alvo {formatar_moeda(preco_alvo)}",
                color="#C8410B", va="bottom", fontsize=9)

    ax.annotate(f"menor: {formatar_moeda(menor.preco)}", xy=(menor.data, float(menor.preco)),
                xytext=(0, -18), textcoords="offset points", ha="center", fontsize=9, color="#1F2933")

    ax.set_title(nome, fontsize=13, fontweight="bold", loc="left")
    ax.yaxis.set_major_formatter(lambda v, _: formatar_moeda(Decimal(str(v))))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(destino, dpi=120)
    plt.close(fig)
    return destino
