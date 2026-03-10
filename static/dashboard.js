/**
 * COM748 Research Platform v1.3 — dashboard.js
 * Light-theme Chart.js visualizations, 7 charts across 2 tabs, tab switching.
 */

/* ── Chart.js Light Theme Defaults ── */
Chart.defaults.color = '#4B5563';
Chart.defaults.borderColor = 'rgba(0,0,0,0.07)';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 12;

const LIGHT_GRID = { color: 'rgba(0,0,0,0.06)' };
const LIGHT_TICK = { color: '#9CA3AF' };

/* ── Colour Palette (matching CSS tokens) ── */
const C = {
    static: '#F59E0B',
    interactive: '#4F46E5',
    accent: '#14B8A6',
    success: '#22C55E',
    error: '#EF4444',
    warning: '#F59E0B',
    logic: '#A78BFA',
    runtime: '#F59E0B',
    timeout: '#06B6D4',
    syntax: '#EF4444',
    muted: '#9CA3AF',
};
const EX_SHORT = ['EX01', 'EX02', 'EX03', 'EX04', 'EX05', 'EX06', 'EX07'];
// API returns ids as ex01, ex02 etc (lowercase). Map both ways.
const EX_TO_LOWER = id => id.toLowerCase();    // 'EX01' → 'ex01'


let chartInstances = {};
let insightsLoaded = false;

/* ── Utilities ── */
function alpha(hex, a) {
    const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${a})`;
}
function setStat(id, val) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('skeleton', 'skeleton-text');
    el.textContent = val;
}
function showError(msg) {
    const el = document.getElementById('db-error-banner');
    if (el) { el.textContent = '⚠ ' + msg; el.classList.add('visible'); }
}
function destroyChart(k) { if (chartInstances[k]) { chartInstances[k].destroy(); chartInstances[k] = null; } }
function emptyMsg(canvasId, msg) {
    const c = document.getElementById(canvasId);
    if (!c) return;
    c.parentElement.innerHTML = `<p style="text-align:center;color:#9CA3AF;padding:3rem 0;font-size:.83rem;">${msg}</p>`;
}
function setRefreshTime() {
    const el = document.getElementById('last-refresh');
    if (el) el.textContent = 'Updated: ' + new Date().toLocaleTimeString();
}

/* ═══════════════════════════════════
   OVERVIEW TAB — 4 charts
   ═══════════════════════════════════ */

async function loadPassRate() {
    try {
        const rows = await fetch('/api/stats/pass-rate').then(r => r.json());
        if (rows.error) return;
        const labels = rows.map(r => r.group === 'static' ? 'Static Group' : 'Interactive Group');
        const data = rows.map(r => r.pass_rate);
        const colors = rows.map(r => r.group === 'static' ? C.static : C.interactive);
        destroyChart('passRate');
        const ctx = document.getElementById('chart-pass-rate').getContext('2d');
        chartInstances.passRate = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Pass Rate (%)', data,
                    backgroundColor: colors.map(c => alpha(c, .75)), borderColor: colors,
                    borderWidth: 2, borderRadius: 8, borderSkipped: false
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${c.raw}%` } } },
                scales: {
                    y: { beginAtZero: true, max: 100, grid: LIGHT_GRID, ticks: { ...LIGHT_TICK, callback: v => v + '%' } },
                    x: { grid: { display: false }, ticks: { ...LIGHT_TICK, font: { weight: '600' } } }
                }
            }
        });
    } catch (e) { console.error('Pass rate:', e); }
}

