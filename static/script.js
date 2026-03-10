/**
 * COM748 Research Platform v1.2 — script.js
 * CodeMirror init, form loading state, success animation, reset button.
 */

document.addEventListener('DOMContentLoaded', function () {

  /* ── CodeMirror Initialisation ── */
  const textarea = document.getElementById('code-editor');
  let cmEditor = null;

  if (textarea) {
    // Wait a tick for CodeMirror CDN to load
    setTimeout(function () {
      if (typeof CodeMirror !== 'undefined') {
        cmEditor = CodeMirror.fromTextArea(textarea, {
          mode: 'python',
          theme: 'dracula',
          lineNumbers: true,
          indentUnit: 4,
          tabSize: 4,
          indentWithTabs: false,
          lineWrapping: false,
          matchBrackets: true,
          autoCloseBrackets: true,
          extraKeys: {
            'Ctrl-Enter': function () { submitForm(); },
            'Cmd-Enter': function () { submitForm(); },
            'Tab': function (cm) {
              if (cm.somethingSelected()) { cm.indentSelection('add'); }
              else { cm.replaceSelection('    ', 'end'); }
            }
          }
        });
        cmEditor.setSize(null, 260);
      }
    }, 100);
  }

  /* ── Form Submission with Loading State ── */
  const form = document.getElementById('submit-form');
  const runBtn = document.getElementById('run-btn') || document.querySelector('button[type="submit"]');

  function submitForm() {
    if (cmEditor) cmEditor.save();  // flush CodeMirror → textarea
    if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
  }

  if (form) {
    form.addEventListener('submit', function () {
      if (runBtn) {
        runBtn.disabled = true;
        runBtn.innerHTML = '<span class="spinner"></span> Running…';
      }
    });
  }

  /* ── Reset Button ── */
  const resetBtn = document.getElementById('reset-btn');
  if (resetBtn && cmEditor) {
    resetBtn.addEventListener('click', function () {
      const starterCode = textarea.dataset.starter || '';
      cmEditor.setValue(starterCode);
      cmEditor.focus();
    });
  }

  /* ── Scroll to Feedback Panel ── */
  const feedbackPanel = document.getElementById('feedback-panel');
  if (feedbackPanel) {
    feedbackPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

});
