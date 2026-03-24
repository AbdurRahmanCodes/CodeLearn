Chart.defaults.color = '#4B5563';
Chart.defaults.borderColor = 'rgba(0,0,0,0.07)';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 12;

const LIGHT_GRID = { color: 'rgba(0,0,0,0.06)' };
const LIGHT_TICK = { color: '#9CA3AF' };

const C = {
  control: '#F59E0B',
  adaptive: '#4F46E5',
  success: '#22C55E',
  error: '#EF4444',
  warning: '#F59E0B',
  accent: '#14B8A6',
  muted: '#9CA3AF',
};

const chartInstances = {};

function seriesHasData(labels, values, requireNonZero = false) {
  if (!Array.isArray(labels) || !Array.isArray(values)) return false;
  if (labels.length === 1 && String(labels[0]).toLowerCase() === 'no data') return false;
  const numericValues = values
    .map((v) => Number(v))
    .filter((v) => Number.isFinite(v));
  if (!numericValues.length) return false;
  if (requireNonZero) return numericValues.some((v) => v !== 0);
  return true;
}

function setChartFallback(canvasId, show) {
  const fb = document.getElementById('fb-' + canvasId);
  if (fb) fb.style.display = show ? 'block' : 'none';
}

function alpha(hex, a) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function setStat(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = String(val);
}

function showError(msg) {
  const el = document.getElementById('db-error-banner');
  if (!el) return;
  el.textContent = 'Error: ' + msg;
  el.classList.add('visible');
}

function hideError() {
  const el = document.getElementById('db-error-banner');
  if (!el) return;
  el.textContent = '';
  el.classList.remove('visible');
}

function setRefreshTime() {
  const el = document.getElementById('last-refresh');
  if (el) el.textContent = 'Updated: ' + new Date().toLocaleTimeString();
}

function destroyChart(key) {
  if (chartInstances[key]) {
    chartInstances[key].destroy();
    chartInstances[key] = null;
  }
}

function drawBarChart(id, key, labels, values, title, color) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  if (!seriesHasData(labels, values, false)) {
    destroyChart(key);
    setChartFallback(id, true);
    return;
  }
  setChartFallback(id, false);
  destroyChart(key);
  const ctx = canvas.getContext('2d');
  chartInstances[key] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: title,
        data: values,
        backgroundColor: labels.map(() => alpha(color, 0.75)),
        borderColor: labels.map(() => color),
        borderWidth: 2,
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, grid: LIGHT_GRID, ticks: LIGHT_TICK },
        x: { grid: { display: false }, ticks: LIGHT_TICK },
      },
    },
  });
}

function drawGroupedBar(id, key, labels, ds1Label, ds1, ds2Label, ds2) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  if (!seriesHasData(labels, ds1, false) && !seriesHasData(labels, ds2, false)) {
    destroyChart(key);
    setChartFallback(id, true);
    return;
  }
  setChartFallback(id, false);
  destroyChart(key);
  const ctx = canvas.getContext('2d');
  chartInstances[key] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: ds1Label,
          data: ds1,
          backgroundColor: alpha(C.control, 0.75),
          borderColor: C.control,
          borderWidth: 2,
          borderRadius: 6,
        },
        {
          label: ds2Label,
          data: ds2,
          backgroundColor: alpha(C.adaptive, 0.75),
          borderColor: C.adaptive,
          borderWidth: 2,
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, grid: LIGHT_GRID, ticks: LIGHT_TICK },
        x: { grid: { display: false }, ticks: LIGHT_TICK },
      },
    },
  });
}

function drawPie(id, key, labels, values) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  if (!seriesHasData(labels, values, true)) {
    destroyChart(key);
    setChartFallback(id, true);
    return;
  }
  setChartFallback(id, false);
  destroyChart(key);
  const colors = [C.error, C.warning, C.accent, C.adaptive, C.control, C.muted];
  const ctx = canvas.getContext('2d');
  chartInstances[key] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: labels.map((_, i) => alpha(colors[i % colors.length], 0.8)),
        borderColor: labels.map((_, i) => colors[i % colors.length]),
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'right' } },
    },
  });
}

async function fetchJson(url) {
  const res = await fetch(url);
  return res.json();
}

async function loadOverview() {
  const data = await fetchJson('/api/stats/dashboard-overview');
  if (data.error) throw new Error(data.error);
  setStat('stat-participants', data.total_participants ?? 0);
  setStat('stat-attempts', data.total_attempts ?? 0);
  setStat('stat-control', data.control_group_size ?? 0);
  setStat('stat-adaptive', data.adaptive_group_size ?? 0);
  setStat('stat-passrate', `${Number(data.overall_pass_rate ?? 0).toFixed(1)}%`);
  setStat(
    'stat-avg-attempts-pass',
    `${Number(data.avg_attempts_to_first_pass_control ?? 0).toFixed(2)} vs ${Number(data.avg_attempts_to_first_pass_adaptive ?? 0).toFixed(2)}`,
  );
}

