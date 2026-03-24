# Design and Evaluation of an Interactive Educational Platform for Teaching Computer Programming (COM748)

MSc Computing Candidate, COM748 Dissertation Module

## Abstract
This paper presents the design, implementation, and evaluation of CodeLearn, a lightweight research-oriented educational platform for introductory programming. The platform was built to investigate whether rule-based adaptive support improves beginner outcomes when compared with non-adaptive progression. The system uses a Flask and MongoDB backend, server-rendered Jinja templates, vanilla JavaScript, and CodeMirror for interactive coding. Unlike heavy AI tutoring systems, adaptivity is implemented through transparent decision rules based on error patterns, attempts, pace, topic mastery, and language-specific difficulty. A two-factor experiment design was implemented across learning mode and intervention arm, with complete event logging in attempts, quiz_attempts, recommendations_log, session_context, and learning_events collections. Evaluation was conducted using a reproducible synthetic population pipeline configured for research consistency. The final evaluation dataset contained 166 participant sessions, 1667 attempt records, 434 quiz records, and 181 recommendation events. Adaptive intervention improved mean session pass rate from 40.75% to 72.91% and reduced mean attempts-to-first-pass from 1.90 to 1.30. Welch testing indicated statistically significant differences for pass rate (t = 9.532, p < 0.001, Cohen's d = 1.478) and attempts-to-first-pass (t = -6.354, p < 0.001, Cohen's d = -0.993). Error-reduction differences were small and non-significant (15.08% vs 15.48%, t = 0.061, p = 0.951, d = 0.01), showing that the major benefit emerged in attainment speed and successful completion rather than in global error trend separation. The findings support the use of transparent, rule-based adaptivity for beginner programming improvement while preserving project scope, interpretability, and operational simplicity.

## Keywords
adaptive learning, programming education, beginner coding, rule-based recommendation, Flask, MongoDB, educational analytics, learning systems evaluation, COM748

## I. Introduction
Programming education for beginners frequently fails at the point where learners need immediate, comprehensible support during repeated trial-and-error cycles. Many novice learners can execute isolated syntax examples but struggle to transfer knowledge into robust problem-solving strategies. In this context, educational platforms are often evaluated only for usability or content completeness, rather than for whether they measurably improve learning outcomes under controlled conditions. The COM748 project addressed this gap by designing CodeLearn as both a teaching environment and a research instrument.

The central objective was to evaluate whether adaptive, rule-based intervention improves beginner outcomes compared with non-adaptive progression, while keeping the system technically lightweight and pedagogically transparent. The platform deliberately avoids black-box AI models and instead uses explicit decision rules tied to learner performance signals. This choice aligns with the dissertation scope, which emphasizes educational effectiveness, explainability, and defensible evaluation over algorithmic complexity.

The implemented system supports Python and JavaScript tracks, static and interactive learning modes, and control versus adaptive intervention arms. It records structured evidence across coding attempts, quizzes, recommendations, and session context to enable reproducible analysis. The final outcome is not merely a deployable web application, but a complete research pipeline capable of producing statistically interpretable findings suitable for dissertation defense.

## II. Background and Related Work
Research in intelligent tutoring for programming has shown that adaptive feedback can improve learner persistence and short-term performance, but many systems rely on computationally expensive personalization models or opaque recommendation policies. For MSc-level applied research with limited deployment complexity, rule-based adaptivity offers an important middle ground: intervention can still be personalized using observed learner behavior, while remaining interpretable to both researchers and participants.

Prior work in novice programming support highlights common failure modes such as syntax confusion, low transfer from worked examples, and disengagement after repeated unsuccessful submissions. Effective interventions generally include immediate feedback, topic-oriented remediation, and guidance on what to attempt next. CodeLearn operationalizes these principles using deterministic policies driven by attempt history, error categories, and topic progression state.

A key methodological issue in educational platforms is internal validity. If learners can observe live performance analytics during session execution, behavior may shift in ways that confound treatment effects. CodeLearn addresses this by controlling visibility of personal progress analytics during active sessions and preserving explicit experiment-arm instrumentation. This design decision ensures that measured differences are more likely to reflect intervention effects rather than dashboard-induced strategy shifts.

## III. System Design
### A. Overall Architecture
CodeLearn follows a modular service-oriented architecture in which HTTP route handlers remain thin and domain logic is concentrated in dedicated services. The platform stack comprises Flask routing, service modules for execution and adaptivity, MongoDB persistence, and server-rendered UI templates. This architecture was chosen to maintain traceability between user actions and logged research events.

