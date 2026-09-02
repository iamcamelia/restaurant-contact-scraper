// Global State
let batchResults = [];
let houstonData = [];
let currentHoustonFilter = 'all';

// On Page Load
document.addEventListener('DOMContentLoaded', () => {
    loadHoustonDataset();
});

// Toast Notification
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toast-msg');
    const toastIcon = document.getElementById('toast-icon');

    toastMsg.innerText = message;
    if (isError) {
        toastIcon.className = "fa-solid fa-circle-exclamation text-rose-400 text-base";
    } else {
        toastIcon.className = "fa-solid fa-check-circle text-emerald-400 text-base";
    }

    toast.classList.remove('translate-y-20', 'opacity-0');
    toast.classList.add('translate-y-0', 'opacity-100');

    setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('translate-y-20', 'opacity-0');
    }, 3500);
}

// Tab Switching
function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active', 'border-b-2', 'border-orange-500', 'text-orange-600', 'bg-white', 'shadow-sm');
        btn.classList.add('text-slate-500');
    });

    const targetContent = document.getElementById(`tab-${tab}`);
    const targetBtn = document.getElementById(`tab-${tab}-btn`);

    if (targetContent && targetBtn) {
        targetContent.classList.remove('hidden');
        targetBtn.classList.add('active', 'border-b-2', 'border-orange-500', 'text-orange-600', 'bg-white', 'shadow-sm');
        targetBtn.classList.remove('text-slate-500');
    }
}

// Quick Example Helper
function loadExample(name, url) {
    document.getElementById('single-name').value = name;
    document.getElementById('single-url').value = url;
}

// Copy to Clipboard Helper
function copyText(text, label = "Copied to clipboard!") {
    if (!text || text === 'N/A') {
        showToast("No data to copy", true);
        return;
    }
    navigator.clipboard.writeText(text).then(() => {
        showToast(label);
    }).catch(() => {
        showToast("Failed to copy", true);
    });
}

function copyField(elementId) {
    const text = document.getElementById(elementId).innerText;
    copyText(text);
}

// ================= TAB 1: SINGLE SCRAPE =================
async function handleSingleScrape(e) {
    e.preventDefault();
    const name = document.getElementById('single-name').value.trim();
    const url = document.getElementById('single-url').value.trim();
    const location = document.getElementById('single-location').value.trim();

    const placeholder = document.getElementById('single-result-placeholder');
    const loading = document.getElementById('single-result-loading');
    const card = document.getElementById('single-result-card');
    const submitBtn = document.getElementById('single-submit-btn');

    placeholder.classList.add('hidden');
    card.classList.add('hidden');
    loading.classList.remove('hidden');
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-50');

    try {
        const resp = await fetch('/api/scrape-single', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url, location })
        });
        const res = await resp.json();

        if (res.success && res.data) {
            const d = res.data;
            document.getElementById('res-name').innerText = d.name || 'Unknown';
            const urlEl = document.getElementById('res-url');
            if (d.url) {
                urlEl.href = d.url;
                const isAuto = d.sources && d.sources.includes('Auto-Discovered');
                document.getElementById('res-url-text').innerHTML = `${d.url} ${isAuto ? '<span class="ml-1.5 text-[10px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded">Auto-Discovered</span>' : ''}`;
                urlEl.classList.remove('hidden');
            } else {
                urlEl.classList.add('hidden');
            }

            document.getElementById('res-sources-badge').innerText = `Sources: ${d.sources || 'Website'}`;

            // Phone
            const phoneVal = d.primary_phone || (d.phone ? d.phone.split(', ')[0] : 'N/A');
            document.getElementById('res-phone').innerText = phoneVal;

            // Email
            const emailVal = d.primary_email || (d.email ? d.email.split(', ')[0] : 'N/A');
            document.getElementById('res-email').innerText = emailVal;

            // Socials
            const socialsContainer = document.getElementById('res-socials-container');
            socialsContainer.innerHTML = '';

            const renderBadge = (link, platform, icon, colorClass) => {
                if (!link) return;
                const a = document.createElement('a');
                a.href = link;
                a.target = '_blank';
                a.className = `badge-social ${colorClass}`;
                a.innerHTML = `<i class="${icon} mr-1.5"></i> ${platform}`;
                socialsContainer.appendChild(a);
            };

            const fbLinks = d.facebook ? d.facebook.split(', ') : [];
            const igLinks = d.instagram ? d.instagram.split(', ') : [];
            const liLinks = d.linkedin ? d.linkedin.split(', ') : [];

            if (fbLinks.length > 0) renderBadge(fbLinks[0], 'Facebook', 'fa-brands fa-facebook', 'badge-facebook');
            if (igLinks.length > 0) renderBadge(igLinks[0], 'Instagram', 'fa-brands fa-instagram', 'badge-instagram');
            if (liLinks.length > 0) renderBadge(liLinks[0], 'LinkedIn', 'fa-brands fa-linkedin', 'badge-linkedin');

            if (socialsContainer.children.length === 0) {
                socialsContainer.innerHTML = '<span class="text-xs text-slate-400">No social profiles detected.</span>';
            }

            loading.classList.add('hidden');
            card.classList.remove('hidden');
            showToast("Scrape completed!");
        } else {
            throw new Error(res.error || "Failed to extract contacts");
        }
    } catch (err) {
        loading.classList.add('hidden');
        placeholder.classList.remove('hidden');
        showToast(err.message, true);
    } finally {
        submitBtn.disabled = false;
        submitBtn.classList.remove('opacity-50');
    }
}