async function loadErrors() {
    try {
        const rows = await fetch('/api/stats/errors').then(r => r.json());
        if (!rows.length) { emptyMsg('chart-errors', 'No error data yet.'); return; }
        const labels = rows.map(r => r.error_type[0].toUpperCase() + r.error_type.slice(1));
        const counts = rows.map(r => r.count);
        const colors = rows.map(r => C[r.error_type] || C.muted);
        destroyChart('errors');
        const ctx = document.getElementById('chart-errors').getContext('2d');
        chartInstances.errors = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data: counts, backgroundColor: colors.map(c => alpha(c, .8)),
                    borderColor: colors, borderWidth: 2, hoverOffset: 8
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false, cutout: '62%',
                plugins: {
                    legend: { position: 'right', labels: { usePointStyle: true, pointStyleWidth: 10, padding: 14 } },
                    tooltip: { callbacks: { label: c => ` ${c.label}: ${c.raw}` } }
                }
            }
        });
    } catch (e) { console.error('Errors:', e); }
}

async function loadAttempts() {
    try {
        const rows = await fetch('/api/stats/attempts').then(r => r.json());
        if (rows.error) return;
        const byGroup = { static: {}, interactive: {} };
        rows.forEach(r => { if (byGroup[r.group_type]) byGroup[r.group_type][r.exercise_id.toLowerCase()] = r.avg_attempts; });
        destroyChart('attempts');
        const ctx = document.getElementById('chart-attempts').getContext('2d');
        chartInstances.attempts = new Chart(ctx, {
            type: 'line',
            data: {
                labels: EX_SHORT,
                datasets: [
                    {
                        label: 'Static', data: EX_SHORT.map(id => byGroup.static[EX_TO_LOWER(id)] ?? null),
                        borderColor: C.static, backgroundColor: alpha(C.static, .1),
                        borderWidth: 2.5, tension: 0.4, fill: true,
                        pointBackgroundColor: C.static, pointRadius: 5, spanGaps: true
                    },
                    {
                        label: 'Interactive', data: EX_SHORT.map(id => byGroup.interactive[EX_TO_LOWER(id)] ?? null),
                        borderColor: C.interactive, backgroundColor: alpha(C.interactive, .1),
                        borderWidth: 2.5, tension: 0.4, fill: true,
                        pointBackgroundColor: C.interactive, pointRadius: 5, spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'top', labels: { usePointStyle: true, pointStyleWidth: 10 } } },
                scales: {
                    y: { beginAtZero: true, grid: LIGHT_GRID, ticks: LIGHT_TICK, title: { display: true, text: 'Avg Attempts', color: '#9CA3AF' } },
                    x: { grid: { display: false }, ticks: LIGHT_TICK }
                }
            }
        });
    } catch (e) { console.error('Attempts:', e); }
}