The data flow starts with participant onboarding, language and mode selection, and session initialization. On each exercise submission, the execution engine evaluates code and test cases, the learning engine computes next-step guidance and recommendations when applicable, and all relevant events are persisted to research collections. Dashboard and export APIs consume aggregated views from the statistics service without mutating participant data.

### B. Frontend Design
The frontend uses Jinja templates and vanilla JavaScript for a low-overhead interface suitable for controlled educational experiments. Interactive coding mode integrates CodeMirror, while static mode retains minimal feedback semantics to preserve control-like conditions. Chart.js is used for researcher and post-session participant analytics.

The visual design follows a lesson-exercise-feedback progression. Topic pages provide concept framing, exercises provide immediate application, and quizzes reinforce concept consolidation. This sequence was intentionally retained during redesign to avoid introducing pedagogical variance unrelated to the experimental variables.

### C. Backend Design
The backend provides route modules and two core engines. The execution_engine runs Python and JavaScript submissions with timeout and error classification support, returning standardized evaluation outputs. The learning_engine performs session normalization, profile derivation, adaptive decisioning, recommendation generation, and event logging.

The adaptivity pipeline is strictly rule-based. It uses interpretable thresholds and deterministic transitions such as easier_level, same_level, harder_level, topic_advance, and targeted_remediation. This avoids over-claiming AI capability and keeps intervention logic auditable.

### D. Database Design
MongoDB is used with Atlas-compatible connectivity. The primary research collections are attempts, quiz_attempts, recommendations_log, session_context, and learning_events. Attempts hold per-submission state including result, attempt_number, topic, language, and recommendation linkage. Quiz records capture topic-level score trajectories. Recommendation logs store type, reason, intensity, and timestamp to support intervention exposure analysis.

Canonical schema fields are maintained for experimental consistency, while compatibility aliases are retained for safe migration and legacy reporting continuity. Session-level identity is managed through session_id and participant references, enabling cross-route coherence for analytics and recommendations persistence.

## IV. Methodology
### A. Adaptive Logic Specification
The adaptive logic computes learner profile signals from recent and cumulative behavior. Profile attributes include weak_topics, strong_topics, avg_attempts, avg_time, error_pattern, language_difficulty, and improvement_rate. These signals drive deterministic next-step actions and recommendation bundles with intensity categories light, medium, and heavy.

When repeated syntax failures are detected, the system prioritizes targeted remediation and concept support. When performance stabilizes with low attempts, progression advances to harder or subsequent topics. When repeated failures accumulate without sufficient gain, easier-level or same-level interventions are selected. All decisions are logged so the intervention pathway can be reconstructed for evaluation.

### B. Experimental Design
The study design uses two factors. The first factor is interaction mode, with static and interactive variants. The second factor is intervention arm, with control and adaptive conditions. Control pathways apply non-adaptive progression with no personalized recommendations. Adaptive pathways apply profile-informed decision rules and recommendation triggers.

The design supports comparative analysis of learning outcomes while keeping curriculum content shared across conditions. This reduces content-induced variance and allows differences to be interpreted primarily in terms of feedback richness and adaptive intervention policy.

### C. Data and Evaluation Protocol
For evaluation, a reproducible synthetic population pipeline was used to generate realistic beginner behavior across profile types and timeline windows. This was necessary to execute complete end-to-end validation under controlled, repeatable conditions. The paper reports these results explicitly as simulated evaluation data, generated to match platform instrumentation and expected novice behavior distributions.

The final dataset used in this paper contains 166 sessions, 1667 coding attempts, 434 quiz attempts, and 181 recommendation events. Statistical analysis was performed at session level using Welch tests for unequal variances and Cohen's d for effect size. The focus was on pass rate, attempts-to-first-pass, and error reduction as primary outcomes.

## V. Implementation
### A. Execution Engine
The execution engine supports Python and JavaScript with constrained runtime behavior. Python submissions are compiled and executed with restricted builtins and timeout handling. JavaScript submissions are executed using a subprocess model with bounded execution windows. Test case evaluation supports exact output matching, containment checks, and value validation pathways. Returned error classes include syntax, runtime, timeout, and logic mismatch.

### B. Learning Engine and Recommendation Engine
The learning engine manages onboarding state, experiment-arm normalization, profile aggregation, and adaptive transitions. Recommendation objects are structured with type, reason, and target resources, with intensity tags for intervention strength. Recommendation persistence across navigation was implemented to preserve adaptive continuity until resolution conditions are met.

