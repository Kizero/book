# mermaid-docx-to-svg

Extract Mermaid diagrams from a `.docx` file and render each diagram to `.svg`.

## Usage

```bash
python3 mermaid_docx_to_svg.py "your-file.docx" -o svg-output
```

Options:

- `--timeout <seconds>`: render timeout per diagram (default `60`)
- `--renderer local|kroki`: choose render backend (default `local`)

## Notes

- Default renderer uses local Mermaid CLI via `npx @mermaid-js/mermaid-cli`.
- `kroki` renderer is available as an alternative if you prefer HTTP rendering.
- Mermaid extraction supports:
  - fenced blocks: <code>```mermaid ... ```</code>
  - single-paragraph diagram lines starting with `graph`, `flowchart`, `sequenceDiagram`, etc.
