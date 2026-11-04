const editModal = new bootstrap.Modal(document.getElementById('editModal'));

document.querySelectorAll('.btn-edit').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById('editId').value = btn.dataset.id;
        document.getElementById('editName').value = btn.dataset.name;
        document.getElementById('editStaffId').value = btn.dataset.staff;
        editModal.show();
    });
});

document.getElementById('btnSaveEdit').addEventListener('click', async () => {
    const id = document.getElementById('editId').value;
    const name = document.getElementById('editName').value.trim();
    const staff_id = document.getElementById('editStaffId').value.trim();

    if (!name || !staff_id) {
        alert('Name and Staff ID are required');
        return;
    }

    try {
        const res = await fetch(`/api/people/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, staff_id })
        });
        const data = await res.json();
        if (data.success) {
            location.reload();
        } else {
            alert(data.message || 'Update failed');
        }
    } catch (err) {
        alert('Network error');
    }
});

document.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', async () => {
        const name = btn.dataset.name;
        if (!confirm(`Remove "${name}"?\n\nAttendance history will be kept.`)) return;

        try {
            const res = await fetch(`/api/people/${btn.dataset.id}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                location.reload();
            } else {
                alert(data.message || 'Delete failed');
            }
        } catch (err) {
            alert('Network error');
        }
    });
});
