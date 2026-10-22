/**
 * Pramana - Interactive Web Application Logic
 * Supports Learn Mode, Debug Mode (Bug DNA), Game Arena, and Evidence RAG.
 */

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

// App State
const state = {
    currentTab: 'overview',
    userXp: parseInt(localStorage.getItem('pramana_user_xp') || '0', 10),
    solvedChallenges: JSON.parse(localStorage.getItem('pramana_solved') || '[]'),
    challenges: [],
    currentGameFilter: 'all',
    currentDifficultyFilter: 'all',
    activeChallenge: null,
    learnLinesData: [],
    systemStatus: null
};

// Preset Code Snippets for Instant Testing
const PRESETS = {
    'c_bst_insert': {
        language: 'cpp',
        description: 'Binary Search Tree insertion matching trees.pdf page 1',
        code: `// Binary Search Tree insertion (grounded in trees.pdf)
struct Node* insert(struct Node* root, int value) {
    // If the tree/subtree is empty, create and return a new node
    if (root == NULL) {
        return createNode(value);
    }
    // Otherwise, recur down the tree
    if (value < root->data) {
        root->left = insert(root->left, value);
    } else if (value > root->data) {
        root->right = insert(root->right, value);
    }
    return root;
}`
    },
    'c_inorder': {
        language: 'cpp',
        description: 'In-order traversal displaying BST nodes in sorted order from trees.pdf page 2',
        code: `// Helper function to print tree in-order from trees.pdf
void inorderTraversal(struct Node* root) {
    if (root != NULL) {
        inorderTraversal(root->left);
        printf("%d ", root->data);
        inorderTraversal(root->right);
    }
}`
    },
    'cpp_factorial': {
        language: 'cpp',
        description: 'Loop condition i < n excludes n, producing 24 instead of 120 for factorial(5)',
        code: `unsigned int factorial(unsigned int n) {
    int res = 1;
    for (int i = 2; i < n; i++)
        res *= i;
    return res;
}`
    },
    'off_by_one': {
        language: 'python',
        description: 'Loop throws IndexError when accessing prices[i]',
        code: `def calculate_total(prices):
    total = 0
    # Bug: Loop attempts to access index len(prices), which is out of bounds
    for i in range(len(prices) + 1):
        total += prices[i]
    return total

items = [10, 20, 30]
print("Total:", calculate_total(items))`
    },
    'mutable_default': {
        language: 'python',
        description: 'User tasks unexpectedly accumulate across different function calls',
        code: `def register_user(username, roles=[]):
    # Bug: roles list persists and mutates across all function calls
    roles.append("student")
    return {"user": username, "roles": roles}

alice = register_user("Alice")
bob = register_user("Bob")
print("Alice:", alice)
print("Bob:", bob) # Unexpectedly contains two 'student' roles!`
    },
    'type_mismatch': {
        language: 'python',
        description: 'TypeError: cannot concatenate str and int directly',
        code: `def generate_user_badge(name, score):
    # Bug: String concatenation with un-cast integer score
    header = "Player: " + name
    stats = header + " - XP: " + score
    return stats

print(generate_user_badge("PramanaUser", 150))`
    },
    'slicing': {
        language: 'python',
        description: 'Clean string reversal with slice step',
        code: `def is_palindrome(word):
    # Traverses sequence backwards with negative step
    clean = word.lower().strip()
    reversed_word = clean[::-1]
    return clean == reversed_word

print("Pramana is palindrome?", is_palindrome("Pramana"))
print("Radar is palindrome?", is_palindrome("Radar"))`
    }
};

function initApp() {
    setupLineNumbers();
    setupNavigation();
    setupLearnMode();
    setupDebugMode();
    setupGameMode();
    setupDocsMode();
    checkSystemStatus();
    updateXpDisplay();
}

/* ==========================================================================
   SYSTEM STATUS & XP MANAGEMENT
   ========================================================================== */
async function checkSystemStatus() {
    try {
        const res = await fetch('/api/status/');
        const data = await res.json();
        state.systemStatus = data;

        const pill = document.getElementById('ai-status-pill');
        if (pill) {
            if (data.has_api_key) {
                pill.className = 'status-pill online';
                pill.innerHTML = `<i class="bi bi-check-circle-fill"></i> AI Active (${data.gemini_model})`;
            } else if (data.diagnostic && data.diagnostic.is_placeholder) {
                pill.className = 'status-pill warning';
                pill.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> GEMINI_API_KEY is placeholder`;
            } else {
                pill.className = 'status-pill warning';
                pill.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> GEMINI_API_KEY Missing`;
            }
        }

        const docCounter = document.getElementById('status-doc-count');
        if (docCounter) {
            docCounter.textContent = `${data.total_documents} Docs (${data.total_indexed_chunks} Chunks)`;
        }
    } catch (e) {
        console.warn("Status check failed", e);
    }
}

function updateXpDisplay() {
    const xpEl = document.getElementById('user-xp-counter');
    const levelEl = document.getElementById('user-level-badge');
    if (xpEl) xpEl.textContent = `${state.userXp} XP`;
    
    // Level computation: 100 XP per level
    const level = Math.floor(state.userXp / 100) + 1;
    if (levelEl) levelEl.textContent = `Lvl ${level}`;
}

function addXp(amount) {
    state.userXp += amount;
    localStorage.setItem('pramana_user_xp', state.userXp.toString());
    updateXpDisplay();
}

/* ==========================================================================
   NAVIGATION & TABS
   ========================================================================== */
function switchTab(targetTab) {
    if (!targetTab) return;
    state.currentTab = targetTab;

    // Update navigation pill active state
    document.querySelectorAll('.nav-link[data-tab]').forEach(l => {
        if (l.getAttribute('data-tab') === targetTab) {
            l.classList.add('active');
        } else {
            l.classList.remove('active');
        }
    });

    // Toggle tab sections
    document.querySelectorAll('.tab-section').forEach(sec => {
        sec.classList.add('d-none');
    });
    const activeSection = document.getElementById(`section-${targetTab}`);
    if (activeSection) {
        activeSection.classList.remove('d-none');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (targetTab === 'game') {
        loadChallenges();
    } else if (targetTab === 'docs') {
        loadDocumentsList();
    }
}

function setupNavigation() {
    // Nav bar tab links
    document.querySelectorAll('.nav-link[data-tab]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetTab = link.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });

    // Any button or link with data-switch-tab
    document.querySelectorAll('[data-switch-tab]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetTab = btn.getAttribute('data-switch-tab');
            switchTab(targetTab);
        });
    });
}

