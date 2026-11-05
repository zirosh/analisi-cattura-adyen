"""Charts (PNG) for the capture-delay analysis.

  output/chart_auth_to_refund_histogram.png
  output/chart_monthly_trend.png
  output/chart_cost_by_threshold.png
"""
# ----------------------------------------------------------------- PARAMETERS
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from common import ALL_THRESHOLDS_H, OUT_DIR, THRESHOLDS_H

OPPORTUNITY_RATE = 0.03
# Go-forward GMV for the run-rate panel: 2025 full-year perimeter GMV (EUR), read from data
# Palette: validated reference categorical slots 1-3 (blue, orange, aqua) + neutral text tokens
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
# ----------------------------------------------------------------------------

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"], "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "legend.frameon": False,
    "axes.titlecolor": INK, "axes.titlesize": 12, "axes.titleweight": "semibold", "axes.titlelocation": "left",
})
P = lambda *a: os.path.join(OUT_DIR, *a)


def eur(x, _=None):
    return f"€{x:,.0f}"


def histogram():
    h = pd.read_csv(P("phase3_refunds", "histogram_auth_to_first_refund.csv"))
    full = pd.DataFrame({"hour_bin": range(168)}).merge(h, how="left").fillna({"payments": 0})
    cap = max(25, full.loc[full.hour_bin > 0, "payments"].max() * 1.6)
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.bar(full.hour_bin + 0.5, full.payments.clip(upper=cap), width=0.8, color=C1, linewidth=0)
    first = int(full.payments.iloc[0])
    ax.annotate(f"0–1 h: {first:,} payments (bar truncated)", xy=(0.5, cap), xytext=(8, cap * 0.93),
                color=INK, fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    for s in THRESHOLDS_H:
        ax.axvline(s, color=MUTED, lw=1, ls=(0, (3, 3)))
        ax.text(s + 0.8, cap * 0.78, f"S = {s} h", color=INK2, fontsize=8.5)
    ax.set_xlim(0, 168)
    ax.set_ylim(0, cap * 1.02)
    ax.set_xticks(range(0, 169, 12))
    ax.set_xlabel("Hours from Authorised to first refund request")
    ax.set_ylabel("Payments (per 1-hour bin)")
    tot = h.payments.sum()
    share = h.cum_share_of_refunded_payments.iloc[-1]
    ax.set_title("Most refunds that capture delay could avoid happen in the first hour after authorisation")
    fig.text(0.01, 0.005, f"In-perimeter payments with a valid refund, first refund request within 0–7 days: {tot:,} "
             f"({share:.0%} of all refunded in-perimeter payments). Spike at 48–50 h = one-off batch refund (79 Kenwood EU orders of 15 Nov 2025). Source: Adyen accounting export 2025.",
             color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(P("chart_auth_to_refund_histogram.png"), dpi=160)
    plt.close(fig)


def trend():
    m = pd.read_csv(P("phase7_trend", "monthly_trend.csv"), parse_dates=["auth_month"])
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    series = [(12, C1), (24, C2), (72, C3)]
    for s, col in series:
        d = m[m.threshold_h == s]
        axes[0].plot(d.auth_month, d.pct_gmv_refunded_in_s, color=col, lw=2, marker="o", ms=4, label=f"S = {s} h")
        axes[1].plot(d.auth_month, d.avoidable_fee_cost_eur, color=col, lw=2, marker="o", ms=4, label=f"S = {s} h")
    axes[0].set_title("Refunded within S, % of in-perimeter GMV")
    axes[0].yaxis.set_major_formatter(lambda x, _: f"{x:.1f}%")
    axes[1].set_title("Avoidable fee cost per month (EUR)")
    axes[1].yaxis.set_major_formatter(eur)
    for ax in axes:
        ax.axvspan(pd.Timestamp("2025-09-20"), pd.Timestamp("2025-12-10"), color=GRID, alpha=0.5, lw=0)
    axes[1].text(pd.Timestamp("2025-09-16"), axes[1].get_ylim()[1] * 0.9, "Shaded: SFCC immediate auto-capture live\nacross brands (Hybris being decommissioned)",
                 color=INK2, fontsize=8.5, va="top", ha="right")
    axes[0].legend(loc="upper left")
    axes[1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %Y"))
    fig.suptitle("Avoidable refunds jump once SFCC captures immediately", x=0.01, ha="left", fontsize=13, fontweight="semibold", color=INK)
    fig.text(0.01, 0.005, "By authorisation month. Jan–Sep perimeter is mostly Hybris (batch capture ~1 h, quick cancellations became cancels). "
             "Nov–Dec include Black Friday / Christmas.\nOne-off: 79 Kenwood EU orders of 15 Nov refunded in one batch 49 h later.", color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.045, 1, 0.97))
    fig.savefig(P("chart_monthly_trend.png"), dpi=160)
    plt.close(fig)


def cost_by_threshold():
    net = pd.read_csv(P("phase6_opportunity", "net_cost_by_threshold.csv"))
    full = net[net.period == "full_data"].set_index("threshold_h")
    base = pd.read_csv(P("phase7_trend", "annualisation_base.csv"))
    sf = base[base.basis == "SFCC immediate, all data"].groupby("threshold_h")[["avoidable_fee_cost_eur", "chargeback_fees_eur", "captured_eur"]].sum()
    gmv = full["captured_eur"].iloc[0]
    sf_gross = (sf.avoidable_fee_cost_eur + sf.chargeback_fees_eur) / sf.captured_eur * gmv
    th = ALL_THRESHOLDS_H
    panels = [("2025 as observed (in-perimeter, Jan–Dec)", full.loc[th, "avoidable_fee_cost_eur"] + full.loc[th, "chargeback_fees_eur"]),
              ("Go-forward: SFCC immediate-capture run-rate on 2025 GMV", sf_gross.loc[th])]
    opp = pd.Series({s: gmv * s / 24 / 365 * OPPORTUNITY_RATE for s in th})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    x = range(len(th))
    for ax, (title, gross) in zip(axes, panels):
        w = 0.38
        ax.bar([i - w / 2 for i in x], gross.values, width=w - 0.02, color=C1, label="Avoidable fees (saving)")
        ax.bar([i + w / 2 for i in x], opp.values, width=w - 0.02, color=C2, label=f"Opportunity cost ({OPPORTUNITY_RATE:.0%})")
        n = gross.values - opp.values
        ax.plot(list(x), n, color=C3, lw=2, marker="o", ms=6, label="Net = saving − opportunity cost", zorder=3)
        ax.axhline(0, color=MUTED, lw=1)
        ax.set_xticks(list(x))
        ax.set_xticklabels([f"{s} h" for s in th])
        ax.set_xlabel("Capture delay S")
        ax.yaxis.set_major_formatter(eur)
        ax.set_title(title, fontsize=10.5)
        best = int(pd.Series(n, index=th).idxmax())
        ax.annotate(f"best: {best} h, net {eur(max(n))}", (th.index(best), max(n)), xytext=(10, 14), textcoords="offset points",
                    color=INK, fontsize=8.5, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    axes[0].legend(loc="upper left", fontsize=8.5)
    fig.suptitle("A short delay pays off, a long one does not: savings saturate after ~1 h, opportunity cost grows linearly",
                 x=0.01, ha="left", fontsize=12, fontweight="semibold", color=INK)
    fig.text(0.01, 0.005, f"Annual EUR on {eur(gmv)} in-perimeter GMV (2025). Opportunity cost = GMV × S/24/365 × {OPPORTUNITY_RATE:.0%}. "
             "Customer-care savings not included (parameter, default 0).", color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(P("chart_cost_by_threshold.png"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    histogram()
    trend()
    cost_by_threshold()
    print("charts written")
