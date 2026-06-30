// App State
let selectedCandidateId = null;
let currentCandidateData = null;

// DOM Elements
const candidateListEl = document.getElementById('candidate-list');
const searchInput = document.getElementById('search-candidates');
const welcomeView = document.getElementById('welcome-view');
const candidateView = document.getElementById('candidate-view');
const btnProcess = document.getElementById('btn-process');
const btnClear = document.getElementById('btn-clear');
const btnCopy = document.getElementById('btn-copy');
const btnDownload = document.getElementById('btn-download');
const pipelineStatus = document.getElementById('pipeline-status');
const statusMessage = document.getElementById('status-message');
const jsonCodeEl = document.getElementById('json-code');

const inputCsv = document.getElementById('input-csv');
const inputResumes = document.getElementById('input-resumes');
const inputGithub = document.getElementById('input-github');
const csvFileName = document.getElementById('csv-file-name');
const resumesCount = document.getElementById('resumes-count');

// Toggle Elements
const toggleIds = [
    'candidate_id', 'full_name', 'emails', 'phones', 'headline',
    'skills', 'experience', 'education', 'provenance', 'overall_confidence'
];

// Initialize UI listeners
document.addEventListener('DOMContentLoaded', () => {
    loadCandidates();

    // Ingestion operations
    btnProcess.addEventListener('click', runPipeline);
    btnClear.addEventListener('click', clearDatabase);

    // File selection label updates
    inputCsv.addEventListener('change', () => {
        const file = inputCsv.files[0];
        csvFileName.textContent = file ? file.name : 'No file chosen';
    });

    inputResumes.addEventListener('change', () => {
        const count = inputResumes.files.length;
        resumesCount.textContent = `${count} file${count === 1 ? '' : 's'} selected`;
    });

    // Search bar filter
    searchInput.addEventListener('input', filterCandidates);

    // Toggle listeners for live JSON projection
    toggleIds.forEach(id => {
        const toggleEl = document.getElementById(`spec-${id}`);
        if (toggleEl) {
            toggleEl.addEventListener('change', updateProjectedJson);
        }
    });

    // Code panel actions
    btnCopy.addEventListener('click', copyJsonToClipboard);
    btnDownload.addEventListener('click', downloadJsonFile);
});

// Fetch all candidates and populate list
async function loadCandidates() {
    try {
        const res = await fetch('/api/candidates');
        if (!res.ok) throw new Error('Failed to load candidate summaries');
        const data = await res.json();
        
        candidateListEl.innerHTML = '';
        if (data.length === 0) {
            candidateListEl.innerHTML = '<li class="no-data">No profiles ingested yet</li>';
            return;
        }

        data.forEach(cand => {
            const li = document.createElement('li');
            li.className = `candidate-item ${cand.candidate_id === selectedCandidateId ? 'active' : ''}`;
            li.dataset.id = cand.candidate_id;
            li.addEventListener('click', () => selectCandidate(cand.candidate_id));

            // Format match score badge
            const confidence = cand.overall_confidence ? Math.round(cand.overall_confidence * 100) : 0;

            li.innerHTML = `
                <div class="candidate-item-meta">
                    <span class="candidate-item-name">${cand.full_name || 'Unnamed Candidate'}</span>
                    <span class="candidate-item-email">${cand.email || 'No email available'}</span>
                </div>
                <div class="confidence-badge">${confidence}%</div>
            `;
            candidateListEl.appendChild(li);
        });

        // Retain candidate selection or select the first candidate by default
        if (selectedCandidateId && data.some(c => c.candidate_id === selectedCandidateId)) {
            selectCandidate(selectedCandidateId);
        } else if (data.length > 0) {
            selectCandidate(data[0].candidate_id);
        } else {
            closeCandidateView();
        }
    } catch (err) {
        console.error(err);
        candidateListEl.innerHTML = '<li class="no-data error">Error loading profiles</li>';
    }
}

// Select a single candidate
async function selectCandidate(cid) {
    selectedCandidateId = cid;
    
    // Highlight list item
    document.querySelectorAll('.candidate-item').forEach(item => {
        item.classList.toggle('active', item.dataset.id === cid);
    });

    try {
        const res = await fetch(`/api/candidates/${cid}`);
        if (!res.ok) throw new Error('Failed to load candidate profile');
        currentCandidateData = await res.json();
        
        // Update DOM
        renderProfileHeader(currentCandidateData.merged);
        renderTimeline(currentCandidateData.merged.experience || []);
        renderEducation(currentCandidateData.merged.education || []);
        renderSkills(currentCandidateData.merged.skills || []);
        renderProvenance(currentCandidateData.merged.provenance || []);

        welcomeView.classList.add('hidden');
        candidateView.classList.remove('hidden');

        // Render tab and update JSON projection
        switchTab('tab-experience');
        updateProjectedJson();
    } catch (err) {
        console.error(err);
        alert('Failed to retrieve candidate profile details.');
    }
}