/* ==========================================================================
   CODE EDITOR LINE NUMBER SYNCHRONIZATION
   ========================================================================== */
function setupLineNumbers() {
    const editors = [
        { textarea: document.getElementById('learn-code-input'), lines: document.getElementById('learn-line-numbers') },
        { textarea: document.getElementById('debug-code-input'), lines: document.getElementById('debug-line-numbers') }
    ];

    editors.forEach(ed => {
        if (!ed.textarea || !ed.lines) return;

        const updateNumbers = () => {
            const count = (ed.textarea.value.split('\n')).length;
            let html = '';
            for (let i = 1; i <= Math.max(count, 1); i++) {
                html += `<span class="line-num">${i}</span>`;
            }
            ed.lines.innerHTML = html;
        };

        ed.textarea.addEventListener('input', updateNumbers);
        ed.textarea.addEventListener('scroll', () => {
            ed.lines.scrollTop = ed.textarea.scrollTop;
        });

        updateNumbers();
    });

    // Preset Buttons
    document.querySelectorAll('[data-load-preset]').forEach(btn => {
        btn.addEventListener('click', () => {
            const presetKey = btn.getAttribute('data-load-preset');
            const preset = PRESETS[presetKey];
            if (!preset) return;

            // Highlight active preset
            document.querySelectorAll('[data-load-preset]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const learnInput = document.getElementById('learn-code-input');
            const debugInput = document.getElementById('debug-code-input');
            const debugDesc = document.getElementById('debug-problem-desc');
            const learnLang = document.getElementById('learn-language-select');
            const debugLang = document.getElementById('debug-language-select');

            if (preset.language) {
                if (learnLang) learnLang.value = preset.language;
                if (debugLang) debugLang.value = preset.language;
            }

            if (learnInput) {
                learnInput.value = preset.code;
                learnInput.dispatchEvent(new Event('input'));
            }
            if (debugInput) {
                debugInput.value = preset.code;
                debugInput.dispatchEvent(new Event('input'));
            }
            if (debugDesc) {
                debugDesc.value = preset.description;
            }

            // If on overview, switch smoothly to the appropriate workspace
            if (state.currentTab === 'overview') {
                if (presetKey.includes('factorial') || presetKey.includes('off_by_one') || presetKey.includes('mutable') || presetKey.includes('type')) {
                    switchTab('debug');
                } else {
                    switchTab('learn');
                }
            }
        });
    });
}

/* ==========================================================================
   LEARN MODE: LINE-BY-LINE EXPLAINER
   ========================================================================== */
function setupLearnMode() {
    const explainBtn = document.getElementById('btn-learn-explain');
    if (!explainBtn) return;

    explainBtn.addEventListener('click', async () => {
        const code = document.getElementById('learn-code-input').value;
        const language = document.getElementById('learn-language-select').value;
        const resultContainer = document.getElementById('learn-results-container');
        const emptyState = document.getElementById('learn-empty-state');
        const spinner = document.getElementById('learn-spinner');
        const timerBadge = document.getElementById('learn-timer');

        if (!code.trim()) {
            showModalAlert('Input Required', 'Please paste or write code first before explaining.');
            return;
        }

        explainBtn.disabled = true;
        spinner.classList.remove('d-none');
        resultContainer.classList.add('d-none');
        emptyState.classList.add('d-none');

        let startTime = Date.now();
        let timerInterval = null;
        if (timerBadge) {
            timerBadge.textContent = '0.0s';
            timerBadge.classList.remove('d-none');
            timerInterval = setInterval(() => {
                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                timerBadge.textContent = `${elapsed}s`;
            }, 100);
        }

        try {
            const res = await fetch('/api/learn/explain/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, language })
            });

            const data = await res.json();
            if (!data.success) {
                const errTitle = data.error_type === 'API_KEY_MISSING' ? 'AI Key Required' : 'Learn Mode Notice';
                showModalAlert(errTitle, data.error || 'Failed to explain code.');
                emptyState.classList.remove('d-none');
                return;
            }

            renderLearnResults(data, code);
            resultContainer.classList.remove('d-none');
        } catch (e) {
            showModalAlert('Network Error', `Unable to communicate with Pramana server: ${e.message}`);
            emptyState.classList.remove('d-none');
        } finally {
            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }
            if (timerBadge) {
                timerBadge.classList.add('d-none');
            }
            explainBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    });
}

