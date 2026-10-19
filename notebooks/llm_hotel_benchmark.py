import marimo

__generated_with = "0.25.0"
app = marimo.App(width="full", app_title="Local LLM Hotel Benchmark")


@app.cell
def _():
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import polars as pl

    from nfbench import bootstrap
    from nfbench.adapters.datasets import discover_csvs, load_dataset
    from nfbench.adapters.hotel_analysis import analyse
    from nfbench.application.benchmark import HotelInput, ModelSelection
    from nfbench.application.response_parsing import validate_hotel_response
    from nfbench.domain.errors import DatasetError
    from nfbench.domain.models import BenchmarkConfig, ColumnMapping
    from nfbench.domain.tasks import TASKS

    store = bootstrap.build_store()
    backends = bootstrap.build_backends()
    return (
        BenchmarkConfig,
        ColumnMapping,
        DatasetError,
        HotelInput,
        ModelSelection,
        Path,
        TASKS,
        alt,
        analyse,
        backends,
        bootstrap,
        discover_csvs,
        load_dataset,
        mo,
        pl,
        store,
        validate_hotel_response,
    )


@app.cell
def _(mo):
    version, set_version = mo.state(0)
    mo.md("""
    # Local LLM Hotel Benchmark
    Compare local models (Ollama, LM Studio) on a hotel-booking cancellation analysis.
    Python calculates the statistics; the models only interpret them.
    Methodology: `BENCHMARK_METHODOLOGY.md`.
    """)
    return set_version, version


@app.cell
def _(mo):
    refresh = mo.ui.refresh(label="Re-check backends")
    mo.vstack([mo.md("## 1. Environment / backend status"), refresh])
    return (refresh,)


@app.cell
def _(backends, mo, refresh):
    refresh  # re-run on click
    statuses = {name: backend.check() for name, backend in backends.items()}
    rows = [
        {
            "backend": s.name,
            "url": s.base_url,
            "status": "available" if s.available else "UNAVAILABLE",
            "models": len(s.models),
            "detail": s.error or "",
        }
        for s in statuses.values()
    ]
    _down = [s.name for s in statuses.values() if not s.available]
    mo.vstack(
        [
            mo.ui.table(rows, selection=None),
            mo.callout(
                mo.md(
                    f"Unavailable: **{', '.join(_down)}**. Start it and press *Re-check backends*; "
                    "the other backends keep working."
                ),
                kind="warn",
            )
            if _down
            else mo.md(""),
        ]
    )
    return (statuses,)


@app.cell
def _(Path, bootstrap, discover_csvs, mo, statuses):
    _csvs = discover_csvs(bootstrap.DATA_DIR)
    csv_options = {str(p.relative_to(bootstrap.DATA_DIR)): str(p) for p in _csvs}
    csv_choice = mo.ui.dropdown(
        csv_options, value=next(iter(csv_options), None), label="CSV in data/", full_width=True
    )
    custom_path = mo.ui.text(
        placeholder="or paste a full path to a CSV", label="Other file", full_width=True
    )
    col_canceled = mo.ui.text("is_canceled", label="Cancellation column")
    col_agent = mo.ui.text("agent", label="Agent column (empty/NULL = direct)")
    col_categorical = mo.ui.text(
        "hotel, market_segment, distribution_channel, deposit_type, customer_type",
        label="Categorical columns to break down",
        full_width=True,
    )

    model_pickers = mo.ui.dictionary(
        {
            name: mo.ui.multiselect(list(s.models), label=f"{name} models", full_width=True)
            for name, s in statuses.items()
            if s.available
        }
    )
    temperature = mo.ui.number(0.0, 2.0, 0.1, value=0.0, label="Temperature")
    max_tokens = mo.ui.number(64, 32768, 64, value=8192, label="Max output tokens")
    runs = mo.ui.slider(1, 10, value=1, label="Runs per model", show_value=True)
    include_hotel = mo.ui.checkbox(True, label="Hotel cancellation analysis")
    include_tasks = mo.ui.checkbox(False, label="Deterministic tasks (pass/fail)")
    run_button = mo.ui.run_button(label="Run benchmark", kind="success")

    mo.vstack(
        [
            mo.md("## 2. Dataset selection"),
            mo.md("Files below `data/` are listed (`data/README.md` describes the columns)."),
            csv_choice,
            custom_path,
            mo.accordion({"Column mapping": mo.vstack([col_canceled, col_agent, col_categorical])}),
            mo.md("## 3. Model selection"),
            mo.vstack(list(model_pickers.values()))
            if len(model_pickers)
            else mo.callout(
                "No backend is available, so no models can be selected.", kind="danger"
            ),
            mo.md("## 4. Benchmark configuration"),
            mo.hstack([temperature, max_tokens, runs], justify="start", gap=2),
            mo.hstack([include_hotel, include_tasks], justify="start", gap=2),
            run_button,
        ]
    )
    return (
        col_agent,
        col_canceled,
        col_categorical,
        csv_choice,
        custom_path,
        include_hotel,
        include_tasks,
        max_tokens,
        model_pickers,
        run_button,
        runs,
        temperature,
    )