// Render profile header details
function renderProfileHeader(profile) {
    document.getElementById('profile-name').textContent = profile.full_name || 'Unnamed';
    document.getElementById('profile-headline').textContent = profile.headline || 'Profile Ingested';

    // Contacts
    const contactContainer = document.getElementById('profile-contacts');
    contactContainer.innerHTML = '';

    if (profile.emails && profile.emails.length > 0) {
        profile.emails.forEach(email => {
            contactContainer.innerHTML += `
                <a href="mailto:${email}" class="contact-badge">
                    <i class="fa-solid fa-envelope"></i> ${email}
                </a>
            `;
        });
    }
    if (profile.phones && profile.phones.length > 0) {
        profile.phones.forEach(phone => {
            contactContainer.innerHTML += `
                <span class="contact-badge">
                    <i class="fa-solid fa-phone"></i> ${phone}
                </span>
            `;
        });
    }
    if (profile.github_username) {
        contactContainer.innerHTML += `
            <a href="https://github.com/${profile.github_username}" target="_blank" class="contact-badge">
                <i class="fa-brands fa-github"></i> github.com/${profile.github_username}
            </a>
        `;
    }

    // Confidence radial progress
    const confidence = profile.overall_confidence ? Math.round(profile.overall_confidence * 100) : 0;
    document.getElementById('confidence-text').textContent = `${confidence}%`;
    document.getElementById('confidence-fill-bar').style.width = `${confidence}%`;
}

// Render Work Experience Timeline
function renderTimeline(experience) {
    const container = document.getElementById('timeline-container');
    container.innerHTML = '';
    
    if (experience.length === 0) {
        container.innerHTML = '<p class="no-data-msg">No work experience listed</p>';
        return;
    }

    experience.forEach(exp => {
        const item = document.createElement('div');
        item.className = 'timeline-item';
        item.innerHTML = `
            <div class="timeline-header">
                <div>
                    <div class="timeline-role">${exp.title || 'Role'}</div>
                    <div class="timeline-company">${exp.company || 'Company'}</div>
                </div>
                <div class="timeline-date">${exp.start || 'Start'} — ${exp.end || 'Present'}</div>
            </div>
            <div class="timeline-summary">${exp.summary || ''}</div>
        `;
        container.appendChild(item);
    });
}

// Render Education Cards
function renderEducation(education) {
    const container = document.getElementById('education-container');
    container.innerHTML = '';

    if (education.length === 0) {
        container.innerHTML = '<p class="no-data-msg">No education records listed</p>';
        return;
    }

    education.forEach(edu => {
        const card = document.createElement('div');
        card.className = 'education-card';
        card.innerHTML = `
            <div class="education-meta">
                <h4>${edu.degree || 'Degree'} ${edu.field ? 'in ' + edu.field : ''}</h4>
                <div class="education-school">${edu.institution ? 'at ' + edu.institution : ''}</div>
            </div>
            <div class="education-year">${edu.end_year || 'N/A'}</div>
        `;
        container.appendChild(card);
    });
}

// Render Skills
function renderSkills(skills) {
    const container = document.getElementById('skills-container');
    container.innerHTML = '';

    if (skills.length === 0) {
        container.innerHTML = '<p class="no-data-msg">No skills parsed</p>';
        return;
    }

    skills.forEach(skill => {
        const badge = document.createElement('span');
        badge.className = 'skill-pill';
        const pct = skill.confidence ? Math.round(skill.confidence * 100) : 0;
        badge.innerHTML = `
            ${skill.name}
            ${pct > 0 ? `<span class="skill-pill-strength">${pct}%</span>` : ''}
        `;
        container.appendChild(badge);
    });
}

