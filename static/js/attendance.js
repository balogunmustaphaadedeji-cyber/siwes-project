async function loadAttendance() {
    const personId = document.getElementById('filterPerson').value;
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;

    const params = new URLSearchParams();
    if (personId) params.append('person_id', personId);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);

    const tbody = document.getElementById('attendanceTable');
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Loading…</td></tr>';

    try {
        const res = await fetch('/api/attendance?' + params.toString());
        const rows = await res.json();

        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">No records found</td></tr>';
            return;
        }

        tbody.innerHTML = rows.map(r => `
            <tr>
                <td><code>${r.staff_id}</code></td>
                <td>${r.name}</td>
                <td>${r.date}</td>
                <td>${r.timestamp.replace('T', ' ').substring(11, 19)}</td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger py-4">Failed to load data</td></tr>';
    }
}

document.getElementById('btnFilter').addEventListener('click', loadAttendance);

document.getElementById('btnExport').addEventListener('click', () => {
    const personId = document.getElementById('filterPerson').value;
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;

    const params = new URLSearchParams();
    if (personId) params.append('person_id', personId);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);

    window.location.href = '/api/attendance/export?' + params.toString();
});

// Load on page open
loadAttendance();