async function loadLearningCurve() {
    try {
        const rows = await fetch('/api/stats/learning-curve').then(r => r.json());
        if (!rows.length) { emptyMsg('chart-learning', 'Insufficient pass data yet.'); return; }
        const byGroup = { static: {}, interactive: {} };
        rows.forEach(r => { if (byGroup[r.group_type]) byGroup[r.group_type][r.exercise_id.toLowerCase()] = r.avg_first_pass; });
        destroyChart('learning');
        const ctx = document.getElementById('chart-learning').getContext('2d');
        chartInstances.learning = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: EX_SHORT,
                datasets: [
                    {
                        label: 'Static', data: EX_SHORT.map(id => byGroup.static[EX_TO_LOWER(id)] ?? null),
                        backgroundColor: alpha(C.static, .75), borderColor: C.static, borderWidth: 2, borderRadius: 6, borderSkipped: false
                    },
                    {
                        label: 'Interactive', data: EX_SHORT.map(id => byGroup.interactive[EX_TO_LOWER(id)] ?? null),
                        backgroundColor: alpha(C.interactive, .75), borderColor: C.interactive, borderWidth: 2, borderRadius: 6, borderSkipped: false
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true, pointStyleWidth: 10 } },
                    tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${c.raw} attempts` } }
                },
                scales: {
                    y: { beginAtZero: true, grid: LIGHT_GRID, ticks: LIGHT_TICK, title: { display: true, text: 'Avg attempts to first pass', color: '#9CA3AF' } },
                    x: { grid: { display: false }, ticks: LIGHT_TICK }
                }
            }
        });
    } catch (e) { console.error('Learning curve:', e); }
}

/* ═══════════════════════════════════
   RESEARCH INSIGHTS TAB — 3 charts
   ═══════════════════════════════════ */

async function loadInsights() {
    if (insightsLoaded) return;
    insightsLoaded = true;
    await Promise.allSettled([loadTimeToPass(), loadPersistence(), loadErrorTransitions()]);
}

async function loadTimeToPass() {
    try {
        const rows = await fetch('/api/stats/time-to-pass').then(r => r.json());
        if (!rows.length) { emptyMsg('chart-time-to-pass', 'No time-to-pass data yet — requires valid sessions with at least one passed exercise.'); return; }
        const byGroup = { static: {}, interactive: {} };
        rows.forEach(r => { if (byGroup[r.group_type]) byGroup[r.group_type][r.exercise_id.toLowerCase()] = r.avg_time_seconds; });
        destroyChart('timeToPPass');
        const ctx = document.getElementById('chart-time-to-pass').getContext('2d');
        chartInstances.timeToPPass = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: EX_SHORT,
                datasets: [
                    {
                        label: 'Static (s)', data: EX_SHORT.map(id => byGroup.static[EX_TO_LOWER(id)] ?? null),
                        backgroundColor: alpha(C.warning, .75), borderColor: C.warning, borderWidth: 2, borderRadius: 6, borderSkipped: false, spanGaps: true
                    },
                    {
                        label: 'Interactive (s)', data: EX_SHORT.map(id => byGroup.interactive[EX_TO_LOWER(id)] ?? null),
                        backgroundColor: alpha(C.accent, .75), borderColor: C.accent, borderWidth: 2, borderRadius: 6, borderSkipped: false, spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true, pointStyleWidth: 10 } },
                    tooltip: {
                        callbacks: {
                            label: c => {
                                if (c.raw <= 5.0 && c.raw > 0) return ` ${c.dataset.label}: ~${c.raw}s (passed on 1st attempt)`;
                                return ` ${c.dataset.label}: ${c.raw}s avg to first pass`;
                            }
                        }
                    }

                },
                scales: {
                    y: { beginAtZero: true, grid: LIGHT_GRID, ticks: LIGHT_TICK, title: { display: true, text: 'Seconds to first pass', color: '#9CA3AF' } },
                    x: { grid: { display: false }, ticks: LIGHT_TICK }
                }
            }
        });
    } catch (e) { console.error('Time-to-pass:', e); }
}

async function loadPersistence() {
    try {
        const rows = await fetch('/api/stats/persistence').then(r => r.json());
        if (!rows.length) { emptyMsg('chart-persistence', 'No persistence data yet — requires sessions where exercises were never passed.'); return; }
        const byGroup = { static: {}, interactive: {} };
        rows.forEach(r => { if (byGroup[r.group_type]) byGroup[r.group_type][r.exercise_id.toLowerCase()] = r.avg_attempts; });
        destroyChart('persistence');
        const ctx = document.getElementById('chart-persistence').getContext('2d');
        chartInstances.persistence = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: EX_SHORT,
                datasets: [
                    {
                        label: 'Static', data: EX_SHORT.map(id => byGroup.static[EX_TO_LOWER(id)] ?? null),
                        backgroundColor: alpha(C.error, .7), borderColor: C.error, borderWidth: 2, borderRadius: 6, borderSkipped: false
                    },
                    {
                        label: 'Interactive', data: EX_SHORT.map(id => byGroup.interactive[EX_TO_LOWER(id)] ?? null),
                        backgroundColor: alpha(C.logic, .7), borderColor: C.logic, borderWidth: 2, borderRadius: 6, borderSkipped: false
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true, pointStyleWidth: 10 } },
                    tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${c.raw} avg attempts (never passed)` } }
                },
                scales: {
                    y: { beginAtZero: true, grid: LIGHT_GRID, ticks: LIGHT_TICK, title: { display: true, text: 'Avg attempts (unsolved)', color: '#9CA3AF' } },
                    x: { grid: { display: false }, ticks: LIGHT_TICK }
                }
            }
        });
    } catch (e) { console.error('Persistence:', e); }
}

