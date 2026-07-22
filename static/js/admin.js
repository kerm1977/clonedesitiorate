'use strict';

var quill = new Quill('#quillEditor', {
    theme: 'snow',
    placeholder: 'Escribe aquí el contenido de Conózcanos...',
    modules: {
        toolbar: [
            [{ header: [1, 2, 3, false] }],
            ['bold', 'italic', 'underline', 'strike'],
            [{ color: [] }, { background: [] }],
            [{ list: 'ordered' }, { list: 'bullet' }],
            ['link', 'blockquote'],
            ['clean']
        ]
    }
});

function flushEditor() {
    document.getElementById('aboutHidden').value = quill.root.innerHTML;
}

function toggleImage(id) {
    const btn = document.getElementById('btn-' + id);
    const badge = document.getElementById('badge-' + id);
    btn.disabled = true;
    fetch('/admin/media/images/' + id + '/toggle', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.active) {
                badge.className = 'badge bg-success status-badge';
                badge.textContent = 'Activa';
                btn.textContent = 'Desactivar';
            } else {
                badge.className = 'badge bg-secondary status-badge';
                badge.textContent = 'Inactiva';
                btn.textContent = 'Activar';
            }
            btn.disabled = false;
        })
        .catch(() => { btn.disabled = false; });
}

const hash = window.location.hash;
if (hash) {
    const tab = document.querySelector('[href="' + hash + '"]');
    if (tab) { new bootstrap.Tab(tab).show(); }
}