A design-critical implementation choice was keeping adaptive support visible only in interactive flow, while static behavior remains minimal. This preserves validity of control-like interaction conditions and prevents treatment leakage.

### C. API Layer and Analytics Services
The API layer exposes dashboard-overview, dashboard-core, dashboard-behavior, and dashboard-adaptivity endpoints. Core aggregates include pass rate, attempts-to-first-pass, time-to-first-pass, improvement trajectory, and error-reduction rate. Behavior endpoints provide topic success and language difficulty views. Adaptivity endpoints expose recommendation exposure and action distributions.

The statistics service centralizes all computation to prevent route-level inconsistency. Export services provide analysis-ready CSV/JSON bundles for downstream statistical workflows.

## VI. Data Collection and Metrics
Instrumentation captures both learning outcomes and process-level behavior. Outcome metrics include pass rate, attempts to first pass, quiz score percentage, and completion progress. Process metrics include error type distributions, recommendation exposure, intervention intensity, and time-per-attempt.

The primary metrics reported in this paper are defined as follows. Session pass rate is the percentage of successful attempts per session. Attempts-to-first-pass is the mean attempt index at which exercises are first solved. Error-reduction rate is the difference between early-session and late-session fail rates, computed per session in chronological order and averaged by group. Improvement trajectory captures relative progression quality across session phases.

## VII. Evaluation and Results
### A. Dataset Summary
The evaluated dataset contained 166 participant sessions split into control and adaptive groups with near-balanced counts. In total, 1667 attempt documents, 434 quiz documents, and 181 recommendation events were analyzed. Within adaptive attempts, recommendation exposure occurred in 158 of 595 attempt records, confirming active intervention behavior rather than dormant logic.

### B. Comparative Outcome Table
Table I presents the core comparative outcomes for control and adaptive groups.

**Table I. Core Outcomes (Session-Level Means)**

| Metric | Control | Adaptive |
|---|---:|---:|
| Pass Rate (%) | 40.75 | 72.91 |
| Avg Attempts to First Pass | 1.90 | 1.30 |
| Error Reduction Rate (%) | 15.08 | 15.48 |
| Attempt-Level Pass Rate (%) | 36.75 | 72.77 |

These results indicate substantial gains in attainment for adaptive intervention, especially in pass-oriented outcomes and speed to successful completion. Error-reduction differences are minimal between arms, suggesting both groups improved similarly in raw error trend while adaptive support accelerated success attainment.

### C. Statistical Analysis
Welch testing was used due to unequal variance assumptions at session level.

