/**
 * Skills registry page — browse registered skill definitions.
 */
"use client";

import { useState, useEffect } from "react";
import { listSkills } from "@/lib/api";
import type { Skill } from "@/types";

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listSkills()
      .then(setSkills)
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="page-header">
        <h1>Skill Registry</h1>
        <p>Versioned, permission-scoped capabilities available to the agent runtime.</p>
      </div>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
          {skills.map((skill) => (
            <div key={skill.name} className="card" style={{ marginBottom: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                <h3 style={{ marginBottom: 0, fontFamily: "var(--mono)", fontSize: 13 }}>
                  {skill.name}
                </h3>
                <span className="badge" style={{ fontSize: 10 }}>v{skill.version}</span>
              </div>
              <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>
                {skill.description}
              </p>
              {skill.required_tools.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".05em", color: "var(--muted)", marginBottom: 4 }}>
                    Required tools
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {skill.required_tools.map((t) => (
                      <code key={t} style={{ fontSize: 11, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 3, padding: "1px 6px" }}>
                        {t}
                      </code>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