@app.cell
def _(
    ColumnMapping,
    DatasetError,
    Path,
    analyse,
    col_agent,
    col_canceled,
    col_categorical,
    csv_choice,
    custom_path,
    load_dataset,
    mo,
):
    dataset = None
    summary = None
    _path = custom_path.value.strip() or csv_choice.value
    _error = None
    if not _path:
        _error = "No CSV selected. Put a CSV in data/ or paste a path."
    else:
        _mapping = ColumnMapping(
            canceled=col_canceled.value.strip(),
            agent=col_agent.value.strip(),
            categorical=tuple(c.strip() for c in col_categorical.value.split(",") if c.strip()),
        )
        try:
            dataset = load_dataset(Path(_path), _mapping)
            summary = analyse(dataset.frame, dataset.mapping)
        except DatasetError as exc:
            _error = str(exc)
    mo.callout(mo.md(f"**Dataset problem:** {_error}"), kind="danger") if _error else mo.md("")
    return dataset, summary


@app.cell
def _(dataset, mo, pl):
    mo.stop(dataset is None, mo.md("_Select a valid dataset to continue._"))
    _info = dataset.info
    _schema = pl.DataFrame(
        {
            "column": list(_info.columns),
            "type": [_info.dtypes[c] for c in _info.columns],
            "missing": [_info.missing[c] for c in _info.columns],
        }
    )
    mo.vstack(
        [
            mo.md("## 5. Dataset overview"),
            mo.hstack(
                [
                    mo.stat(_info.name, label="File", bordered=True),
                    mo.stat(f"{_info.rows:,}", label="Rows", bordered=True),
                    mo.stat(f"{len(_info.columns)}", label="Columns", bordered=True),
                    mo.stat(_info.sha256[:12], label="SHA-256 (prefix)", bordered=True),
                ],
                wrap=True,
            ),
            mo.md("**Columns, types and missing values**"),
            mo.ui.table(_schema, selection=None, page_size=8),
            mo.md("**Sample**"),
            mo.ui.table(dataset.frame.head(10), selection=None),
        ]
    )


@app.cell
def _(
    BenchmarkConfig,
    HotelInput,
    ModelSelection,
    TASKS,
    bootstrap,
    dataset,
    include_hotel,
    include_tasks,
    max_tokens,
    mo,
    model_pickers,
    run_button,
    runs,
    set_version,
    store,
    summary,
    temperature,
):
    mo.stop(
        not run_button.value,
        mo.md("## 6. Benchmark execution\n_Configure above, then press **Run benchmark**._"),
    )
    _selections = [
        ModelSelection(backend, model)
        for backend, picker in model_pickers.value.items()
        for model in picker
    ]
    _use_hotel = include_hotel.value and dataset is not None and summary is not None
    _problems = []
    if not _selections:
        _problems.append("select at least one model")
    if not (_use_hotel or include_tasks.value):
        _problems.append(
            "enable the hotel analysis (needs a valid dataset) or the deterministic tasks"
        )
    mo.stop(bool(_problems), mo.callout(mo.md("Cannot run: " + "; ".join(_problems)), kind="warn"))

    _config = BenchmarkConfig(
        temperature=float(temperature.value),
        max_tokens=int(max_tokens.value),
        runs=int(runs.value),
        hotel_analysis=_use_hotel,
        deterministic_tasks=include_tasks.value,
    )
    _jobs = (
        len(_selections)
        * _config.runs
        * (int(_use_hotel) + (len(TASKS) if include_tasks.value else 0))
    )
    _hotel = HotelInput(dataset.info, summary) if _use_hotel else None
    with mo.status.progress_bar(total=_jobs, title="Starting", remove_on_exit=False) as _bar:

        def _progress(done: int, total: int, label: str) -> None:
            _bar.update(title=label, increment=1 if done else 0)

        last_run = bootstrap.build_controller(store).run(_selections, _config, _hotel, _progress)
    set_version(lambda v: v + 1)
    _errors = [r for r in last_run if r.error]
    mo.vstack(
        [
            mo.md("## 6. Benchmark execution"),
            mo.md(f"Finished **{len(last_run)}** requests, appended to `{store.path.name}`."),
            mo.callout(mo.md(f"{len(_errors)} request(s) failed; see *Raw results*."), kind="warn")
            if _errors
            else mo.md(""),
        ]
    )
    return (last_run,)