// ================= TAB 2: BATCH SCRAPER =================
function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
        const text = event.target.result;
        const lines = text.split(/\r?\n/);
        const formatted = [];
        lines.forEach(line => {
            const parts = line.split(',');
            if (parts.length >= 2) {
                formatted.push(`${parts[0].trim()}, ${parts[1].trim()}`);
            }
        });
        document.getElementById('batch-textarea').value = formatted.join('\n');
        showToast(`Loaded ${formatted.length} restaurants from file!`);
    };
    reader.readAsText(file);
}

async function startBatchScrape() {
    const raw = document.getElementById('batch-textarea').value.trim();
    if (!raw) {
        showToast("Please enter at least one restaurant (Name, URL).", true);
        return;
    }

    const lines = raw.split(/\r?\n/);
    const items = [];
    lines.forEach((line, idx) => {
        const parts = line.split(',');
        if (parts.length >= 2) {
            items.push({
                row: idx + 6,
                name: parts[0].trim(),
                url: parts[1].trim()
            });
        }
    });

    if (items.length === 0) {
        showToast("Could not parse restaurant items. Format: Name, URL", true);
        return;
    }

    const workers = parseInt(document.getElementById('batch-workers').value) || 5;
    const progressContainer = document.getElementById('batch-progress-container');
    const progressBar = document.getElementById('batch-progress-bar');
    const statusText = document.getElementById('batch-status-text');
    const percentText = document.getElementById('batch-percent-text');
    const runBtn = document.getElementById('batch-run-btn');

    progressContainer.classList.remove('hidden');
    progressBar.style.width = '30%';
    percentText.innerText = '30%';
    statusText.innerText = `Scraping ${items.length} restaurants with ${workers} workers...`;
    runBtn.disabled = true;
    runBtn.classList.add('opacity-50');

    try {
        const resp = await fetch('/api/scrape-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items, workers })
        });
        const res = await resp.json();

        if (res.success && res.data) {
            progressBar.style.width = '100%';
            percentText.innerText = '100%';
            statusText.innerText = 'Complete!';

            batchResults = res.data;
            renderBatchTable(batchResults);
            document.getElementById('batch-results-container').classList.remove('hidden');
            document.getElementById('batch-count-badge').innerText = `${batchResults.length} processed`;
            showToast(`Batch scrape complete: ${batchResults.length} restaurants!`);
        } else {
            throw new Error(res.error || "Batch scraping failed");
        }
    } catch (err) {
        showToast(err.message, true);
    } finally {
        runBtn.disabled = false;
        runBtn.classList.remove('opacity-50');
    }
}