function renderLearnResults(data, originalCode) {
    state.learnLinesData = data.lines || [];

    // Duration badge
    const durationBadge = document.getElementById('learn-duration-badge');
    if (durationBadge) {
        if (data.retrieval_duration_seconds !== undefined && data.generation_duration_seconds !== undefined) {
            durationBadge.textContent = `⚡ ${data.duration_seconds}s (Retrieval: ${data.retrieval_duration_seconds}s, AI: ${data.generation_duration_seconds}s)`;
        } else if (data.duration_seconds) {
            durationBadge.textContent = `⚡ ${data.duration_seconds}s response`;
        } else {
            durationBadge.textContent = '';
        }
    }

    // A. Program Purpose
    const summaryEl = document.getElementById('learn-summary-text');
    if (summaryEl) {
        summaryEl.textContent = data.summary || data.program_summary || 'Analysis complete.';
    }

    // B. How It Works (Execution Flow)
    const flowContainer = document.getElementById('learn-flow-steps');
    if (flowContainer) {
        const flowSteps = Array.isArray(data.execution_flow) ? data.execution_flow : (data.program_flow ? [data.program_flow] : []);
        if (flowSteps.length > 0) {
            flowContainer.innerHTML = flowSteps.map((step, idx) => `
                <div class="flow-step-item">
                    <span class="flow-step-badge">${idx + 1}</span>
                    <span class="text-light">${escapeHtml(step.replace(/^Step\s*\d+:\s*/i, ''))}</span>
                </div>
            `).join('');
        } else {
            flowContainer.innerHTML = `<p class="text-secondary small mb-0">${escapeHtml(data.program_flow || 'Executes sequentially.')}</p>`;
        }
    }

    // C. Line-by-Line Code Inspector
    const viewer = document.getElementById('learn-interactive-lines');
    if (viewer) {
        viewer.innerHTML = '';
        const lines = originalCode.split('\n');
        lines.forEach((lineText, idx) => {
            const lineNum = idx + 1;
            const row = document.createElement('div');
            row.className = 'code-line-row';
            row.setAttribute('data-line', lineNum);
            row.innerHTML = `
                <div class="row-number">${lineNum}</div>
                <div class="row-content">${escapeHtml(lineText || ' ')}</div>
            `;

            row.addEventListener('click', () => {
                selectLearnLine(lineNum, row);
            });

            viewer.appendChild(row);
        });

        // Automatically select Line 1 or first line
        if (lines.length > 0) {
            const firstRow = viewer.querySelector('.code-line-row');
            if (firstRow) selectLearnLine(1, firstRow);
        }
    }

    // D. Output & Execution Trace
    const trace = data.trace || {};
    const inputEl = document.getElementById('learn-trace-input');
    const actualEl = document.getElementById('learn-trace-actual');
    const expectedEl = document.getElementById('learn-trace-expected');
    const tableBody = document.getElementById('learn-trace-table-body');
    const discEl = document.getElementById('learn-trace-discrepancy');

    if (inputEl) inputEl.textContent = trace.sample_input || 'N/A';
    if (actualEl) actualEl.textContent = trace.actual_output || 'N/A';
    if (expectedEl) expectedEl.textContent = trace.expected_output || 'N/A';

    if (tableBody) {
        const iters = Array.isArray(trace.iterations) ? trace.iterations : [];
        if (iters.length > 0) {
            tableBody.innerHTML = iters.map(it => `
                <tr>
                    <td class="font-monospace text-warning fw-semibold">${escapeHtml(it.step || '')}</td>
                    <td class="text-light">${escapeHtml(it.values || '')}</td>
                </tr>
            `).join('');
        } else {
            tableBody.innerHTML = `<tr><td colspan="2" class="text-muted small">No step-by-step loop trace needed for this program.</td></tr>`;
        }
    }

    if (discEl) {
        if (trace.discrepancy_explanation) {
            discEl.innerHTML = `<i class="bi bi-exclamation-circle-fill me-1"></i> <strong>Execution Analysis:</strong> ${escapeHtml(trace.discrepancy_explanation)}`;
            discEl.classList.remove('d-none');
        } else {
            discEl.classList.add('d-none');
        }
    }

    // E. Important Concepts
    const conceptsContainer = document.getElementById('learn-concepts-list');
    if (conceptsContainer) {
        const concepts = Array.isArray(data.concepts) ? data.concepts : [];
        if (concepts.length > 0) {
            conceptsContainer.innerHTML = concepts.map(c => `
                <div class="col-md-6">
                    <div class="p-2 rounded bg-dark border border-secondary h-100">
                        <strong class="text-info small d-block mb-1"><i class="bi bi-bookmark-check-fill me-1"></i>${escapeHtml(c.name || 'Core Concept')}</strong>
                        <p class="text-secondary small mb-0">${escapeHtml(c.explanation || '')}</p>
                    </div>
                </div>
            `).join('');
        } else {
            conceptsContainer.innerHTML = `<div class="col-12 text-muted small">No specific advanced concepts flagged.</div>`;
        }
    }

    // Evidence Grounding & Document Verification (Real RAG)
    const evidenceBanner = document.getElementById('learn-evidence-banner');
    const evidencePill = document.getElementById('learn-evidence-status-pill');
    const passagesList = document.getElementById('learn-evidence-passages-list');

    if (passagesList) {
        passagesList.innerHTML = '';
        const ev = data.evidence_trail;
        if (ev && ev.has_evidence && ev.passages && ev.passages.length > 0) {
            if (evidenceBanner) {
                evidenceBanner.className = 'alert alert-info py-2 small mb-2';
                evidenceBanner.innerHTML = `<i class="bi bi-journal-bookmark-fill me-1"></i> <strong>Verified Corpus Grounding:</strong> ${escapeHtml(ev.message)}`;
            }
            if (evidencePill) {
                evidencePill.className = 'badge bg-info text-dark small fw-bold';
                evidencePill.textContent = `${ev.passages.length} Verified Passage(s)`;
            }

            ev.passages.forEach(p => {
                const card = document.createElement('div');
                card.className = 'evidence-card';
                card.innerHTML = `
                    <div class="evidence-header">
                        <span class="text-info fw-bold"><i class="bi bi-file-earmark-pdf-fill me-1"></i> ${escapeHtml(p.filename)} (Page ${p.page_number})</span>
                        <span class="badge bg-secondary font-monospace">Cosine Sim: ${p.similarity_score}</span>
                    </div>
                    <div class="evidence-passage-text">${escapeHtml(p.text)}</div>
                `;
                passagesList.appendChild(card);
            });
        } else {
            if (evidenceBanner) {
                evidenceBanner.className = 'alert alert-secondary py-2 small mb-2';
                evidenceBanner.innerHTML = `<i class="bi bi-info-circle me-1"></i> ${ev && ev.message ? escapeHtml(ev.message) : 'No matching documentation passages found in uploaded corpus. Analysis relies on general programming principles.'}`;
            }
            if (evidencePill) {
                evidencePill.className = 'badge bg-dark border border-secondary text-muted small';
                evidencePill.textContent = 'General AI Knowledge';
            }
        }
    }

    // F. Suggested Improvement
    const impContainer = document.getElementById('learn-improvement-container');
    const imp = data.improvement || {};
    if (impContainer) {
        if (imp.has_issue) {
            impContainer.classList.remove('d-none');
            const titleEl = document.getElementById('learn-improvement-title');
            const descEl = document.getElementById('learn-improvement-desc');
            const codeEl = document.getElementById('learn-improvement-code');
            const changeEl = document.getElementById('learn-improvement-change');

            if (titleEl) titleEl.textContent = imp.issue_title || 'Identified Logical Issue';
            if (descEl) descEl.textContent = imp.issue_description || '';
            if (codeEl) codeEl.textContent = imp.corrected_code || '';
            if (changeEl) {
                changeEl.innerHTML = `<strong>Correction details:</strong> ${escapeHtml(imp.explanation_of_change || '')}`;
            }

            const copyBtn = document.getElementById('btn-copy-learn-fix');
            if (copyBtn) {
                copyBtn.onclick = () => {
                    if (imp.corrected_code) {
                        navigator.clipboard.writeText(imp.corrected_code).then(() => {
                            const origHtml = copyBtn.innerHTML;
                            copyBtn.innerHTML = '<i class="bi bi-check2 me-1"></i>Copied!';
                            setTimeout(() => { copyBtn.innerHTML = origHtml; }, 2000);
                        });
                    }
                };
            }
        } else {
            impContainer.classList.add('d-none');
        }
    }
}

