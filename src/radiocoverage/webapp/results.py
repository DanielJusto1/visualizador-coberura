"""Result panels shared by the link pages."""

import streamlit as st

from radiocoverage.geo import GeoPoint
from radiocoverage.link_budget import LinkBudgetResult
from radiocoverage.link_map import build_link_map
from radiocoverage.path import LinkPath
from radiocoverage.profile import TerrainProfile
from radiocoverage.terrain import TerrainError
from radiocoverage.webapp import charts, style
from radiocoverage.webapp.compute import profile_png
from radiocoverage.webapp.settings import RadioSettings
from radiocoverage.webapp.tables import budget_csv, link_budget_rows
from radiocoverage.webapp.texts import current_language, t


def link_verdict(budget: LinkBudgetResult) -> None:
    p = budget.parameters
    style.verdict(
        budget.is_viable,
        t("verdict.ok" if budget.is_viable else "verdict.fail"),
        t("q.margin_required", margin=budget.margin_db, required=p.required_margin_db),
    )


def validity_messages(budget: LinkBudgetResult) -> list[str]:
    """Translated notes when the link is outside the model's validity range."""
    from radiocoverage.propagation import get_model

    p = budget.parameters
    model = get_model(budget.model_key, p.frequency_mhz)
    return [
        t("validity.warning", model=model.label, quantity=t(f"validity.{name}"), value=value,
          low=low, high=high, unit=unit)
        for name, value, low, high, unit in model.validity_issues(
            p.distance_km, p.tx_height_m, p.rx_height_m
        )
    ]  # fmt: skip


def link_metrics(path: LinkPath, budget: LinkBudgetResult, wide: bool = False) -> None:
    p = budget.parameters
    if wide:
        c1, c2, c3, c4 = st.columns(4)
    else:
        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)
    c1.metric(t("q.distance"), f"{path.distance_km:.2f} km", border=True,
              help=t("help.metric.distance", azimuth=path.bearing_deg))  # fmt: skip
    c2.metric(t("q.rx_power"), f"{budget.rx_power_dbm:.1f} dBm", border=True,
              help=t("help.metric.rx_power", sensitivity=p.rx_sensitivity_dbm))  # fmt: skip
    c3.metric(
        t("q.margin"), f"{budget.margin_db:.1f} dB",
        delta=f"{budget.margin_db - p.required_margin_db:+.1f} dB",
        border=True, help=t("help.metric.margin", required=p.required_margin_db),
    )  # fmt: skip
    c4.metric(t("q.path_loss"), f"{budget.path_loss_db:.1f} dB", border=True,
              help=budget.model_label)  # fmt: skip


def render_link_results(
    tx: GeoPoint,
    rx: GeoPoint,
    settings: RadioSettings,
    path: LinkPath,
    budget: LinkBudgetResult,
    profile: TerrainProfile | None,
    key: str,
    show_map: bool = False,
) -> None:
    lang = current_language()
    link_verdict(budget)
    link_metrics(path, budget, wide=show_map)
    for warning in validity_messages(budget):
        st.caption(f"⚠️ {warning}")

    names = [t("web.tab.budget"), t("web.tab.profile"), t("web.tab.power"), t("web.tab.export")]
    if show_map:
        names.insert(0, t("web.tab.map"))
    tabs = dict(zip(names, st.tabs(names), strict=True))

    if show_map:
        with tabs[t("web.tab.map")]:
            m = build_link_map(path, budget, settings.band, profile, lang=lang)
            html = m.get_root().render()
            if hasattr(st, "iframe"):
                st.iframe(html, height=520)
            else:  # older Streamlit versions
                import streamlit.components.v1 as components

                components.html(html, height=520)

    rows = link_budget_rows(budget, path, profile, lang)
    with tabs[t("web.tab.budget")]:
        st.dataframe(
            rows,
            hide_index=True,
            width="stretch",
            column_config={
                "section": st.column_config.TextColumn(t("web.col.section"), width=95),
                "item": st.column_config.TextColumn(t("web.col.item"), width="medium"),
                "value": st.column_config.TextColumn(t("web.col.value"), width="medium"),
            },
            height=min(36 * (len(rows) + 1) + 4, 760),
        )

    with tabs[t("web.tab.profile")]:
        if profile is None:
            st.info(t("web.profile.disabled"), icon=":material/terrain:")
        else:
            st.altair_chart(charts.profile_chart(profile, lang), width="stretch")
            edge = profile.edge
            st.caption(
                t(
                    "web.profile.caption",
                    status=t(f"terrain.{profile.status_key}"),
                    clearance=profile.min_clearance_ratio * 100,
                    loss=profile.diffraction_loss_db,
                    edge=float(edge.distance_m) / 1000 if edge is not None else 0.0,
                )
            )

    with tabs[t("web.tab.power")]:
        st.altair_chart(
            charts.power_distance_chart(budget, path.distance_km, lang), width="stretch"
        )
        st.caption(t("web.power.caption"))

    with tabs[t("web.tab.export")]:
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            t("web.download.csv"), budget_csv(rows).encode("utf-8-sig"), "link_budget.csv",
            "text/csv", icon=":material/table_view:", key=f"{key}_csv", width="stretch",
        )  # fmt: skip
        map_html = (
            build_link_map(path, budget, settings.band, profile, lang=lang).get_root().render()
        )
        c2.download_button(
            t("web.download.map"), map_html.encode("utf-8"), "link_map.html", "text/html",
            icon=":material/map:", key=f"{key}_html", width="stretch",
        )  # fmt: skip
        if profile is not None:
            try:
                png = profile_png(tx, rx, settings)
            except TerrainError as exc:  # pragma: no cover - network problem
                st.error(str(exc))
            else:
                c3.download_button(
                    t("web.download.profile"), png, "terrain_profile.png", "image/png",
                    icon=":material/landscape:", key=f"{key}_png", width="stretch",
                )  # fmt: skip
