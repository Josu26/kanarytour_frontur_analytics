import csv
import json
from collections import defaultdict

from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render

TABLE_NAME = "frontur_canarias_monthly"
# Tabla mensual por isla (year, month, island, tourists)
ISLAND_TABLE = "frontur_canarias_islands_monthly"


def _build_where_from_request(request):
    """
    Construye WHERE + params a partir de filtros:
    - residence
    - year_from / year_to
    (island se maneja solo con la tabla de islas, no existe en la tabla principal)
    """
    residence = request.GET.get("residence") or ""
    year_from = request.GET.get("year_from") or ""
    year_to = request.GET.get("year_to") or ""

    where_clauses = []
    params = []

    if year_from:
        where_clauses.append("year >= %s")
        params.append(int(year_from))

    if year_to:
        where_clauses.append("year <= %s")
        params.append(int(year_to))

    if residence:
        where_clauses.append("residence = %s")
        params.append(residence)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    current_filters = {
        "residence": residence or None,
        "year_from": int(year_from) if year_from else None,
        "year_to": int(year_to) if year_to else None,
    }
    return where_sql, params, current_filters


def dashboard_view(request):
    # --------- 1. Filtros del modo analista ---------
    island_filter = request.GET.get("island") or None
    year_a = request.GET.get("year_a") or ""
    year_b = request.GET.get("year_b") or ""
    where_sql, params, current_filters = _build_where_from_request(request)

    # --------- 2. Leer datos limpios de SQLite (tabla principal) ---------
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT year, month, residence, tourists
            FROM {TABLE_NAME}
            {where_sql}
            ORDER BY year, month, residence
            """,
            params,
        )
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    # 2b. Para la tabla detallada limitamos a 500 filas, como tenías
    table_rows = rows[:500]

    # 3. Convertir a lista de diccionarios
    records = [dict(zip(columns, row)) for row in rows]
    total_rows = len(records)

    # 4. KPIs básicos
    date_min = None
    date_max = None
    total_visitors = None

    if records:
        ym_set = {(int(r["year"]), int(r["month"])) for r in records}
        ym_sorted_keys = sorted(ym_set)
        y0, m0 = ym_sorted_keys[0]
        y1, m1 = ym_sorted_keys[-1]
        date_min = f"{y0}-{m0:02d}"
        date_max = f"{y1}-{m1:02d}"
        total_visitors = int(sum(float(r["tourists"]) for r in records))

    # 5. Agregado por año-mes (para gráfico y KPIs avanzados)
    ym_totals = defaultdict(float)
    residence_series = defaultdict(lambda: defaultdict(float))  # por residencia

    for r in records:
        y = int(r["year"])
        m = int(r["month"])
        res = r["residence"]
        val = float(r["tourists"])

        ym_totals[(y, m)] += val
        residence_series[res][(y, m)] += val

    ym_sorted = sorted(ym_totals.items())
    chart_labels = [f"{y}-{m:02d}" for (y, m), _ in ym_sorted]
    chart_values = [int(val) for _, val in ym_sorted]

    # 6. KPIs avanzados: últimos 12 meses vs 12 anteriores
    kpi_last_12m = None
    kpi_prev_12m = None
    kpi_last_12m_growth_pct = None
    last_12_periods = []  # (year, month) de los últimos 12

    if len(ym_sorted) >= 12:
        last_12 = ym_sorted[-12:]
        kpi_last_12m = int(sum(val for _, val in last_12))
        last_12_periods = [key for key, _ in last_12]

    if len(ym_sorted) >= 24:
        prev_12 = ym_sorted[-24:-12]
        kpi_prev_12m = int(sum(val for _, val in prev_12))
        if kpi_prev_12m > 0:
            kpi_last_12m_growth_pct = (
                (kpi_last_12m - kpi_prev_12m) / kpi_prev_12m
            ) * 100

    # 7. Mes pico de turistas
    best_period_label = None
    best_period_value = None
    if ym_sorted:
        (by, bm), bval = max(ym_sorted, key=lambda item: item[1])
        best_period_label = f"{by}-{bm:02d}"
        best_period_value = int(bval)

    # 8. Top países de residencia (Top 5)
    residence_totals = defaultdict(float)
    for r in records:
        residence_totals[r["residence"]] += float(r["tourists"])

    top_residences = sorted(
        residence_totals.items(), key=lambda x: x[1], reverse=True
    )[:5]

    top_residences_list = [
        {"residence": name, "tourists": int(val)} for name, val in top_residences
    ]

    # Dependencia de mercados clave
    main_market_name = None
    main_market_share = None
    top3_share = None
    if total_visitors and top_residences_list:
        main_market = top_residences_list[0]
        main_market_name = main_market["residence"]
        main_market_share = (main_market["tourists"] / total_visitors) * 100

        top3_sum = sum(r["tourists"] for r in top_residences_list[:3])
        top3_share = (top3_sum / total_visitors) * 100

    # 9. Estacionalidad: media por mes (1–12)
    month_totals = defaultdict(float)
    month_counts = defaultdict(int)
    for (y, m), val in ym_totals.items():
        month_totals[m] += val
        month_counts[m] += 1

    season_labels = []
    season_values = []
    for m in range(1, 13):
        if month_counts[m]:
            season_labels.append(f"{m:02d}")
            season_values.append(int(month_totals[m] / month_counts[m]))

    # 10. Impacto COVID: media pre-COVID, mínimo y recuperación
    baseline_avg = None
    covid_min_label = None
    covid_min_val = None
    covid_drop_pct = None
    recovery_month_label = None

    baseline_vals = [val for (y, _), val in ym_totals.items() if y <= 2019]
    if baseline_vals:
        baseline_avg = sum(baseline_vals) / len(baseline_vals)

        (cy, cm), cval = min(ym_totals.items(), key=lambda item: item[1])
        covid_min_label = f"{cy}-{cm:02d}"
        covid_min_val = int(cval)

        if baseline_avg > 0:
            covid_drop_pct = ((cval - baseline_avg) / baseline_avg) * 100
            threshold = 0.9 * baseline_avg
            for (y, m), val in sorted(ym_totals.items()):
                if y >= 2020 and val >= threshold:
                    recovery_month_label = f"{y}-{m:02d}"
                    break

    # 11. Series por residencia para el filtro interactivo
    series_per_residence = {}
    for residence, ymmap in residence_series.items():
        sorted_items = sorted(ymmap.items())
        labels = [f"{y}-{m:02d}" for (y, m), _ in sorted_items]
        values = [int(v) for _, v in sorted_items]
        series_per_residence[residence] = {"labels": labels, "values": values}

    # 12. Métricas por isla basadas en la tabla mensual de islas
    islands_table = []          # para tabla + mapa
    island_labels = []          # nombres para el bar chart
    island_values_pct = []      # % para el bar chart
    island_total_last_12 = None
    main_island_name = None
    main_island_share = None
    top3_islands_share = None

    if last_12_periods:
        (y_start, m_start) = last_12_periods[0]
        (y_end, m_end) = last_12_periods[-1]

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT island, SUM(tourists) AS total_tourists
                    FROM {ISLAND_TABLE}
                    WHERE
                        (year > %s OR (year = %s AND month >= %s))
                        AND
                        (year < %s OR (year = %s AND month <= %s))
                    GROUP BY island
                    ORDER BY total_tourists DESC
                    """,
                    [y_start, y_start, m_start, y_end, y_end, m_end],
                )
                island_rows = cursor.fetchall()
        except Exception:
            island_rows = []

        total_islands_all = sum(float(t or 0.0) for _, t in island_rows)

        if total_islands_all > 0:
            island_total_last_12 = int(total_islands_all)

            for island, total in island_rows:
                total_f = float(total or 0.0)
                share_pct = (total_f / total_islands_all) * 100
                islands_table.append(
                    {
                        "island": island,
                        "tourists_12m": int(total_f),
                        "share_pct": share_pct,
                    }
                )

            # Filtro por isla en modo analista (solo se deja la seleccionada)
            if island_filter:
                islands_table = [
                    i for i in islands_table if i["island"] == island_filter
                ]

            # Ordenar
            islands_table.sort(key=lambda x: x["tourists_12m"], reverse=True)

            island_labels = [i["island"] for i in islands_table]
            island_values_pct = [round(i["share_pct"], 1) for i in islands_table]

            if islands_table:
                main_island_name = islands_table[0]["island"]
                main_island_share = islands_table[0]["share_pct"]
                top3_islands_share = sum(i["share_pct"] for i in islands_table[:3])

    # 13. Años disponibles + comparación año vs año
    years_available = sorted({int(y) for (y, _) in ym_totals.keys()}) if ym_totals else []

    year_compare_a = int(year_a) if year_a.isdigit() else None
    year_compare_b = int(year_b) if year_b.isdigit() else None
    year_compare_delta = None

    if (
        year_compare_a
        and year_compare_b
        and year_compare_a in years_available
        and year_compare_b in years_available
    ):
        total_a = sum(val for (y, _), val in ym_totals.items() if y == year_compare_a)
        total_b = sum(val for (y, _), val in ym_totals.items() if y == year_compare_b)
        if total_b > 0:
            year_compare_delta = ((total_a - total_b) / total_b) * 100

    # 14. Listas para filtros (modo analista)
    available_residences = sorted({r["residence"] for r in records}) if records else []
    available_islands = sorted({i["island"] for i in islands_table}) if islands_table else []

    # Query string actual para anclarlo al botón de descarga
    query_string = request.GET.urlencode()

    # 15. Contexto para la plantilla
    context = {
        "columns": columns,
        "rows": table_rows,
        "records": records,
        "total_rows": total_rows,
        "date_col": "year/month",
        "visitors_col": "tourists",
        "date_min": date_min,
        "date_max": date_max,
        "total_visitors": total_visitors,
        "TABLE_NAME": TABLE_NAME,

        # KPIs avanzados
        "kpi_last_12m": kpi_last_12m,
        "kpi_prev_12m": kpi_prev_12m,
        "kpi_last_12m_growth_pct": kpi_last_12m_growth_pct,
        "best_period_label": best_period_label,
        "best_period_value": best_period_value,

        # Dependencia de mercados
        "main_market_name": main_market_name,
        "main_market_share": main_market_share,
        "top3_share": top3_share,

        # Impacto COVID
        "baseline_avg": int(baseline_avg) if baseline_avg else None,
        "covid_min_label": covid_min_label,
        "covid_min_val": covid_min_val,
        "covid_drop_pct": covid_drop_pct,
        "recovery_month_label": recovery_month_label,

        # Series principales
        "chart_labels": json.dumps(chart_labels),
        "chart_values": json.dumps(chart_values),
        "season_labels": json.dumps(season_labels),
        "season_values": json.dumps(season_values),

        # Series por residencia
        "series_per_residence_json": json.dumps(series_per_residence),

        # Top 5 países
        "top_residences": top_residences_list,

        # ISLAS – tabla, KPIs, barra + mapa
        "islands_table": islands_table,
        "islands_total_12m": island_total_last_12,
        "islands_top3_share": top3_islands_share,
        "island_labels_json": json.dumps(island_labels),
        "island_shares_json": json.dumps(island_values_pct),
        "islands_map_json": json.dumps(islands_table),
        "island_leader_name": main_island_name,
        "island_leader_share": main_island_share,

        # Compatibilidad antigua (no los usas en HTML, pero los dejo)
        "island_shares": islands_table,
        "island_total_last_12": island_total_last_12,
        "main_island_name_old": main_island_name,
        "main_island_share_old": main_island_share,
        "top3_islands_share_old": top3_islands_share,
        "island_values_pct_json": json.dumps(island_values_pct),

        # Filtros modo analista
        "available_residences": available_residences,
        "available_islands": available_islands,
        "current_residence": current_filters["residence"],
        "current_island": island_filter,
        "current_year_from": current_filters["year_from"],
        "current_year_to": current_filters["year_to"],
        "years_available": years_available,
        "year_compare_a": year_compare_a,
        "year_compare_b": year_compare_b,
        "year_compare_delta": year_compare_delta,

        # Query string para el botón de descarga
        "query_string": query_string,
    }

    return render(request, "analytics/dashboard.html", context)


def download_clean_csv(request):
    """
    Descarga el dataset limpio principal en CSV usando los mismos filtros
    (residence + rango de años). Island no se aplica aquí porque la tabla
    principal no tiene columna island.
    """
    where_sql, params, _ = _build_where_from_request(request)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT year, month, residence, tourists
            FROM {TABLE_NAME}
            {where_sql}
            ORDER BY year, month, residence
            """,
            params,
        )
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="frontur_canarias_clean.csv"'

    writer = csv.writer(response)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)

    return response