function selectLearnLine(lineNum, rowElement) {
    document.querySelectorAll('#learn-interactive-lines .code-line-row').forEach(r => {
        r.classList.remove('active-line');
    });
    if (rowElement) rowElement.classList.add('active-line');

    const detailBox = document.getElementById('learn-line-detail');
    if (!detailBox) return;

    const lineInfo = state.learnLinesData.find(l => l.line_number === lineNum);

    if (!lineInfo) {
        detailBox.innerHTML = `
            <div class="text-secondary small">
                <i class="bi bi-info-circle me-1"></i> Line ${lineNum}: Empty or comment line without executable statements.
            </div>
        `;
        return;
    }

    if (lineInfo.is_blank) {
        detailBox.innerHTML = `
            <div class="d-flex align-items-center gap-2 mb-2">
                <span class="badge bg-secondary text-white fw-bold">Line ${lineNum}</span>
                <span class="text-muted small">Blank Line</span>
            </div>
            <p class="text-secondary small mb-0"><i class="bi bi-info-circle me-1"></i> ${escapeHtml(lineInfo.what || 'Blank line for vertical spacing.')}</p>
        `;
        return;
    }

    if (lineInfo.is_structural) {
        detailBox.innerHTML = `
            <div class="d-flex align-items-center gap-2 mb-2">
                <span class="badge bg-dark border border-secondary text-light fw-bold">Line ${lineNum}</span>
                <span class="text-info small">Structural Delimiter</span>
            </div>
            <div class="mb-2">
                <strong class="text-info small"><i class="bi bi-braces me-1"></i> What It Does:</strong>
                <p class="text-light small mb-1">${escapeHtml(lineInfo.what)}</p>
            </div>
            <div>
                <strong class="text-primary small"><i class="bi bi-question-circle me-1"></i> Why It's Needed:</strong>
                <p class="text-secondary small mb-0">${escapeHtml(lineInfo.why)}</p>
            </div>
        `;
        return;
    }

    let conceptsHtml = '';
    if (lineInfo.concepts) {
        const items = typeof lineInfo.concepts === 'string' ? lineInfo.concepts.split(',') : lineInfo.concepts;
        conceptsHtml = items.map(c => `<span class="badge-concept">${escapeHtml(c.trim ? c.trim() : c)}</span>`).join('');
    }

    let exampleSection = '';
    if (lineInfo.example) {
        exampleSection = `
            <div class="mb-2">
                <strong class="text-warning small"><i class="bi bi-lightbulb me-1"></i> Concrete Example:</strong>
                <p class="text-light small mb-1 font-monospace bg-dark p-1 rounded border border-secondary">${escapeHtml(lineInfo.example)}</p>
            </div>
        `;
    }

    detailBox.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-indigo text-white fw-bold">Line ${lineNum}</span>
            <div>${conceptsHtml}</div>
        </div>
        <div class="mb-2">
            <strong class="text-info small"><i class="bi bi-arrow-right-circle me-1"></i> What It Does:</strong>
            <p class="text-light small mb-1">${escapeHtml(lineInfo.what || 'Executes this statement.')}</p>
        </div>
        <div class="mb-2">
            <strong class="text-primary small"><i class="bi bi-question-circle me-1"></i> Why It's Needed:</strong>
            <p class="text-secondary small mb-1">${escapeHtml(lineInfo.why || 'Necessary for program logic.')}</p>
        </div>
        ${exampleSection}
        <div class="mb-2">
            <strong class="text-success small"><i class="bi bi-link-45deg me-1"></i> Surrounding Connection:</strong>
            <p class="text-secondary small mb-1">${escapeHtml(lineInfo.connects || 'Connects with nearby logic.')}</p>
        </div>
        <div>
            <strong class="text-danger small"><i class="bi bi-exclamation-triangle me-1"></i> What If Changed or Removed?</strong>
            <p class="text-secondary small mb-0">${escapeHtml(lineInfo.what_if_changed || lineInfo.impact_if_removed || 'May cause unintended behavior or syntax error.')}</p>
        </div>
    `;

    // Ensure detail box is visible smoothly without page jump
    detailBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* ==========================================================================
   DEBUG MODE: BUG DNA & EVIDENCE TRAIL
   ========================================================================== */
function setupDebugMode() {
    const analyzeBtn = document.getElementById('btn-debug-analyze');
    if (!analyzeBtn) return;

    analyzeBtn.addEventListener('click', async () => {
        const code = document.getElementById('debug-code-input').value;
        const language = document.getElementById('debug-language-select').value;
        const problem_description = document.getElementById('debug-problem-desc').value;
        const resultsContainer = document.getElementById('debug-results-container');
        const emptyState = document.getElementById('debug-empty-state');
        const spinner = document.getElementById('debug-spinner');

        if (!code.trim()) {
            alert('Please paste code to debug.');
            return;
        }

        analyzeBtn.disabled = true;
        spinner.classList.remove('d-none');
        resultsContainer.classList.add('d-none');
        emptyState.classList.add('d-none');

        try {
            const res = await fetch('/api/debug/analyze/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, language, problem_description })
            });

            const data = await res.json();
            if (!data.success && data.error_type === 'API_KEY_MISSING') {
                // If API key is missing, show static AST verification results anyway!
                showModalAlert('AI Service Notice', data.error);
                if (data.static_check) {
                    renderStaticOnlyReport(data.static_check, code);
                    resultsContainer.classList.remove('d-none');
                } else {
                    emptyState.classList.remove('d-none');
                }
                return;
            }

            if (!data.success) {
                showModalAlert('Debug Analysis Notice', data.error || 'Failed to complete analysis.');
                emptyState.classList.remove('d-none');
                return;
            }

            renderDebugResults(data);
            resultsContainer.classList.remove('d-none');
        } catch (e) {
            showModalAlert('Error', `Network request error: ${e.message}`);
            emptyState.classList.remove('d-none');
        } finally {
            analyzeBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    });
}

function renderDebugResults(data) {
    // 1. Bug DNA Core Cards
    document.getElementById('dna-error-type').textContent = data.error_type || 'Logic Flaw';
    document.getElementById('dna-affected-line').textContent = `Line ${data.affected_line_number || '1'}: ${data.affected_expression || 'Expression'}`;
    document.getElementById('dna-root-cause').textContent = data.root_cause || 'Root cause identified.';
    document.getElementById('dna-visible-symptom').textContent = data.visible_symptom || 'Program crash / incorrect output.';
    document.getElementById('dna-why-occurs').textContent = data.why_occurs || '';
    document.getElementById('dna-likely-impact').textContent = data.likely_impact || '';
    document.getElementById('dna-beginner-explanation').textContent = data.beginner_explanation || '';
    document.getElementById('dna-change-summary').textContent = data.change_summary || '';

    // 2. Code Comparison Diff
    document.getElementById('diff-original-code').textContent = data.original_code || '';
    document.getElementById('diff-corrected-code').textContent = data.corrected_code || '';

    // 3. Fix Confidence Check (Section 9)
    const verif = data.verification || {};
    const badge = document.getElementById('verification-status-badge');
    const verdictText = document.getElementById('verification-verdict-text');
    const checksList = document.getElementById('verification-checks-list');
    const disclaimer = document.getElementById('verification-disclaimer');

    let badgeClass = 'unverified';
    if (verif.status === 'CHECKS PASSED') badgeClass = 'passed';
    else if (verif.status === 'CHECKS FAILED') badgeClass = 'failed';

    if (badge) {
        badge.className = `verification-badge ${badgeClass}`;
        let timingHtml = '';
        if (data.retrieval_duration_seconds !== undefined && data.generation_duration_seconds !== undefined) {
            timingHtml = ` <span class="badge bg-dark border border-secondary text-info ms-1 small font-monospace">⚡ ${data.duration_seconds}s (Retrieval: ${data.retrieval_duration_seconds}s, AI: ${data.generation_duration_seconds}s)</span>`;
        }
        badge.innerHTML = `<i class="bi bi-shield-check"></i> ${verif.status || 'NOT VERIFIED'}${timingHtml}`;
    }
    if (verdictText) verdictText.textContent = verif.verdict || '';
    if (disclaimer) disclaimer.textContent = verif.disclaimer || 'Static checks inspect AST syntax. Untested runtime logic remains unverified.';

    if (checksList) {
        checksList.innerHTML = '';
        (verif.checks_run || []).forEach(c => {
            const item = document.createElement('div');
            item.className = 'check-item';
            const icon = c.status === 'PASSED' ? '<i class="bi bi-check-circle-fill text-success"></i>' : (c.status === 'FAILED' ? '<i class="bi bi-x-circle-fill text-danger"></i>' : '<i class="bi bi-dash-circle text-warning"></i>');
            item.innerHTML = `
                ${icon}
                <div>
                    <strong class="text-light">${escapeHtml(c.name)}</strong>
                    <div class="text-secondary small">${escapeHtml(c.detail || '')}</div>
                </div>
            `;
            checksList.appendChild(item);
        });
    }

    // 4. Evidence Trail (Section 7)
    renderEvidenceTrail(data.evidence_trail, data.documentation_claims, data.ai_suggestions, data.unverified_claims);
}

function renderStaticOnlyReport(check, originalCode) {
    document.getElementById('dna-error-type').textContent = check.status === 'CHECKS PASSED' ? 'Valid Syntax' : 'SyntaxError';
    document.getElementById('dna-affected-line').textContent = 'Static AST Check';
    document.getElementById('dna-root-cause').textContent = check.verdict;
    document.getElementById('dna-visible-symptom').textContent = check.errors && check.errors.length ? check.errors[0] : 'No syntax errors found';
    document.getElementById('dna-why-occurs').textContent = check.verdict;
    document.getElementById('dna-likely-impact').textContent = 'Requires AI key to generate semantic diagnosis and automatic code correction.';
    document.getElementById('dna-beginner-explanation').textContent = 'Static Python AST parser verified your code structure safely without running it.';
    document.getElementById('dna-change-summary').textContent = 'Static analysis only (AI offline).';

    document.getElementById('diff-original-code').textContent = originalCode;
    document.getElementById('diff-corrected-code').textContent = originalCode;

    const badge = document.getElementById('verification-status-badge');
    if (badge) {
        badge.className = `verification-badge ${check.status === 'CHECKS PASSED' ? 'passed' : 'failed'}`;
        badge.innerHTML = `<i class="bi bi-shield-check"></i> ${check.status}`;
    }

    const checksList = document.getElementById('verification-checks-list');
    if (checksList) {
        checksList.innerHTML = '';
        (check.checks || []).forEach(c => {
            const item = document.createElement('div');
            item.className = 'check-item';
            const icon = c.status === 'PASSED' ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>';
            item.innerHTML = `${icon} <div><strong class="text-light">${escapeHtml(c.name)}</strong><div class="text-secondary small">${escapeHtml(c.detail || '')}</div></div>`;
            checksList.appendChild(item);
        });
    }

    renderEvidenceTrail({ has_evidence: false, message: 'AI key required for vector similarity retrieval.' }, [], ['Static code check completed without runtime execution.'], ['Dynamic behavior unverified.']);
}

function renderEvidenceTrail(evidenceTrail, docClaims, aiSuggestions, unverifiedClaims) {
    const container = document.getElementById('evidence-passages-list');
    const banner = document.getElementById('evidence-status-banner');
    if (!container) return;

    container.innerHTML = '';

    if (!evidenceTrail || !evidenceTrail.has_evidence || !evidenceTrail.passages || evidenceTrail.passages.length === 0) {
        if (banner) {
            banner.className = 'alert alert-secondary py-2 small';
            banner.innerHTML = `<i class="bi bi-info-circle me-1"></i> ${evidenceTrail ? evidenceTrail.message : 'No documentation passages matched this query. Explanations rely on general AI knowledge.'}`;
        }
    } else {
        if (banner) {
            banner.className = 'alert alert-info py-2 small';
            banner.innerHTML = `<i class="bi bi-journal-bookmark-fill me-1"></i> Grounded in ${evidenceTrail.passages.length} verified documentation passage(s).`;
        }

        evidenceTrail.passages.forEach((p, idx) => {
            const card = document.createElement('div');
            card.className = 'evidence-card';
            card.innerHTML = `
                <div class="evidence-header">
                    <span class="text-info fw-bold"><i class="bi bi-file-earmark-text me-1"></i> ${escapeHtml(p.filename)} (Page/Section ${p.page_number})</span>
                    <span class="badge bg-secondary font-monospace">Cosine Sim: ${p.similarity_score}</span>
                </div>
                <div class="evidence-passage-text">${escapeHtml(p.text)}</div>
            `;
            container.appendChild(card);
        });
    }

    // Claims separation
    const claimsContainer = document.getElementById('evidence-claims-breakdown');
    if (claimsContainer) {
        claimsContainer.innerHTML = '';

        if (docClaims && docClaims.length > 0) {
            claimsContainer.innerHTML += `
                <div class="mb-2">
                    <span class="claim-pill doc-backed"><i class="bi bi-check2-circle"></i> Documentation-Supported Claims</span>
                    <ul class="text-light small ps-3 mb-0">${docClaims.map(c => `<li>${escapeHtml(c)}</li>`).join('')}</ul>
                </div>
            `;
        }

        if (aiSuggestions && aiSuggestions.length > 0) {
            claimsContainer.innerHTML += `
                <div class="mb-2">
                    <span class="claim-pill ai-suggestion"><i class="bi bi-robot"></i> General AI Analytical Suggestions</span>
                    <ul class="text-light small ps-3 mb-0">${aiSuggestions.map(c => `<li>${escapeHtml(c)}</li>`).join('')}</ul>
                </div>
            `;
        }

        if (unverifiedClaims && unverifiedClaims.length > 0) {
            claimsContainer.innerHTML += `
                <div>
                    <span class="claim-pill unverified"><i class="bi bi-question-diamond"></i> Unverified Assumptions (Require Runtime Tests)</span>
                    <ul class="text-light small ps-3 mb-0">${unverifiedClaims.map(c => `<li>${escapeHtml(c)}</li>`).join('')}</ul>
                </div>
            `;
        }
    }
}

/* ==========================================================================
   GAME ARENA: THREE INTERACTIVE CODING GAMES
   ========================================================================== */
function setupGameMode() {
    // Game Type Selectors
    document.querySelectorAll('[data-game-type]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-game-type]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentGameFilter = btn.getAttribute('data-game-type');
            filterChallenges();
        });
    });

    // Difficulty Filters
    document.querySelectorAll('[data-difficulty]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-difficulty]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentDifficultyFilter = btn.getAttribute('data-difficulty');
            filterChallenges();
        });
    });

    // Reset Progress
    const resetBtn = document.getElementById('btn-reset-game-progress');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            if (confirm('Reset your earned XP and solved challenges?')) {
                localStorage.removeItem('pramana_user_xp');
                localStorage.removeItem('pramana_solved');
                state.userXp = 0;
                state.solvedChallenges = [];
                updateXpDisplay();
                loadChallenges();
            }
        });
    }
}

async function loadChallenges() {
    try {
        const res = await fetch('/api/games/');
        const data = await res.json();
        if (data.success) {
            state.challenges = data.challenges || [];
            filterChallenges();
        }
    } catch (e) {
        console.error("Failed to load challenges", e);
    }
}

function filterChallenges() {
    const listContainer = document.getElementById('game-challenges-list');
    if (!listContainer) return;
    listContainer.innerHTML = '';

    let filtered = state.challenges;
    if (state.currentGameFilter !== 'all') {
        filtered = filtered.filter(c => c.game_type === state.currentGameFilter);
    }
    if (state.currentDifficultyFilter !== 'all') {
        filtered = filtered.filter(c => c.difficulty.toLowerCase() === state.currentDifficultyFilter.toLowerCase());
    }

    if (filtered.length === 0) {
        listContainer.innerHTML = `<div class="p-4 text-center text-secondary small">No challenges found in this category.</div>`;
        return;
    }

    filtered.forEach(c => {
        const isSolved = state.solvedChallenges.includes(c.id);
        const card = document.createElement('div');
        card.className = `p-3 mb-2 rounded border ${state.activeChallenge && state.activeChallenge.id === c.id ? 'border-primary bg-card-hover' : 'border-secondary bg-surface'} cursor-pointer`;
        card.style.cursor = 'pointer';
        
        let diffColor = 'success';
        if (c.difficulty === 'Intermediate') diffColor = 'warning';
        if (c.difficulty === 'Advanced') diffColor = 'danger';

        card.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="badge bg-${diffColor} small">${c.difficulty}</span>
                <span class="text-warning small fw-bold">+${c.xp_reward} XP</span>
            </div>
            <div class="fw-bold game-challenge-title mb-1">${escapeHtml(c.title)}</div>
            <div class="d-flex justify-content-between align-items-center mt-2">
                <span class="badge bg-dark border border-secondary text-secondary small text-uppercase">${c.game_type.replace('_', ' ')}</span>
                ${isSolved ? '<span class="badge bg-success"><i class="bi bi-check"></i> Solved</span>' : '<span class="text-muted small">Not attempted</span>'}
            </div>
        `;

        card.addEventListener('click', () => {
            selectChallenge(c);
        });

        listContainer.appendChild(card);
    });

    // Auto-select first if none selected
    if (filtered.length > 0 && !state.activeChallenge) {
        selectChallenge(filtered[0]);
    }
}

