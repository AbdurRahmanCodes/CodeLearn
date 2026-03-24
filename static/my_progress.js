(function () {
    var progressChart = null;
    var quizChart = null;

    function setText(id, value) {
        var el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function showAlert(message) {
        var alertEl = document.getElementById('dashboard-alert');
        if (!alertEl) return;
        alertEl.textContent = message;
        alertEl.classList.add('visible');
    }

    function hideAlert() {
        var alertEl = document.getElementById('dashboard-alert');
        if (!alertEl) return;
        alertEl.textContent = '';
        alertEl.classList.remove('visible');
    }

    async function fetchJson(url) {
        var response = await fetch(url);
        var data = await response.json();
        return { status: response.status, data: data };
    }

    function destroyCharts() {
        if (progressChart) {
            progressChart.destroy();
            progressChart = null;
        }
        if (quizChart) {
            quizChart.destroy();
            quizChart = null;
        }
    }

    function toExerciseLabel(exerciseId) {
        var raw = String(exerciseId || '');
        if (raw.toLowerCase().startsWith('ex')) {
            return raw.toUpperCase();
        }
        return 'EX' + raw;
    }

    function renderProgressChart(exercises) {
        if (typeof Chart === 'undefined') return;
        var canvas = document.getElementById('progress-chart');
        if (!canvas) return;

        var keys = Object.keys(exercises || {});
        var labels = keys.map(toExerciseLabel);
        var attempts = keys.map(function (key) { return Number((exercises[key] || {}).total_attempts || 0); });
        var passState = keys.map(function (key) { return (exercises[key] || {}).passed ? 1 : 0; });

        progressChart = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Attempts',
                        data: attempts,
                        backgroundColor: 'rgba(79, 70, 229, 0.75)',
                        borderColor: '#4F46E5',
                        borderWidth: 2,
                        borderRadius: 8,
                    },
                    {
                        label: 'Passed',
                        data: passState,
                        type: 'line',
                        borderColor: '#22C55E',
                        backgroundColor: 'rgba(34, 197, 94, 0.12)',
                        borderWidth: 2,
                        pointRadius: 4,
                        yAxisID: 'y1',
                        tension: 0.3,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Attempts' }
                    },
                    y1: {
                        beginAtZero: true,
                        max: 1,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: {
                            callback: function (value) {
                                return value === 1 ? 'Yes' : 'No';
                            }
                        },
                        title: { display: true, text: 'Passed' }
                    }
                }
            }
        });
    }

    function renderQuizChart(quizzesByTopic) {
        if (typeof Chart === 'undefined') return;
        var canvas = document.getElementById('quiz-chart');
        if (!canvas) return;

        var topics = Object.keys(quizzesByTopic || {});
        var scores = topics.map(function (topic) {
            var attempts = quizzesByTopic[topic] || [];
            var latest = attempts[0] || {};
            return Number(latest.percentage || 0);
        });

        quizChart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: topics,
                datasets: [
                    {
                        label: 'Quiz Score %',
                        data: scores,
                        borderColor: '#14B8A6',
                        backgroundColor: 'rgba(20, 184, 166, 0.16)',
                        borderWidth: 2,
                        pointRadius: 5,
                        pointBackgroundColor: '#14B8A6',
                        tension: 0.35,
                        fill: true,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function (value) { return value + '%'; }
                        }
                    }
                }
            }
        });
    }

    function renderRecommendations(recommendations) {
        var wrap = document.getElementById('recommendation-history');
        if (!wrap) return;

        if (!recommendations || !recommendations.length) {
            wrap.innerHTML = '<article class="info-section"><p>No recommendations shown in this session.</p></article>';
            return;
        }

        wrap.innerHTML = recommendations.slice(0, 12).map(function (rec) {
            var title = rec.title || rec.recommendation_type || 'Recommendation';
            var reason = rec.reason || 'Adaptive support';
            var topic = rec.topic || 'General';
            var timestamp = rec.timestamp || '';
            return (
                '<article class="info-section">' +
                '<h3 class="info-section__title">' + title + '</h3>' +
                '<p><strong>Topic:</strong> ' + topic + '</p>' +
                '<p>' + reason + '</p>' +
                (timestamp ? '<p><small>' + timestamp + '</small></p>' : '') +
                '</article>'
            );
        }).join('');
    }

    function renderInsights(weakTopics) {
        var wrap = document.getElementById('insights-panel');
        if (!wrap) return;

        if (!weakTopics || !weakTopics.length) {
            wrap.innerHTML = '<article class="info-section"><p>No weak topics detected yet. Keep practicing to generate personalized insights.</p></article>';
            return;
        }

        var topWeak = weakTopics[0] || {};
        var recommendation = 'You should review ' + String(topWeak.topic || 'this topic') + '.';
        wrap.innerHTML =
            '<article class="info-section">' +
            '<h3 class="info-section__title">Weak topics</h3>' +
            '<ul style="margin:.5rem 0 0 1rem;">' +
            weakTopics.slice(0, 4).map(function (row) {
                return '<li>' + String(row.topic || 'unknown') + ' (' + Number(row.failure_rate || 0).toFixed(1) + '% failure)</li>';
            }).join('') +
            '</ul>' +
            '<p style="margin-top:.7rem;"><strong>Suggestion:</strong> ' + recommendation + '</p>' +
            '</article>';
    }

    async function loadDashboard() {
        var loadingEl = document.getElementById('progress-loading');
        try {
            hideAlert();
            destroyCharts();
            if (loadingEl) loadingEl.style.display = 'block';

            var userRes = await fetchJson('/dashboard/user');
            if (userRes.status !== 200 || !userRes.data.success) {
                setText('session-status-pill', 'Session status: Start a learning session first');
                showAlert('Start a session to see your progress. Choose language and mode on Home first.');
                var insightsWrap = document.getElementById('insights-panel');
                if (insightsWrap) {
                    insightsWrap.innerHTML = '<article class="info-section"><p>Start a session to see your progress.</p></article>';
                }
                return;
            }

            var dashboard = userRes.data.dashboard || {};
            setText('session-status-pill', 'Session status: Active');
            setText('user-total-attempts', String(dashboard.total_attempts || 0));
            setText('user-pass-rate', String(dashboard.pass_rate || 0) + '%');
            setText('user-exercises-completed', String(dashboard.exercises_completed || 0));
            setText('user-quiz-average', String(dashboard.average_quiz_score || 0) + '%');

            var progressRes = await fetchJson('/dashboard/progress');
            renderProgressChart((progressRes.data || {}).exercises || {});

            var quizRes = await fetchJson('/dashboard/quizzes');
            renderQuizChart((quizRes.data || {}).quizzes || {});

            var recRes = await fetchJson('/dashboard/recommendations');
            renderRecommendations((recRes.data || {}).recommendations || []);

            var weakRes = await fetchJson('/dashboard/weak-topics');
            renderInsights((weakRes.data || {}).weak_topics || []);

            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        } catch (err) {
            showAlert('Unable to load progress data right now. Please try again shortly.');
            console.error(err);
        } finally {
            if (loadingEl) loadingEl.style.display = 'none';
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }
    }

    loadDashboard();
})();