async function loadErrorTransitions() {
    try {
        const rows = await fetch('/api/stats/error-transitions').then(r => r.json());
        if (!rows.length) { emptyMsg('chart-transitions', 'No error transition data yet — requires multiple attempts per session.'); return; }
        const top = rows.slice(0, 12);
        const labels = top.map(r => `${r.from} → ${r.to}`);
        const counts = top.map(r => r.count);
        const colors = top.map((_, i) => [C.error, C.warning, C.logic, C.accent, C.interactive, C.success][i % 6]);
        destroyChart('transitions');
        const ctx = document.getElementById('chart-transitions').getContext('2d');
        chartInstances.transitions = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Occurrences', data: counts,
                    backgroundColor: colors.map(c => alpha(c, .72)), borderColor: colors,
                    borderWidth: 2, borderRadius: 6, borderSkipped: false
                }]
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${c.raw} transitions` } } },
                scales: {
                    x: { beginAtZero: true, grid: LIGHT_GRID, ticks: LIGHT_TICK },
                    y: { grid: { display: false }, ticks: { ...LIGHT_TICK, font: { family: "'JetBrains Mono',monospace", size: 11 } } }
                }
            }
        });
    } catch (e) { console.error('Transitions:', e); }
}

/* ═══════════════════════════════════
   SUMMARY STATS (top cards)
   ═══════════════════════════════════ */

async function loadSummary() {
    try {
        const [summary, quality] = await Promise.all([
            fetch('/api/stats/summary').then(r => r.json()),
            fetch('/api/stats/session-quality').then(r => r.json()),
        ]);
        if (summary.error) { showError(summary.error); return; }
        setStat('stat-participants', summary.total_participants ?? '—');
        setStat('stat-static', summary.static_participants ?? '—');
        setStat('stat-interactive', summary.interactive_participants ?? '—');
        setStat('stat-attempts', summary.total_attempts ?? '—');
        setStat('stat-passrate', (summary.overall_pass_rate ?? '—') + '%');
        if (!quality.error) setStat('stat-valid', `${quality.valid ?? 0} / ${quality.total ?? 0}`);
    } catch (e) { showError('Cannot reach /api/stats/summary — is the server running?'); }
}

/* ═══════════════════════════════════
   TAB SWITCHING
   ═══════════════════════════════════ */

document.querySelectorAll('.dash-tab').forEach(tab => {
    tab.addEventListener('click', function () {
        const target = this.dataset.tab;
        document.querySelectorAll('.dash-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        this.classList.add('active');
        const pane = document.getElementById('tab-' + target);
        if (pane) pane.classList.add('active');
        if (target === 'insights') loadInsights();
        if (typeof lucide !== 'undefined') lucide.createIcons();
    });
});

/* ═══════════════════════════════════
   INIT & AUTO-REFRESH
   ═══════════════════════════════════ */

async function loadOverview() {
    await loadSummary();
    await Promise.allSettled([loadPassRate(), loadErrors(), loadAttempts(), loadLearningCurve()]);
    setRefreshTime();
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadOverview();
    setInterval(loadOverview, 30_000);

    const btn = document.getElementById('refresh-btn');
    if (btn) {
        btn.addEventListener('click', async () => {
            btn.disabled = true;
            btn.innerHTML = 'Refreshing…';
            insightsLoaded = false;
            const activeInsights = document.getElementById('tab-insights');
            if (activeInsights?.classList.contains('active')) {
                await Promise.all([loadOverview(), loadInsights()]);
            } else {
                await loadOverview();
            }
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="refresh-cw"></i> Refresh';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        });
    }
});