function selectChallenge(c) {
    state.activeChallenge = c;
    
    // Highlight list
    document.querySelectorAll('#game-challenges-list > div').forEach(div => {
        div.classList.remove('border-primary');
    });

    const arena = document.getElementById('game-active-arena');
    if (!arena) return;

    let diffColor = 'success';
    if (c.difficulty === 'Intermediate') diffColor = 'warning';
    if (c.difficulty === 'Advanced') diffColor = 'danger';

    arena.innerHTML = `
        <div class="pramana-card">
            <div class="pramana-card-header">
                <div>
                    <span class="badge bg-${diffColor} me-2">${c.difficulty}</span>
                    <span class="fw-bold game-challenge-title">${escapeHtml(c.title)}</span>
                </div>
                <span class="xp-badge"><i class="bi bi-award-fill"></i> +${c.xp_reward} XP</span>
            </div>
            <div class="pramana-card-body">
                <div class="mb-3">
                    <strong class="text-info small"><i class="bi bi-code-slash me-1"></i> Code Snippet:</strong>
                    <div class="interactive-code-viewer p-2 mt-1">
                        <pre class="m-0 game-code-snippet" style="font-family: var(--font-mono); font-size: 0.85rem;">${escapeHtml(c.code)}</pre>
                    </div>
                </div>

                <div class="mb-3">
                    <strong class="game-section-label"><i class="bi bi-question-circle me-1 text-warning"></i> Challenge Question:</strong>
                    <p class="text-secondary small mt-1 mb-0">${escapeHtml(c.prompt)}</p>
                </div>

                <div id="game-options-container" class="mb-3">
                    ${(c.options || []).map((opt, i) => `
                        <button class="game-option-btn" data-option="${escapeHtml(opt)}">
                            <span class="text-muted me-2">${String.fromCharCode(65 + i)}.</span> ${escapeHtml(opt)}
                        </button>
                    `).join('')}
                </div>

                <div id="game-feedback-area" class="d-none"></div>

                <div class="d-flex justify-content-between align-items-center mt-3 pt-3 border-top border-secondary">
                    <button id="btn-submit-game-answer" class="btn btn-pramana" disabled>
                        <i class="bi bi-send-check"></i> Submit Answer
                    </button>
                    <button id="btn-retry-game-answer" class="btn btn-pramana-outline d-none">
                        <i class="bi bi-arrow-clockwise"></i> Try Again
                    </button>
                </div>
            </div>
        </div>
    `;

    let selectedAnswer = '';
    const optionBtns = arena.querySelectorAll('.game-option-btn');
    const submitBtn = arena.querySelector('#btn-submit-game-answer');
    const retryBtn = arena.querySelector('#btn-retry-game-answer');
    const feedbackArea = arena.querySelector('#game-feedback-area');

    optionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            optionBtns.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedAnswer = btn.getAttribute('data-option');
            submitBtn.disabled = false;
        });
    });

    submitBtn.addEventListener('click', async () => {
        if (!selectedAnswer) return;
        submitBtn.disabled = true;

        try {
            const res = await fetch('/api/games/check/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    challenge_id: c.id,
                    answer: selectedAnswer
                })
            });

            const data = await res.json();
            if (!data.success) {
                alert(data.error || 'Failed to check answer.');
                submitBtn.disabled = false;
                return;
            }

            // Visual feedback on options
            optionBtns.forEach(b => {
                const optText = b.getAttribute('data-option');
                if (optText === data.correct_answer) {
                    b.classList.add('correct');
                } else if (optText === selectedAnswer && !data.is_correct) {
                    b.classList.add('wrong');
                }
            });

            // Display feedback details
            feedbackArea.classList.remove('d-none');
            if (data.is_correct) {
                feedbackArea.innerHTML = `
                    <div class="alert alert-success p-3">
                        <div class="fw-bold d-flex align-items-center gap-2">
                            <i class="bi bi-check-circle-fill"></i> Brilliant! Correct Answer (+${data.xp_awarded} XP)
                        </div>
                        <div class="mt-2 small game-feedback-explanation">${escapeHtml(data.explanation)}</div>
                        <div class="mt-2">
                            <strong class="small text-muted">Fixed Solution:</strong>
                            <pre class="bg-dark p-2 rounded text-success small mt-1 mb-0">${escapeHtml(data.solution_code)}</pre>
                        </div>
                    </div>
                `;

                if (!state.solvedChallenges.includes(c.id)) {
                    state.solvedChallenges.push(c.id);
                    localStorage.setItem('pramana_solved', JSON.stringify(state.solvedChallenges));
                    addXp(data.xp_awarded);
                }
                filterChallenges();
            } else {
                feedbackArea.innerHTML = `
                    <div class="alert alert-danger p-3">
                        <div class="fw-bold d-flex align-items-center gap-2">
                            <i class="bi bi-x-circle-fill"></i> Not quite right
                        </div>
                        <div class="mt-2 small game-feedback-explanation">${escapeHtml(data.explanation)}</div>
                    </div>
                `;
                retryBtn.classList.remove('d-none');
            }

        } catch (e) {
            alert(`Error checking answer: ${e.message}`);
            submitBtn.disabled = false;
        }
    });

    retryBtn.addEventListener('click', () => {
        selectChallenge(c);
    });
}

