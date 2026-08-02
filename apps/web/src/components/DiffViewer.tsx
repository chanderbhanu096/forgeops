/**
 * Diff viewer — renders a unified diff with colour-coded lines.
 */

interface Props {
  patch: string;
  maxLines?: number;
}

export function DiffViewer({ patch, maxLines = 200 }: Props) {
  const lines = patch.split("\n").slice(0, maxLines);

  function lineClass(line: string) {
    if (line.startsWith("+") && !line.startsWith("+++")) return "diff-line add";
    if (line.startsWith("-") && !line.startsWith("---")) return "diff-line del";
    if (line.startsWith("@")) return "diff-line meta";
    return "diff-line";
  }

  return (
    <div className="diff">
      {lines.map((line, i) => (
        <div key={i} className={lineClass(line)}>
          {line || "\u00A0"}
        </div>
      ))}
      {patch.split("\n").length > maxLines && (
        <div className="diff-line muted">… {patch.split("\n").length - maxLines} more lines</div>
      )}
    </div>
  );
}