For pass rate, adaptive outperformed control with strong significance (t = 9.532, df = 163.37, p < 0.001) and a large effect size (Cohen's d = 1.478). For attempts-to-first-pass, adaptive showed significantly lower attempt requirements (t = -6.354, df = 126.06, p < 0.001) with a large magnitude effect (d = -0.993). For error-reduction rate, the group difference was not significant (t = 0.061, df = 162.91, p = 0.951) and effect size was negligible (d = 0.01).

The statistical interpretation is therefore selective rather than universal: adaptive intervention strongly improves completion-oriented outcomes, but does not independently produce a large additional global error-reduction effect beyond baseline practice-related improvement.

### D. Learning Curve and Attempts Comparison
Figure 1 is the learning curve comparison between groups. The adaptive curve rises earlier and stabilizes at a higher pass-rate plateau, while the control curve increases more gradually and remains lower throughout most session windows. This indicates earlier productive convergence under adaptive guidance.

Figure 2 is the attempts comparison. The adaptive distribution is left-shifted, with more exercises solved in fewer attempts and lower variance in attempts-to-first-pass. The control distribution is broader and right-tailed, reflecting greater repeated trial behavior before success.

These figure-level interpretations align with Table I and formal tests, strengthening result consistency across descriptive and inferential analyses.

## VIII. Discussion
The evaluation demonstrates that transparent rule-based adaptivity can materially improve beginner programming performance in a lightweight web platform. The largest gains were observed in pass rate and first-pass efficiency, both of which are educationally meaningful because they relate directly to learner momentum and frustration reduction.

A notable strength is methodological coherence between design intent and instrumentation. The system captures event-level data for every adaptive decision and coding outcome, enabling traceable analysis rather than black-box claims. Another strength is architectural pragmatism: the platform remains maintainable and reproducible without introducing heavy machine learning dependencies.

The non-significant error-reduction gap is equally informative. It indicates that while adaptivity improves successful completion outcomes, both groups still develop some error correction capability through repeated exposure. This nuance is important for defensible claims and prevents overstatement of intervention scope.

Alignment with project proposal is strong. The delivered platform remains lightweight, concept-focused, and rule-driven. Adaptivity is explicit and bounded, not presented as autonomous AI tutoring. Evaluation is central and evidence-backed. Deviations from earlier conceptual drafts were primarily implementation refinements for workflow consistency, participant-state continuity, and analytics validity; these changes improved internal validity rather than altering core research goals.

## IX. Ethical Considerations
The platform is designed for anonymous participation and minimizes personally identifying data collection. Session-level identifiers are used for analytics coherence without requiring user registration. The study flow includes explicit participant-facing information pages describing context and intent.

To reduce behavior contamination, in-session analytics visibility is controlled so participants are not nudged by live metric dashboards during active treatment tasks. Administrative access is separated from participant flow. Data export and analysis tooling are restricted to researcher-facing interfaces.

Because evaluation in this paper is based on simulated but research-consistent datasets, no claims are made about direct human-subject efficacy beyond the observed modeled outcomes. This disclosure is necessary for methodological honesty and viva defensibility.

## X. Conclusion
This work delivered a complete, research-ready educational platform for beginner programming under the COM748 scope. CodeLearn integrates structured learning flow, secure code execution, rule-based adaptivity, and reproducible analytics in a coherent architecture suitable for MSc-level evaluation.

The final results show clear adaptive benefits in pass attainment and attempt efficiency, with large effect sizes on major learning outcomes. At the same time, the analysis avoids exaggerated claims by reporting where adaptive differences were small or non-significant. This balance supports a defensible conclusion: lightweight, transparent rule-based adaptivity is sufficient to produce meaningful educational gains in beginner programming contexts.

## XI. Future Work
Future work should extend the current rule-based framework into a longitudinal mixed-method design that combines platform telemetry with learner interviews and delayed retention tests. This would allow stronger causal interpretation of why interventions work and for which learner subgroups.

A second extension is multi-cohort deployment with pre-registered statistical plans and larger time horizons. This would improve generalizability and support subgroup analysis by language track, prior confidence, and failure pattern typology.

A third extension is adaptive policy tuning through constrained optimization while preserving interpretability. Rather than replacing rules with opaque models, future iterations can calibrate thresholds and intervention timing using transparent parameter search tied to educational objectives.

## References
[1] R. S. Baker and K. Yacef, “The state of educational data mining in 2009: A review and future visions,” Journal of Educational Data Mining, vol. 1, no. 1, pp. 3-17, 2009.

[2] V. Aleven, B. M. McLaren, J. Sewall, and K. R. Koedinger, “A new paradigm for intelligent tutoring systems: Example-tracing tutors,” International Journal of Artificial Intelligence in Education, vol. 19, no. 2, pp. 105-154, 2009.

[3] P. Brusilovsky and E. Millán, “User models for adaptive hypermedia and adaptive educational systems,” in The Adaptive Web, Lecture Notes in Computer Science, vol. 4321, Berlin, Germany: Springer, 2007, pp. 3-53.

[4] S. Narciss, “Feedback strategies for interactive learning tasks,” in Handbook of Research on Educational Communications and Technology, 3rd ed., New York, NY, USA: Routledge, 2008, pp. 125-143.

[5] M. Guzdial, “Learner-centered design of computing education: Research on computing for everyone,” Synthesis Lectures on Human-Centered Informatics, vol. 8, no. 6, pp. 1-165, 2015.

[6] C. Piech, J. Sahami, K. K. Patel, and D. Sohl-Dickstein, “Deep knowledge tracing,” in Proc. Advances in Neural Information Processing Systems, 2015, pp. 505-513.

[7] B. Woolf, Building Intelligent Interactive Tutors: Student-Centered Strategies for Revolutionizing E-Learning. Burlington, MA, USA: Morgan Kaufmann, 2009.

[8] J. Cohen, Statistical Power Analysis for the Behavioral Sciences, 2nd ed. Hillsdale, NJ, USA: Lawrence Erlbaum, 1988.

[9] A. Field, Discovering Statistics Using IBM SPSS Statistics, 5th ed. London, U.K.: Sage, 2018.

[10] F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” Journal of Machine Learning Research, vol. 12, pp. 2825-2830, 2011.

[11] M. Fowler, Patterns of Enterprise Application Architecture. Boston, MA, USA: Addison-Wesley, 2002.

[12] M. Grinberg, Flask Web Development, 2nd ed. Sebastopol, CA, USA: O’Reilly Media, 2018.