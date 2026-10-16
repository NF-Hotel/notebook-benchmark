# notebook-benchmark

A [marimo](https://marimo.io) notebook that benchmarks locally hosted LLMs (**Ollama** and **LM Studio**) on a real task: interpreting cancellation statistics of a hotel-booking dataset.

Python computes the facts; each model only interprets them. Speed, memory use and answers are compared side by side. **No model is ranked or declared "best".**

| Page | Content |
|---|---|
| [Getting Started](Getting-Started) | Install, start the servers, run the notebook |
| [Using the Notebook](Using-the-Notebook) | The 12 sections and what each shows |
| [Dataset](Dataset) | Expected CSV columns, direct vs agent, column mapping |
| [Methodology](Methodology) | What is measured and how, cold vs warm, caveats |
| [Results Schema](Results-Schema) | Fields of `output/results.jsonl` |
| [Architecture](Architecture) | Layers, components, data flow |
| [Development](Development) | Tests, linting, extending |
| [Troubleshooting](Troubleshooting) | Common problems |