/* ==========================================================================
   EVIDENCE DOCS (RAG MANAGEMENT)
   ========================================================================== */
function setupDocsMode() {
    const fileInput = document.getElementById('rag-file-input');
    const dropzone = document.getElementById('rag-dropzone');
    const uploadBtn = document.getElementById('btn-trigger-upload');
    const clearBtn = document.getElementById('btn-clear-rag-store');
    const testQueryBtn = document.getElementById('btn-test-rag-query');

    if (uploadBtn && fileInput) {
        uploadBtn.addEventListener('click', () => fileInput.click());
    }

    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                handleFileUpload(fileInput.files[0]);
            }
        });
    }

    if (dropzone) {
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', async () => {
            if (confirm('Clear all indexed documents and vector embeddings from FAISS?')) {
                try {
                    const res = await fetch('/api/rag/clear/', { method: 'POST' });
                    const data = await res.json();
                    if (data.success) {
                        loadDocumentsList();
                        checkSystemStatus();
                        showModalAlert('Vector Store Cleared', data.message);
                    }
                } catch (e) {
                    alert('Failed to clear store.');
                }
            }
        });
    }

    if (testQueryBtn) {
        testQueryBtn.addEventListener('click', async () => {
            const queryInput = document.getElementById('rag-test-query-input');
            const query = queryInput.value.trim();
            const resultsBox = document.getElementById('rag-query-results');

            if (!query) return;
            testQueryBtn.disabled = true;
            resultsBox.innerHTML = '<div class="text-secondary small"><span class="spinner-pramana me-1"></span> Searching FAISS vector index...</div>';

            try {
                const res = await fetch('/api/rag/query/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query })
                });

                const data = await res.json();
                if (!data.success) {
                    resultsBox.innerHTML = `<div class="text-danger small">${escapeHtml(data.error || 'Query failed.')}</div>`;
                    return;
                }

                const ev = data.evidence;
                if (!ev.has_evidence || !ev.passages || ev.passages.length === 0) {
                    resultsBox.innerHTML = `<div class="alert alert-warning py-2 small">${escapeHtml(ev.message)}</div>`;
                } else {
                    let html = `<div class="alert alert-info py-2 small mb-2">${escapeHtml(ev.message)}</div>`;
                    ev.passages.forEach(p => {
                        html += `
                            <div class="evidence-card mb-2">
                                <div class="evidence-header">
                                    <span class="text-info fw-bold">${escapeHtml(p.filename)} (p. ${p.page_number})</span>
                                    <span class="badge bg-secondary">Sim: ${p.similarity_score}</span>
                                </div>
                                <div class="text-light small">${escapeHtml(p.text)}</div>
                            </div>
                        `;
                    });
                    resultsBox.innerHTML = html;
                }
            } catch (e) {
                resultsBox.innerHTML = `<div class="text-danger small">Error: ${escapeHtml(e.message)}</div>`;
            } finally {
                testQueryBtn.disabled = false;
            }
        });
    }
}

