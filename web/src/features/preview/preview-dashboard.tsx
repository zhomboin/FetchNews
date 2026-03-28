import React from "react";

type PreviewDashboardProps = {
  health: string;
  currentPath: string;
};

type MetricCell = {
  label: string;
  value: string;
  note: string;
};

type QueueItem = {
  title: string;
  group: string;
  score: string;
  sources: string;
  state: string;
  reason: string;
};

type ArticleSection = {
  heading: string;
  body: string;
};

type SourceMixItem = {
  label: string;
  ratio: number;
};

type LogEntry = {
  time: string;
  level: "warn" | "info" | "error";
  title: string;
  detail: string;
};

type PublishWindow = {
  time: string;
  platform: string;
  status: string;
};

type SectionTitleProps = {
  kicker: string;
  title: string;
  meta?: string;
};

const METRICS: MetricCell[] = [
  { label: "今日采集", value: "184", note: "+12 高优信号" },
  { label: "待审核", value: "27", note: "4 条需人工复核" },
  { label: "待发布", value: "08", note: "18:30 批次已排程" },
  { label: "异常日志", value: "03", note: "2 个源需重试" },
];

const QUEUE_ITEMS: QueueItem[] = [
  {
    title: "OpenAI 发布 agent 评测工具链更新",
    group: "模型 / 工具链",
    score: "92",
    sources: "GitHub | Blog | X",
    state: "高可信",
    reason: "多源交叉一致，适合进入今日头条段落。",
  },
  {
    title: "Mistral 推出推理栈性能优化版本",
    group: "推理 / 基建",
    score: "81",
    sources: "Blog | X",
    state: "待确认",
    reason: "缺少第三来源，建议人工补查 release note。",
  },
  {
    title: "HF 新开源评测集登上社区热榜",
    group: "数据 / 社区",
    score: "74",
    sources: "Hugging Face | Reddit",
    state: "可入选",
    reason: "社区热度高，适合放入次级栏目条目。",
  },
];

const ARTICLE_SECTIONS: ArticleSection[] = [
  {
    heading: "模型与平台",
    body: "今日高价值更新集中在 agent 评测和推理效率，两条主线都显示出平台方在把能力从“发布模型”推进到“验证可用性”。",
  },
  {
    heading: "开源与社区",
    body: "社区端更关注评测基准和真实工作流，热度正在从单纯参数规模转向部署稳定性、工具链成熟度和验证成本。",
  },
  {
    heading: "编辑提示",
    body: "建议头条保留 OpenAI 与 Mistral 两条，避免三条工具新闻连续堆叠；社区项适合放入第二屏短评。",
  },
];

const SOURCE_MIX: SourceMixItem[] = [
  { label: "GitHub / Releases", ratio: 0.42 },
  { label: "Official Blogs", ratio: 0.27 },
  { label: "X Allowlist", ratio: 0.19 },
  { label: "Papers / arXiv", ratio: 0.12 },
];

const LOG_ENTRIES: LogEntry[] = [
  { time: "16:02", level: "warn", title: "x-allowlist rate window hit", detail: "切换到回退节流队列，计划 16:08 自动重试。" },
  { time: "15:48", level: "info", title: "daily digest rebuilt", detail: "根据最新审核结果重新生成长文与短帖版本。" },
  { time: "15:31", level: "error", title: "rss parser mismatch", detail: "某博客 feed 字段缺失 author，已落入异常池。" },
  { time: "14:57", level: "info", title: "publish queue scheduled", detail: "公众号与 X 批次写入发布队列，等待人工确认。" },
];

const PUBLISH_WINDOWS: PublishWindow[] = [
  { time: "17:40", platform: "公众号", status: "待人工确认" },
  { time: "18:30", platform: "X", status: "已排程" },
  { time: "18:35", platform: "Telegram", status: "已排程" },
];

const SIGNAL_SERIES = [42, 49, 47, 61, 58, 71, 76];
const VIEW_LABEL_BY_PATH: Record<string, string> = {
  "/": "总览视角",
  "/stories": "审核视角",
  "/articles": "草稿视角",
  "/publishing": "发布视角",
};