function renderBatchTable(results) {
    const tbody = document.getElementById('batch-table-body');
    tbody.innerHTML = '';

    results.forEach((r, idx) => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-slate-50 transition border-b border-slate-100";

        const phone = r.primary_phone || (r.phone ? r.phone.split(', ')[0] : '-');
        const email = r.primary_email || (r.email ? r.email.split(', ')[0] : '-');

        const socialBadges = [];
        if (r.facebook) socialBadges.push(`<a href="${r.facebook.split(', ')[0]}" target="_blank" class="badge-social badge-facebook text-[10px]"><i class="fa-brands fa-facebook"></i></a>`);
        if (r.instagram) socialBadges.push(`<a href="${r.instagram.split(', ')[0]}" target="_blank" class="badge-social badge-instagram text-[10px]"><i class="fa-brands fa-instagram"></i></a>`);
        if (r.linkedin) socialBadges.push(`<a href="${r.linkedin.split(', ')[0]}" target="_blank" class="badge-social badge-linkedin text-[10px]"><i class="fa-brands fa-linkedin"></i></a>`);

        tr.innerHTML = `
            <td class="py-3 px-4 font-mono text-slate-400">${r.row || (idx + 1)}</td>
            <td class="py-3 px-4">
                <div class="font-bold text-slate-900">${r.name}</div>
                <a href="${r.url}" target="_blank" class="text-slate-400 hover:text-blue-600 text-[11px] truncate max-w-[180px] block">${r.url}</a>
            </td>
            <td class="py-3 px-4 font-semibold ${phone !== '-' ? 'text-emerald-700' : 'text-slate-400'}">${phone}</td>
            <td class="py-3 px-4 font-semibold ${email !== '-' ? 'text-blue-700' : 'text-slate-400'}">${email}</td>
            <td class="py-3 px-4"><div class="flex gap-1">${socialBadges.join('') || '<span class="text-slate-300">-</span>'}</div></td>
            <td class="py-3 px-4 text-slate-400 text-[11px]">${r.sources || 'Web'}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ================= TAB 3: HOUSTON DATASET =================
async function loadHoustonDataset() {
    try {
        const resp = await fetch('/api/houston-dataset');
        const res = await resp.json();
        if (res.success && res.data) {
            houstonData = res.data;
            renderHoustonTable(houstonData);
        }
    } catch (e) {
        console.error("Failed to load Houston dataset:", e);
    }
}

function setHoustonFilter(filter) {
    currentHoustonFilter = filter;
    document.querySelectorAll('.houston-filter-btn').forEach(btn => {
        btn.classList.remove('active', 'bg-orange-100', 'text-orange-700');
        btn.classList.add('bg-slate-100', 'text-slate-600');
    });
    event.target.classList.add('active', 'bg-orange-100', 'text-orange-700');
    event.target.classList.remove('bg-slate-100', 'text-slate-600');
    filterHoustonTable();
}

function filterHoustonTable() {
    const search = document.getElementById('houston-search').value.toLowerCase();
    const filtered = houstonData.filter(r => {
        const matchesSearch = !search ||
            (r.name && r.name.toLowerCase().includes(search)) ||
            (r.phone && r.phone.toLowerCase().includes(search)) ||
            (r.email && r.email.toLowerCase().includes(search));

        if (!matchesSearch) return false;

        if (currentHoustonFilter === 'phone') return !!r.phone;
        if (currentHoustonFilter === 'email') return !!r.email;
        if (currentHoustonFilter === 'social') return !!(r.facebook || r.instagram || r.linkedin);
        return true;
    });

    renderHoustonTable(filtered);
}

function renderHoustonTable(data) {
    const tbody = document.getElementById('houston-table-body');
    tbody.innerHTML = '';

    data.forEach(r => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-slate-50 transition border-b border-slate-100";

        const phones = r.phone ? r.phone.split(', ') : [];
        const emails = r.email ? r.email.split(', ') : [];
        const phone = phones.length > 0 ? phones[0] : '-';
        const email = emails.length > 0 ? emails[0] : '-';

        const socialBadges = [];
        if (r.facebook) socialBadges.push(`<a href="${r.facebook.split(', ')[0]}" target="_blank" class="badge-social badge-facebook text-[10px]"><i class="fa-brands fa-facebook"></i></a>`);
        if (r.instagram) socialBadges.push(`<a href="${r.instagram.split(', ')[0]}" target="_blank" class="badge-social badge-instagram text-[10px]"><i class="fa-brands fa-instagram"></i></a>`);
        if (r.linkedin) socialBadges.push(`<a href="${r.linkedin.split(', ')[0]}" target="_blank" class="badge-social badge-linkedin text-[10px]"><i class="fa-brands fa-linkedin"></i></a>`);

        tr.innerHTML = `
            <td class="py-3 px-4 font-mono font-bold text-slate-400">Row ${r.row}</td>
            <td class="py-3 px-4">
                <div class="font-bold text-slate-900">${r.name}</div>
                <a href="${r.url}" target="_blank" class="text-slate-400 hover:text-blue-600 text-[11px] truncate max-w-[200px] block">${r.url}</a>
            </td>
            <td class="py-3 px-4 font-semibold ${phone !== '-' ? 'text-emerald-700 font-bold' : 'text-slate-400'}">${phone}</td>
            <td class="py-3 px-4 font-semibold ${email !== '-' ? 'text-blue-700 font-bold' : 'text-slate-400'}">${email}</td>
            <td class="py-3 px-4"><div class="flex gap-1">${socialBadges.join('') || '<span class="text-slate-300">-</span>'}</div></td>
        `;
        tbody.appendChild(tr);
    });
}

// ================= EXPORTS & GOOGLE SHEETS =================
function copyGoogleSheetsData(source) {
    const list = source === 'houston' ? houstonData : batchResults;
    if (!list || list.length === 0) {
        showToast("No data available to copy.", true);
        return;
    }

    // Sort by row
    const sorted = [...list].sort((a, b) => (a.row || 0) - (b.row || 0));

    // Generate TSV format (Phone \t Email)
    const tsvLines = sorted.map(r => {
        const phone = r.primary_phone || (r.phone ? r.phone.split(', ')[0] : '');
        const email = r.primary_email || (r.email ? r.email.split(', ')[0] : '');
        return `${phone}\t${email}`;
    });

    const tsvContent = tsvLines.join('\n');
    copyText(tsvContent, `Copied ${sorted.length} rows for Google Sheets! Click cell G6 and press Ctrl+V.`);
}

async function exportCSV(source) {
    const results = source === 'houston' ? houstonData : batchResults;
    if (!results || results.length === 0) {
        showToast("No data to export.", true);
        return;
    }

    try {
        const resp = await fetch('/api/export-csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ results })
        });
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${source}_restaurant_contacts.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("CSV Downloaded!");
    } catch (e) {
        showToast("Failed to download CSV", true);
    }
}

async function exportAppsScript(source) {
    const results = source === 'houston' ? houstonData : batchResults;
    if (!results || results.length === 0) {
        showToast("No data for script generation.", true);
        return;
    }

    try {
        const resp = await fetch('/api/export-sheets-script', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ results })
        });
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `update_google_sheet.gs`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("Apps Script Downloaded!");
    } catch (e) {
        showToast("Failed to generate Apps Script", true);
    }
}