async function handleFileUpload(file) {
    const statusBox = document.getElementById('rag-upload-status');
    const formData = new FormData();
    formData.append('document', file);

    if (statusBox) {
        statusBox.classList.remove('d-none');
        statusBox.className = 'alert alert-info py-2 small mt-2';
        statusBox.innerHTML = `<span class="spinner-pramana me-1"></span> Extracting & generating embeddings for <strong>${escapeHtml(file.name)}</strong>...`;
    }

    try {
        const res = await fetch('/api/rag/upload/', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();
        if (!data.success) {
            if (statusBox) {
                statusBox.className = 'alert alert-danger py-2 small mt-2';
                statusBox.innerHTML = `<i class="bi bi-x-circle me-1"></i> ${escapeHtml(data.error || 'Upload failed.')}`;
            }
            return;
        }

        if (statusBox) {
            statusBox.className = 'alert alert-success py-2 small mt-2';
            statusBox.innerHTML = `<i class="bi bi-check-circle me-1"></i> Indexed <strong>${escapeHtml(file.name)}</strong>: ${data.pages_extracted} page(s), ${data.chunks_indexed} chunk(s) stored in FAISS.`;
        }

        loadDocumentsList();
        checkSystemStatus();
    } catch (e) {
        if (statusBox) {
            statusBox.className = 'alert alert-danger py-2 small mt-2';
            statusBox.innerHTML = `<i class="bi bi-x-circle me-1"></i> Upload error: ${escapeHtml(e.message)}`;
        }
    }
}

async function loadDocumentsList() {
    const listEl = document.getElementById('rag-documents-list');
    if (!listEl) return;

    try {
        const res = await fetch('/api/rag/documents/');
        const data = await res.json();
        if (data.success) {
            const docs = data.documents || [];
            if (docs.length === 0) {
                listEl.innerHTML = '<div class="p-3 text-muted text-center small">No documents in index yet. Upload a PDF or TXT above.</div>';
                return;
            }

            listEl.innerHTML = docs.map(d => `
                <div class="d-flex justify-content-between align-items-center p-2 mb-2 rounded bg-surface border border-secondary">
                    <div>
                        <span class="text-light fw-bold small"><i class="bi bi-file-earmark-text text-primary me-1"></i> ${escapeHtml(d.filename)}</span>
                        <div class="text-muted small">${d.pages_count} page(s) &bull; ${d.chunks_count} chunk(s) &bull; ${(d.file_size_bytes / 1024).toFixed(1)} KB</div>
                    </div>
                    <span class="badge bg-success small"><i class="bi bi-check2"></i> Indexed</span>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error("Failed to load documents", e);
    }
}

/* ==========================================================================
   HELPERS & MODALS
   ========================================================================== */
function showModalAlert(title, message) {
    const titleEl = document.getElementById('globalModalLabel');
    const bodyEl = document.getElementById('globalModalBody');
    if (titleEl && bodyEl) {
        titleEl.textContent = title;
        bodyEl.innerHTML = `<div class="modal-notice-message" style="color: #252525 !important; font-size: 18px !important; line-height: 1.6 !important;">${escapeHtml(message)}</div>`;
        const modal = new bootstrap.Modal(document.getElementById('globalModal'));
        modal.show();
    } else {
        alert(`${title}\n\n${message}`);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
