/**
 * Budget meter — shows step and cost usage as progress bars.
 */

interface Props {
  stepsUsed: number;
  maxSteps: number;
  costUsed: number;
  maxCost: number;
}

export function BudgetMeter({ stepsUsed, maxSteps, costUsed, maxCost }: Props) {
  const stepPct = Math.min((stepsUsed / maxSteps) * 100, 100);
  const costPct = Math.min((costUsed / maxCost) * 100, 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 12,
            marginBottom: 4,
            color: "var(--muted)",
          }}
        >
          <span>Steps</span>
          <span>
            {stepsUsed} / {maxSteps}
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{
              width: `${stepPct}%`,
              background: stepPct > 80 ? "var(--orange)" : "var(--accent)",
            }}
          />
        </div>
      </div>

      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 12,
            marginBottom: 4,
            color: "var(--muted)",
          }}
        >
          <span>Cost</span>
          <span>
            €{costUsed.toFixed(3)} / €{maxCost.toFixed(2)}
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{
              width: `${costPct}%`,
              background: costPct > 80 ? "var(--orange)" : "var(--accent)",
            }}
          />
        </div>
      </div>
    </div>
  );
}