async function loadCoreResults() {
  const core = await fetchJson('/api/stats/dashboard-core');
  if (core.error) throw new Error(core.error);

  drawBarChart('chart-pass-rate', 'passRate', core.pass_rate.labels, core.pass_rate.values, 'Pass Rate (%)', C.success);
  drawBarChart('chart-attempts-first-pass', 'attemptsFirstPass', core.attempts_to_first_pass.labels, core.attempts_to_first_pass.values, 'Avg Attempts to First Pass', C.warning);
  drawBarChart('chart-time-first-pass', 'timeFirstPass', core.time_to_first_pass.labels, core.time_to_first_pass.values, 'Seconds to First Pass', C.accent);
  drawBarChart('chart-improvement-rate', 'improvementRate', core.improvement_rate.labels, core.improvement_rate.values, 'Improvement Rate', C.adaptive);
  drawBarChart('chart-error-reduction', 'errorReduction', core.error_reduction_rate.labels, core.error_reduction_rate.values, 'Error Reduction Rate', C.control);
}

async function loadBehaviorResults() {
  const behavior = await fetchJson('/api/stats/dashboard-behavior');
  if (behavior.error) throw new Error(behavior.error);

  drawPie('chart-errors', 'errors', behavior.error_distribution.labels, behavior.error_distribution.values);
  drawBarChart('chart-topic-success', 'topicSuccess', behavior.topic_success.labels, behavior.topic_success.values, 'Topic Success (%)', C.success);
  drawGroupedBar(
    'chart-language-difficulty',
    'languageDifficulty',
    behavior.language_difficulty.labels,
    'Pass Rate %',
    behavior.language_difficulty.pass_rate,
    'Syntax Error %',
    behavior.language_difficulty.syntax_error_rate,
  );
}

async function loadAdaptivityResults() {
  const adapt = await fetchJson('/api/stats/dashboard-adaptivity');
  if (adapt.error) throw new Error(adapt.error);

  drawBarChart(
    'chart-recommendation-effect',
    'recommendationEffect',
    adapt.recommendation_effectiveness.labels,
    adapt.recommendation_effectiveness.values,
    'Pass Rate by Recommendation Exposure',
    C.success,
  );
  drawBarChart(
    'chart-adaptive-actions',
    'adaptiveActions',
    adapt.adaptive_actions.labels,
    adapt.adaptive_actions.values,
    'Adaptive Actions Count',
    C.adaptive,
  );
  drawBarChart(
    'chart-recommendation-intensity',
    'recommendationIntensity',
    adapt.recommendation_intensity.labels,
    adapt.recommendation_intensity.values,
    'Recommendation Intensity Count',
    C.warning,
  );
}

async function loadRecommendedNextStep() {
  const wrap = document.getElementById('next-step-card');
  if (!wrap) return;
  try {
    const data = await fetchJson('/dashboard/recommended-next-step');
    if (!data.success || !data.recommendation) {
      wrap.innerHTML = '<p class="adaptive-empty">No recommendation available.</p>';
      return;
    }
    const rec = data.recommendation;
    wrap.innerHTML = `
      <div class="next-step-card">
        <div class="next-step-card__type">${String(rec.type || 'recommendation')}</div>
        <div class="next-step-card__title">${String((rec.topic || 'topic')).toUpperCase()} - ${String((rec.language || 'python')).toUpperCase()}</div>
        <div class="next-step-card__message">${String(rec.message || '')}</div>
      </div>
    `;
  } catch {
    wrap.innerHTML = '<p class="adaptive-error">Unable to load recommendation.</p>';
  }
}

async function loadDashboard() {
  const loading = document.getElementById('dashboard-loading');
  try {
    hideError();
    if (loading) loading.style.display = 'block';
    await loadOverview();
    await loadCoreResults();
    await loadBehaviorResults();
    await loadAdaptivityResults();
    await loadRecommendedNextStep();
    setRefreshTime();
    if (typeof lucide !== 'undefined') lucide.createIcons();
  } catch (err) {
    showError(err.message || 'Failed to load dashboard data');
  } finally {
    if (loading) loading.style.display = 'none';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  const refreshBtn = document.getElementById('refresh-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      refreshBtn.disabled = true;
      refreshBtn.textContent = 'Refreshing...';
      await loadDashboard();
      refreshBtn.disabled = false;
      refreshBtn.innerHTML = '<i data-lucide="refresh-cw"></i> Refresh';
      if (typeof lucide !== 'undefined') lucide.createIcons();
    });
  }
  setInterval(() => {
    if (document.visibilityState === 'visible') loadDashboard();
  }, 30000);
});