@app.cell
def _(mo, pl, store, version):
    version()  # reload after each run
    all_results = store.load_frame()
    mo.stop(
        all_results.is_empty(),
        mo.md("## 7. Performance results\n_No results yet. Run a benchmark._"),
    )
    _sessions = (
        all_results.select("session_id", "timestamp")
        .drop_nulls("session_id")
        .group_by("session_id", maintain_order=True)
        .agg(pl.col("timestamp").first())
    )
    _labels = {f"{row[1] or 'legacy'}  ({row[0]})": row[0] for row in reversed(_sessions.rows())}
    session_pick = mo.ui.dropdown(
        {"All results": "", **_labels},
        value=next(iter(_labels), "All results"),
        label="Result set",
        full_width=True,
    )
    type_pick = mo.ui.dropdown(
        {
            "Hotel analysis": "hotel_cancellation",
            "Deterministic tasks": "deterministic_task",
            "Both": "",
        },
        value="Hotel analysis",
        label="Workload",
    )
    mo.vstack(
        [
            mo.md("## 7. Performance results"),
            mo.hstack([session_pick, type_pick], justify="start", gap=2),
        ]
    )
    return all_results, session_pick, type_pick


@app.cell
def _(all_results, mo, pl, session_pick, type_pick):
    _view = all_results
    if session_pick.value:
        _view = _view.filter(pl.col("session_id") == session_pick.value)
    if type_pick.value:
        _view = _view.filter(pl.col("analysis_type") == type_pick.value)
    mo.stop(_view.is_empty(), mo.md("_No results for this selection._"))
    view = _view.with_columns(
        (pl.col("model") + " (" + pl.col("backend") + ")").alias("label"),
        pl.when(pl.col("cold").is_null())
        .then(pl.lit("unknown"))  # legacy v1 rows carry no cold/warm information
        .when(pl.col("cold"))
        .then(pl.lit("cold"))
        .otherwise(pl.lit("warm"))
        .alias("phase"),
    )
    ok = view.filter(pl.col("error").is_null())
    return ok, view


@app.cell
def _(alt, mo, ok, pl):
    mo.stop(
        ok.is_empty(),
        mo.callout("Every request in this selection failed; see Raw results.", kind="danger"),
    )
    _long = ok.select("label", "phase", "ttft_s", "total_s", "completion_tokens", "tokens_per_s")
    _agg = (
        _long.group_by("label", "phase")
        .agg(
            pl.col("ttft_s").mean().alias("TTFT (s)"),
            pl.col("total_s").mean().alias("Total time (s)"),
            pl.col("completion_tokens").mean().alias("Completion tokens"),
            pl.col("tokens_per_s").mean().alias("Tokens/s"),
            pl.len().alias("requests"),
        )
        .sort("label", "phase")
    )

    def _chart(metric: str, better: str):
        return (
            alt.Chart(_agg)
            .mark_bar()
            .encode(
                y=alt.Y("label:N", title=None, axis=alt.Axis(labelLimit=260)),
                yOffset="phase:N",
                x=alt.X(f"{metric}:Q", title=f"{metric} ({better})"),
                color=alt.Color(
                    "phase:N",
                    scale=alt.Scale(
                        domain=["cold", "warm", "unknown"], range=["#e07a5f", "#3d85c6", "#999999"]
                    ),
                ),
                tooltip=["label", "phase", alt.Tooltip(f"{metric}:Q", format=".2f"), "requests"],
            )
            .properties(width=420, height=max(120, 46 * ok["label"].n_unique()))
        )

    mo.vstack(
        [
            mo.md(
                "Cold = first request of a model in its session (may include model loading); warm = later requests."
            ),
            mo.ui.table(_agg.with_columns(pl.selectors.float().round(2)), selection=None),
            mo.hstack(
                [
                    _chart("TTFT (s)", "lower is faster"),
                    _chart("Total time (s)", "lower is faster"),
                ],
                wrap=True,
            ),
            _chart("Tokens/s", "higher is faster"),
        ]
    )