// Render Provenance logs
function renderProvenance(provenance) {
    const container = document.getElementById('provenance-container');
    container.innerHTML = '';

    if (provenance.length === 0) {
        container.innerHTML = '<tr><td colspan="4" style="text-align:center;">No traceability records available</td></tr>';
        return;
    }

    provenance.forEach(prov => {
        // Format source labels
        const sources = prov.source.split(',').map(s => {
            const clean = s.trim().toLowerCase();
            return `<span class="source-badge source-${clean}">${clean}</span>`;
        }).join(' ');

        // Format value fields if object
        let valStr = prov.value;
        if (typeof prov.value === 'object' && prov.value !== null) {
            valStr = JSON.stringify(prov.value);
        }

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${prov.field}</strong></td>
            <td>${sources}</td>
            <td><code>${prov.method}</code></td>
            <td>${valStr || ''}</td>
        `;
        container.appendChild(row);
    });
}

// Tab Switcher
function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        const matches = btn.getAttribute('onclick').includes(tabId);
        btn.classList.toggle('active', matches);
    });

    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.toggle('active', pane.id === tabId);
    });
}

// Fetch and render projected JSON output
async function updateProjectedJson() {
    if (!selectedCandidateId) return;

    // Collect checked fields
    const selectedFields = [];
    toggleIds.forEach(id => {
        const chk = document.getElementById(`spec-${id}`);
        if (chk && chk.checked) {
            selectedFields.push(id);
        }
    });

    try {
        const res = await fetch(`/api/candidates/${selectedCandidateId}/project`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fields: selectedFields })
        });
        if (!res.ok) throw new Error('Failed to update json projection');
        const data = await res.json();
        
        jsonCodeEl.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
        console.error(err);
        jsonCodeEl.textContent = '{"error": "Failed to update field projection"}';
    }
}

// Run Pipeline Ingestion Process
async function runPipeline() {
    const csvFile = inputCsv.files[0];
    const resumeFiles = inputResumes.files;
    const githubUsernames = inputGithub.value.trim();

    if (!csvFile && resumeFiles.length === 0 && !githubUsernames) {
        alert('Please provide at least one input source (Recruiter CSV, Resumes, or GitHub usernames).');
        return;
    }

    btnProcess.disabled = true;
    pipelineStatus.classList.remove('hidden');
    statusMessage.textContent = 'Processing candidates... Ingesting CSV, Resumes, and GitHub profiles...';

    const formData = new FormData();
    if (csvFile) {
        formData.append('csv_file', csvFile);
    }
    for (let i = 0; i < resumeFiles.length; i++) {
        formData.append('resumes', resumeFiles[i]);
    }
    if (githubUsernames) {
        formData.append('github_usernames', githubUsernames);
    }

    try {
        const res = await fetch('/api/pipeline/process', {
            method: 'POST',
            body: formData
        });
        if (!res.ok) throw new Error('Pipeline processing failed');
        const data = await res.json();

        // Reset file inputs
        inputCsv.value = '';
        inputResumes.value = '';
        inputGithub.value = '';
        csvFileName.textContent = 'No file chosen';
        resumesCount.textContent = '0 files selected';

        statusMessage.textContent = `Completed! Ingested ${data.processed_count} candidates.`;
        setTimeout(() => {
            pipelineStatus.classList.add('hidden');
            btnProcess.disabled = false;
            loadCandidates();
        }, 2000);
    } catch (err) {
        console.error(err);
        statusMessage.textContent = 'Error running pipeline.';
        btnProcess.disabled = false;
        setTimeout(() => pipelineStatus.classList.add('hidden'), 3500);
    }
}

// Wipes DB
async function clearDatabase() {
    if (!confirm('Are you sure you want to clear all candidate records from the SQLite database?')) {
        return;
    }

    btnClear.disabled = true;
    pipelineStatus.classList.remove('hidden');
    statusMessage.textContent = 'Wiping database...';

    try {
        const res = await fetch('/api/pipeline/clear', { method: 'POST' });
        if (!res.ok) throw new Error('Failed to clear database');
        
        statusMessage.textContent = 'Database cleared successfully!';
        setTimeout(() => {
            pipelineStatus.classList.add('hidden');
            btnClear.disabled = false;
            selectedCandidateId = null;
            currentCandidateData = null;
            loadCandidates();
            closeCandidateView();
        }, 1500);
    } catch (err) {
        console.error(err);
        statusMessage.textContent = 'Failed to wipe database.';
        btnClear.disabled = false;
        setTimeout(() => pipelineStatus.classList.add('hidden'), 3000);
    }
}

// Filter candidate list client-side
function filterCandidates() {
    const term = searchInput.value.toLowerCase().trim();
    const items = candidateListEl.querySelectorAll('.candidate-item');
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(term)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

function closeCandidateView() {
    candidateView.classList.add('hidden');
    welcomeView.classList.remove('hidden');
}

// Copy JSON to clipboard with feedback animations
function copyJsonToClipboard() {
    const text = jsonCodeEl.textContent;
    navigator.clipboard.writeText(text).then(() => {
        btnCopy.innerHTML = '<i class="fa-solid fa-check" style="color: var(--success-green);"></i> Copied';
        setTimeout(() => {
            btnCopy.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
    });
}

// Download JSON output
function downloadJsonFile() {
    const text = jsonCodeEl.textContent;
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `projected_profile_${selectedCandidateId || 'candidate'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
