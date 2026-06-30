import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as echarts from "echarts";
import { invoke, view } from "@forge/bridge";


// ─── Palette ────────────────────────────────────────────────────────────────
const COLOR = {
  health:   "#4C9BE8",   // blue
  coverage: "#27AE60",   // green
  critical: "#E74C3C",   // red
  high:     "#E67E22",   // orange
  medium:   "#F1C40F",   // yellow
};


// ─── Helper: initialise (or re-use) an ECharts instance ─────────────────────
function initChart(el) {
  return echarts.getInstanceByDom(el) || echarts.init(el, null, {
    width:  el.offsetWidth  || 700,
    height: el.offsetHeight || 280,
  });
}


// ─── Chart components ────────────────────────────────────────────────────────

function HealthChart({ dates, values }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = initChart(ref.current);
    chart.setOption({
      title:   { text: "Code Health", subtext: "CodeScene · 0–10 (higher is better)", left: "center" },
      tooltip: { trigger: "axis" },
      xAxis:   { type: "category", data: dates, boundaryGap: false },
      yAxis:   { type: "value", min: 0, max: 10 },
      series:  [{
        name: "Health", type: "line", smooth: true,
        data: values, symbol: "circle", symbolSize: 6,
        lineStyle: { color: COLOR.health, width: 2 },
        itemStyle: { color: COLOR.health },
        areaStyle: { color: COLOR.health + "22" },
      }],
      grid: { top: 70, bottom: 30, left: "8%", right: "4%", containLabel: true },
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [dates, values]);

  return <div ref={ref} style={{ width: "100%", height: "280px" }} />;
}


function CoverageChart({ dates, values }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = initChart(ref.current);
    chart.setOption({
      title:   { text: "Test Coverage", subtext: "CodeScene · % (higher is better)", left: "center" },
      tooltip: { trigger: "axis", valueFormatter: v => v + "%" },
      xAxis:   { type: "category", data: dates, boundaryGap: false },
      yAxis:   { type: "value", min: 0, max: 100, axisLabel: { formatter: "{value}%" } },
      series:  [{
        name: "Coverage", type: "line", smooth: true,
        data: values, symbol: "circle", symbolSize: 6,
        lineStyle: { color: COLOR.coverage, width: 2 },
        itemStyle: { color: COLOR.coverage },
        areaStyle: { color: COLOR.coverage + "22" },
      }],
      grid: { top: 70, bottom: 30, left: "8%", right: "4%", containLabel: true },
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [dates, values]);

  return <div ref={ref} style={{ width: "100%", height: "280px" }} />;
}


function SnykChart({ dates, critical, high, medium }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = initChart(ref.current);
    chart.setOption({
      title:   { text: "Snyk Vulnerabilities", subtext: "lower is better", left: "center" },
      tooltip: { trigger: "axis" },
      legend:  { bottom: 0, data: ["Critical", "High", "Medium"] },
      xAxis:   { type: "category", data: dates, boundaryGap: false },
      yAxis:   { type: "value", minInterval: 1 },
      series:  [
        {
          name: "Critical", type: "line", smooth: true,
          data: critical, symbol: "circle", symbolSize: 6,
          lineStyle: { color: COLOR.critical, width: 2 },
          itemStyle: { color: COLOR.critical },
        },
        {
          name: "High", type: "line", smooth: true,
          data: high, symbol: "circle", symbolSize: 6,
          lineStyle: { color: COLOR.high, width: 2 },
          itemStyle: { color: COLOR.high },
        },
        {
          name: "Medium", type: "line", smooth: true,
          data: medium, symbol: "circle", symbolSize: 6,
          lineStyle: { color: COLOR.medium, width: 2 },
          itemStyle: { color: COLOR.medium },
        },
      ],
      grid: { top: 70, bottom: 50, left: "8%", right: "4%", containLabel: true },
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [dates, critical, high, medium]);

  return <div ref={ref} style={{ width: "100%", height: "300px" }} />;
}


// ─── Summary badge ───────────────────────────────────────────────────────────
function Badge({ label, value, color, unit = "" }) {
  return (
    <div style={{
      display: "inline-block", padding: "10px 18px", margin: "0 8px 8px 0",
      borderRadius: "8px", background: color + "18", border: `1px solid ${color}44`,
      textAlign: "center", minWidth: "90px",
    }}>
      <div style={{ fontSize: "22px", fontWeight: "700", color }}>{value}{unit}</div>
      <div style={{ fontSize: "11px", color: "#666", marginTop: "2px" }}>{label}</div>
    </div>
  );
}


// ─── Per-repo detail table ───────────────────────────────────────────────────
function RepoTable({ repos }) {
  if (!repos || repos.length === 0) return null;

  const th = { padding: "8px 12px", textAlign: "left", fontSize: "12px",
               fontWeight: "600", color: "#6B778C", borderBottom: "2px solid #e0e0e0" };
  const td = { padding: "8px 12px", fontSize: "13px", borderBottom: "1px solid #f0f0f0" };

  return (
    <div style={{ ...cardStyle, marginTop: "16px", overflowX: "auto" }}>
      <div style={{ fontWeight: "600", fontSize: "13px", color: "#172B4D", marginBottom: "10px" }}>
        Repos breakdown
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={th}>Repository</th>
            <th style={{ ...th, textAlign: "right" }}>Health</th>
            <th style={{ ...th, textAlign: "right" }}>Coverage</th>
            <th style={{ ...th, textAlign: "right", color: COLOR.critical }}>Critical</th>
            <th style={{ ...th, textAlign: "right", color: COLOR.high }}>High</th>
            <th style={{ ...th, textAlign: "right", color: COLOR.medium }}>Medium</th>
          </tr>
        </thead>
        <tbody>
          {repos.map(repo => (
            <tr key={repo.name}>
              <td style={{ ...td, fontFamily: "monospace", fontSize: "12px" }}>{repo.name}</td>
              <td style={{ ...td, textAlign: "right", color: COLOR.health, fontWeight: "600" }}>
                {repo.codescene.health}
              </td>
              <td style={{ ...td, textAlign: "right", color: COLOR.coverage, fontWeight: "600" }}>
                {repo.codescene.coverage}%
              </td>
              <td style={{ ...td, textAlign: "right", color: COLOR.critical, fontWeight: "600" }}>
                {repo.snyk.critical}
              </td>
              <td style={{ ...td, textAlign: "right", color: COLOR.high, fontWeight: "600" }}>
                {repo.snyk.high}
              </td>
              <td style={{ ...td, textAlign: "right", color: COLOR.medium, fontWeight: "600" }}>
                {repo.snyk.medium}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


// ─── Single pod panel ────────────────────────────────────────────────────────
function PodPanel({ podName, series, latestPod }) {
  const { dates, codescene, snyk } = series;
  const last = i => Array.isArray(i) && i.length ? i[i.length - 1] : "—";

  return (
    <div style={{ padding: "0 4px" }}>

      {/* Summary badges (pod-level aggregates) */}
      <div style={{ marginBottom: "20px" }}>
        <Badge label="Health"    value={last(codescene.health)}   color={COLOR.health}   />
        <Badge label="Coverage"  value={last(codescene.coverage)} color={COLOR.coverage} unit="%" />
        <Badge label="Critical"  value={last(snyk.critical)}      color={COLOR.critical} />
        <Badge label="High"      value={last(snyk.high)}          color={COLOR.high}     />
        <Badge label="Medium"    value={last(snyk.medium)}        color={COLOR.medium}   />
      </div>

      {/* Trend charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
        <div style={cardStyle}>
          <HealthChart   dates={dates} values={codescene.health}   />
        </div>
        <div style={cardStyle}>
          <CoverageChart dates={dates} values={codescene.coverage} />
        </div>
      </div>

      <div style={cardStyle}>
        <SnykChart
          dates={dates}
          critical={snyk.critical}
          high={snyk.high}
          medium={snyk.medium}
        />
      </div>

      {/* Per-repo table from latest snapshot */}
      {latestPod && <RepoTable repos={latestPod.repos} />}

    </div>
  );
}

const cardStyle = {
  background: "#fff",
  borderRadius: "8px",
  border: "1px solid #e8e8e8",
  padding: "12px",
  boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
};


// ─── Tab bar ─────────────────────────────────────────────────────────────────
function TabBar({ pods, active, onSelect }) {
  return (
    <div style={{ display: "flex", borderBottom: "2px solid #e0e0e0", marginBottom: "20px" }}>
      {pods.map(pod => (
        <button
          key={pod}
          onClick={() => onSelect(pod)}
          style={{
            padding: "10px 20px",
            border: "none",
            borderBottom: active === pod ? "2px solid #0052CC" : "2px solid transparent",
            marginBottom: "-2px",
            background: "none",
            cursor: "pointer",
            fontWeight: active === pod ? "700" : "400",
            color: active === pod ? "#0052CC" : "#555",
            fontSize: "14px",
          }}
        >
          {pod}
        </button>
      ))}
    </div>
  );
}


// ─── Root Dashboard ──────────────────────────────────────────────────────────
function Dashboard() {
  const [history, setHistory]     = useState(null);
  const [latest, setLatest]       = useState(null);
  const [activeTab, setActiveTab] = useState(null);
  const [error, setError]         = useState(null);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    async function load() {
      try {
        // Fetch both history (for charts) and latest (for repo table) in parallel.
        const [histData, latestData] = await Promise.all([
          invoke("getHistory"),
          invoke("getLatest"),
        ]);

        if (!histData || !histData.pods) {
          setError("Resolver returned no history data. Check that history.json is published to GitHub.");
          return;
        }

        const pods = Object.keys(histData.pods);
        setHistory(histData.pods);
        setLatest(latestData);
        setActiveTab(pods[0] || null);
      } catch (err) {
        setError(String(err?.message ?? err));
      } finally {
        setLoading(false);
        setTimeout(() => view.resize(), 300);
      }
    }
    load();
  }, []);


  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <div style={{ fontFamily: "'Segoe UI', Arial, sans-serif", padding: "20px", background: "#f4f5f7" }}>

      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ margin: 0, color: "#172B4D", fontSize: "20px" }}>Quality AI Dashboard</h2>
        <p style={{ margin: "4px 0 0", color: "#6B778C", fontSize: "13px" }}>
          CodeScene · Snyk — weekly trend
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ color: "#555", padding: "40px 0", textAlign: "center" }}>
          Loading metrics…
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          background: "#fff0f0", border: "1px solid #e74c3c",
          borderRadius: "6px", padding: "14px 18px", color: "#900",
          whiteSpace: "pre-wrap", wordBreak: "break-word",
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Dashboard content */}
      {!loading && !error && history && activeTab && (
        <>
          <TabBar
            pods={Object.keys(history)}
            active={activeTab}
            onSelect={pod => { setActiveTab(pod); setTimeout(() => view.resize(), 300); }}
          />
          <PodPanel
            podName={activeTab}
            series={history[activeTab]}
            latestPod={latest?.pods?.find(p => p.name === activeTab)}
          />
        </>
      )}

    </div>
  );
}


// ─── Mount ───────────────────────────────────────────────────────────────────
createRoot(document.getElementById("root")).render(<Dashboard />);