@app.cell
def _(alt, mo, ok, pl):
    _graded = ok.filter(pl.col("passed").is_not_null())
    mo.stop(_graded.is_empty())
    _data = _graded.with_columns(
        pl.when(pl.col("passed")).then(pl.lit("pass")).otherwise(pl.lit("fail")).alias("result")
    )
    mo.vstack(
        [
            mo.md("**Deterministic task outcomes**"),
            alt.Chart(_data)
            .mark_rect(stroke="white")
            .encode(
                x=alt.X("task_id:N", title=None),
                y=alt.Y("label:N", title=None),
                color=alt.Color(
                    "result:N",
                    scale=alt.Scale(domain=["pass", "fail"], range=["#2e9e5b", "#d64545"]),
                ),
                tooltip=["label", "task_id", "result", "run"],
            )
            .properties(width=420, height=max(100, 30 * _data["label"].n_unique())),
        ]
    )


@app.cell
def _(alt, dataset, mo, pl, summary):
    mo.stop(summary is None)
    _pct = lambda s: "n/a" if s.rate is None else f"{s.rate:.1%}"  # noqa: E731
    _groups = pl.DataFrame(
        {
            "group": ["Overall", "Direct customers", "Agent bookings"],
            "bookings": [summary.overall.bookings, summary.direct.bookings, summary.agent.bookings],
            "cancellations": [
                summary.overall.cancellations,
                summary.direct.cancellations,
                summary.agent.cancellations,
            ],
            "rate": [summary.overall.rate, summary.direct.rate, summary.agent.rate],
        }
    )
    _rate_chart = (
        alt.Chart(_groups)
        .mark_bar()
        .encode(
            x=alt.X("group:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("rate:Q", title="Cancellation rate", axis=alt.Axis(format="%")),
            color=alt.Color("group:N", legend=None),
            tooltip=["group", "bookings", "cancellations", alt.Tooltip("rate:Q", format=".1%")],
        )
        .properties(width=320, height=240, title="Cancellation rate: overall vs direct vs agent")
    )

    dim_picker = mo.ui.dropdown(
        [b.dimension for b in summary.breakdowns] or ["(none)"],
        value=(summary.breakdowns[0].dimension if summary.breakdowns else "(none)"),
        label="Breakdown by",
    )
    mo.vstack(
        [
            mo.md("## 8. Hotel cancellation analysis (calculated by Python)"),
            mo.hstack(
                [
                    mo.stat(
                        _pct(summary.overall),
                        label="Overall",
                        caption=f"{summary.overall.cancellations:,} of {summary.overall.bookings:,}",
                        bordered=True,
                    ),
                    mo.stat(
                        _pct(summary.direct),
                        label="Direct customers",
                        caption=f"{summary.direct.cancellations:,} of {summary.direct.bookings:,}",
                        bordered=True,
                    ),
                    mo.stat(
                        _pct(summary.agent),
                        label="Agent bookings",
                        caption=f"{summary.agent.cancellations:,} of {summary.agent.bookings:,}",
                        bordered=True,
                    ),
                ],
                wrap=True,
            ),
            _rate_chart,
            dim_picker,
        ]
    )
    return (dim_picker,)


@app.cell
def _(alt, dim_picker, mo, pl, summary):
    mo.stop(summary is None or not summary.breakdowns)
    _bd = next(b for b in summary.breakdowns if b.dimension == dim_picker.value)
    _frame = pl.DataFrame(
        {
            "value": [r.value for r in _bd.rows],
            "bookings": [r.stats.bookings for r in _bd.rows],
            "cancellations": [r.stats.cancellations for r in _bd.rows],
            "rate": [r.stats.rate for r in _bd.rows],
        }
    )
    _chart = (
        alt.Chart(_frame)
        .mark_bar()
        .encode(
            y=alt.Y("value:N", sort=[r.value for r in _bd.rows], title=None),
            x=alt.X("rate:Q", title="Cancellation rate", axis=alt.Axis(format="%")),
            tooltip=["value", "bookings", "cancellations", alt.Tooltip("rate:Q", format=".1%")],
        )
        .properties(width=520, height=max(120, 28 * len(_frame)), title=f"By {_bd.dimension}")
    )
    mo.vstack(
        [
            _chart,
            mo.md(f"_{_bd.omitted_groups} smaller groups omitted._")
            if _bd.omitted_groups
            else mo.md(""),
            mo.md("**Notes:** " + "; ".join(summary.notes)) if summary.notes else mo.md(""),
            mo.md("_Differences here are associations in the data, not proof of cause._"),
        ]
    )


@app.cell
def _(mo, ok, pl, validate_hotel_response):
    _hotel = ok.filter(pl.col("analysis_type") == "hotel_cancellation")
    mo.stop(
        _hotel.is_empty(),
        mo.md("## 9. LLM analysis comparison\n_No hotel-analysis results in this selection._"),
    )
    hotel_rows = _hotel.with_row_index("row_id").with_columns(
        pl.format("{} · run {} · {}", pl.col("label"), pl.col("run") + 1, pl.col("phase")).alias(
            "choice"
        )
    )
    _table = hotel_rows.select(
        pl.col("model").alias("Model"),
        pl.col("backend").alias("Backend"),
        pl.col("phase").alias("Phase"),
        pl.col("ttft_s").round(2).alias("TTFT (s)"),
        pl.col("total_s").round(2).alias("Total time (s)"),
        pl.col("completion_tokens").alias("Tokens"),
        pl.col("tokens_per_s").round(1).alias("Tokens/s"),
        pl.col("system_ram_peak_mb").round(0).alias("RAM peak (MB)"),
        pl.col("gpu_vram_peak_mb").round(0).alias("VRAM peak (MB)"),
        pl.col("response_valid").alias("Valid JSON"),
        pl.col("finish_reason").alias("Finish reason"),
    )
    _choices = hotel_rows["choice"].to_list()
    response_pick = mo.ui.multiselect(
        _choices, value=_choices[-3:], label="Responses to compare", full_width=True
    )
    mo.vstack(
        [
            mo.md("## 9. LLM analysis comparison"),
            mo.md(
                "No model is ranked. *Valid JSON* only says the answer had the requested structure."
            ),
            mo.ui.table(_table, selection=None),
            response_pick,
        ]
    )
    return hotel_rows, response_pick


@app.cell
def _(hotel_rows, mo, pl, response_pick, summary, validate_hotel_response):
    mo.stop(not response_pick.value)

    def _pct(x):
        return "n/a" if x is None else f"{x:.1%}"

    def _card(row: dict) -> object:
        _v = validate_hotel_response(row["output"])
        _head = (
            f"**{row['model']}** ({row['backend']}) - {row['phase']}, run {row['run'] + 1}\n\n"
            f"TTFT {row['ttft_s']:.2f}s · total {row['total_s']:.2f}s · "
            f"{row['completion_tokens']} tokens · "
            f"{'n/a' if row['tokens_per_s'] is None else format(row['tokens_per_s'], '.1f')} tok/s"
        )
        if not _v.valid or _v.data is None:
            return mo.vstack(
                [
                    mo.md(_head),
                    mo.callout(mo.md(f"Invalid response: {_v.error}"), kind="danger"),
                    mo.accordion({"Raw response": mo.md(f"```\n{row['output'][:6000]}\n```")}),
                ]
            )
        _d = _v.data
        _ref = (
            {
                "overall_cancellation": summary.overall,
                "direct_customers": summary.direct,
                "agent_bookings": summary.agent,
            }
            if summary
            else {}
        )
        _rates = "\n".join(
            f"| {name.replace('_', ' ')} | {_pct(_d[name]['rate'])} | "
            f"{_pct(_ref[name].rate) if name in _ref else 'n/a'} |"
            for name in ("overall_cancellation", "direct_customers", "agent_bookings")
        )
        _findings = "\n".join(f"- {f}" for f in _d["key_findings"])
        _limits = "\n".join(f"- {f}" for f in _d["limitations"])
        return mo.vstack(
            [
                mo.md(_head),
                mo.md(f"**Summary**\n\n{_d['summary']}"),
                mo.md("| | model says | calculated |\n|---|---|---|\n" + _rates),
                mo.md(f"**Key findings**\n\n{_findings}"),
                mo.md(f"**Limitations**\n\n{_limits}"),
                mo.accordion(
                    {
                        "Interpretations": mo.md(
                            "\n\n".join(
                                f"**{n.replace('_', ' ')}:** {_d[n]['interpretation']}"
                                for n in (
                                    "overall_cancellation",
                                    "direct_customers",
                                    "agent_bookings",
                                )
                            )
                        )
                    }
                ),
            ]
        )

    _chosen = hotel_rows.filter(pl.col("choice").is_in(response_pick.value)).sort("row_id")
    mo.hstack([_card(r) for r in _chosen.iter_rows(named=True)], align="start", gap=2, wrap=True)


@app.cell
def _(alt, mo, ok, pl):
    mo.stop(ok.is_empty())
    _measures = {"before": "before", "after": "after", "peak": "peak"}

    def _long(prefix: str, kind: str) -> pl.DataFrame:
        return pl.concat(
            [
                ok.select(
                    "label",
                    pl.lit(kind).alias("resource"),
                    pl.lit(m).alias("moment"),
                    pl.col(f"{prefix}_{m}_mb").cast(pl.Float64).alias("mb"),
                )
                for m in _measures
            ]
        ).drop_nulls("mb")

    _ram = _long("system_ram", "System RAM")
    _vram = _long("gpu_vram", "GPU VRAM")

    def _chart(data: pl.DataFrame, title: str):
        _agg = data.group_by("label", "moment").agg(pl.col("mb").mean()).sort("label")
        return (
            alt.Chart(_agg)
            .mark_bar()
            .encode(
                y=alt.Y("label:N", title=None, axis=alt.Axis(labelLimit=260)),
                yOffset="moment:N",
                x=alt.X("mb:Q", title="MB (mean)"),
                color=alt.Color("moment:N", sort=["before", "after", "peak"]),
                tooltip=["label", "moment", alt.Tooltip("mb:Q", format=",.0f")],
            )
            .properties(title=title, width=420, height=max(120, 60 * data["label"].n_unique()))
        )

    mo.vstack(
        [
            mo.md("## 10. Resource usage"),
            mo.md(
                "RAM is **system-wide** used memory and VRAM is total `nvidia-smi` memory in use, sampled every ~0.25 s. "
                "They include everything running on the machine, not only the model."
            ),
            _chart(_ram, "System RAM")
            if not _ram.is_empty()
            else mo.callout("System RAM: unavailable", kind="warn"),
            _chart(_vram, "GPU VRAM")
            if not _vram.is_empty()
            else mo.callout(
                "GPU VRAM: unavailable (no NVIDIA GPU or nvidia-smi not found)", kind="warn"
            ),
        ]
    )


@app.cell
def _(mo, view):
    mo.vstack(
        [
            mo.md("## 11. Raw results"),
            mo.ui.table(view.drop("label", "phase"), selection=None, page_size=10),
        ]
    )


@app.cell
def _(mo, view):
    _export = view.drop("label", "phase")
    mo.vstack(
        [
            mo.md(
                "## 12. Export\nExports the rows of the current selection. All results remain in `output/results.jsonl`."
            ),
            mo.hstack(
                [
                    mo.download(
                        data=_export.write_csv().encode(),
                        filename="benchmark_results.csv",
                        mimetype="text/csv",
                        label="Download CSV",
                    ),
                    mo.download(
                        data=_export.write_json().encode(),
                        filename="benchmark_results.json",
                        mimetype="application/json",
                        label="Download JSON",
                    ),
                ],
                justify="start",
            ),
        ]
    )


if __name__ == "__main__":
    app.run()