function SignalChart(): React.JSX.Element {
  const width = 320;
  const height = 150;
  const padding = 18;
  const maxValue = Math.max(...SIGNAL_SERIES);
  const minValue = Math.min(...SIGNAL_SERIES);
  const stepX = (width - padding * 2) / (SIGNAL_SERIES.length - 1);

  const points = SIGNAL_SERIES.map((value, index) => {
    const x = padding + index * stepX;
    const y = height - padding - ((value - minValue) / Math.max(maxValue - minValue, 1)) * (height - padding * 2);
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="signal-chart" aria-label="近七日信号强度变化">
      <defs>
        <linearGradient id="signal-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="rgba(191, 156, 106, 0.34)" />
          <stop offset="100%" stopColor="rgba(191, 156, 106, 0)" />
        </linearGradient>
      </defs>
      {[0, 1, 2, 3].map((line) => (
        <line
          key={line}
          x1={padding}
          y1={padding + line * 34}
          x2={width - padding}
          y2={padding + line * 34}
          className="signal-grid"
        />
      ))}
      <polyline points={`${padding},${height - padding} ${points} ${width - padding},${height - padding}`} className="signal-area" />
      <polyline points={points} className="signal-line" />
      {SIGNAL_SERIES.map((value, index) => {
        const x = padding + index * stepX;
        const y = height - padding - ((value - minValue) / Math.max(maxValue - minValue, 1)) * (height - padding * 2);
        return <circle key={`${value}-${index}`} cx={x} cy={y} r="3.8" className="signal-dot" />;
      })}
    </svg>
  );
}

function SectionTitle({ kicker, title, meta }: SectionTitleProps): React.JSX.Element {
  return (
    <header className="section-title">
      <div>
        <p>{kicker}</p>
        <h2>{title}</h2>
      </div>
      {meta ? <span>{meta}</span> : null}
    </header>
  );
}

/**
 * Preview shell for the warm-metal admin experience before full feature pages land.
 */
export function PreviewDashboard({ health, currentPath }: PreviewDashboardProps): React.JSX.Element {
  const currentLabel = VIEW_LABEL_BY_PATH[currentPath] ?? VIEW_LABEL_BY_PATH["/"];

  return (
    <div className="preview-page">
      <section className="intro-band">
        <div className="intro-copy">
          <p className="eyebrow">Warm Metal Review Surface</p>
          <h1>AI 内容审核与分发后台预览</h1>
          <p className="lede">
            用暖白金属极简基底承载审核、统计、日志和草稿预览。整体强调秩序、可信度与轻未来感，而不是炫技型 AI 控制台。
          </p>
        </div>

        <div className="intro-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>当前预览</span>
            <strong>{currentLabel}</strong>
          </div>
        </div>
      </section>

      <section className="metric-strip" aria-label="核心概览指标">
        {METRICS.map((metric) => (
          <article key={metric.label} className="metric-cell">
            <p>{metric.label}</p>
            <strong>{metric.value}</strong>
            <span>{metric.note}</span>
          </article>
        ))}
      </section>

      <section className="preview-grid">
        <article className="panel queue-panel">
          <SectionTitle kicker="Content Audit" title="审核队列" meta="27 条待筛选" />
          <div className="queue-list">
            {QUEUE_ITEMS.map((item) => (
              <article key={item.title} className="queue-row">
                <div className="queue-score">{item.score}</div>
                <div className="queue-main">
                  <div className="queue-heading">
                    <h3>{item.title}</h3>
                    <span>{item.group}</span>
                  </div>
                  <p>{item.reason}</p>
                </div>
                <div className="queue-meta">
                  <strong>{item.state}</strong>
                  <span>{item.sources}</span>
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="panel mix-panel">
          <SectionTitle kicker="Source Weight" title="来源结构" meta="P0 优先" />
          <div className="mix-list">
            {SOURCE_MIX.map((item) => (
              <div key={item.label} className="mix-row">
                <div className="mix-copy">
                  <strong>{item.label}</strong>
                  <span>{Math.round(item.ratio * 100)}%</span>
                </div>
                <div className="mix-track">
                  <div className="mix-fill" style={{ width: `${item.ratio * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel draft-panel">
          <SectionTitle kicker="Daily Digest" title="长文草稿预览" meta="已生成 v3" />
          <div className="draft-article">
            <div className="draft-headline">
              <p>今日导语</p>
              <h3>AI 资讯日报 2026-03-25</h3>
              <span>今日重点从“模型发布”向“可用性验证”迁移，审核建议聚焦平台级动作而非单点热帖。</span>
            </div>

            <div className="draft-body">
              {ARTICLE_SECTIONS.map((section) => (
                <section key={section.heading}>
                  <h4>{section.heading}</h4>
                  <p>{section.body}</p>
                </section>
              ))}
            </div>
          </div>
        </article>

        <article className="panel chart-panel">
          <SectionTitle kicker="Signal Tempo" title="近七日信号强度" meta="自动聚类结果" />
          <SignalChart />
          <div className="chart-footer">
            <span>周初以官方博客为主</span>
            <span>周中开始转向多源交叉热点</span>
          </div>
        </article>

        <article className="panel log-panel">
          <SectionTitle kicker="Ops Ledger" title="系统日志" meta="近 4 条事件" />
          <div className="log-list">
            {LOG_ENTRIES.map((entry) => (
              <article key={`${entry.time}-${entry.title}`} className={`log-row log-${entry.level}`}>
                <div className="log-time">{entry.time}</div>
                <div className="log-main">
                  <div className="log-head">
                    <strong>{entry.title}</strong>
                    <span>{entry.level}</span>
                  </div>
                  <p>{entry.detail}</p>
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="panel publish-panel">
          <SectionTitle kicker="Publish Runway" title="发布窗口" meta="今日排程" />
          <div className="runway">
            {PUBLISH_WINDOWS.map((window, index) => (
              <div key={`${window.time}-${window.platform}`} className="runway-step">
                <div className="runway-node">
                  <span>{index + 1}</span>
                </div>
                <div className="runway-copy">
                  <strong>{window.platform}</strong>
                  <p>{window.time}</p>
                  <span>{window.status}</span>
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}