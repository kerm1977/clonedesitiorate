'use strict';

let busy = false;
let quillEditor = null;

function toggleOptions() {
    const menu = document.getElementById('optionsMenu');
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }
}

function toggleComments() {
    const body = document.getElementById('commentsBody');
    if (!body) return;
    if (body.style.display === 'none') {
        body.style.display = 'block';
        loadComments();
    } else {
        body.style.display = 'none';
    }
}

function triggerConfetti() {
    if (typeof confetti === 'function') {
        var duration = 5 * 1000;
        var end = Date.now() + duration;

        (function frame() {
            // Main burst from center
            confetti({
                particleCount: 50,
                spread: 100,
                origin: { y: 0.6 },
                colors: ['#ff6b9d', '#845ec2', '#e91e8c', '#ffc75f', '#f9f871', '#ff00ff', '#00ffff'],
                zIndex: 1000
            });
            
            // Side bursts
            confetti({
                particleCount: 30,
                angle: 60,
                spread: 80,
                origin: { x: 0 },
                colors: ['#ff6b9d', '#845ec2', '#e91e8c', '#ffc75f', '#f9f871'],
                zIndex: 1000
            });
            confetti({
                particleCount: 30,
                angle: 120,
                spread: 80,
                origin: { x: 1 },
                colors: ['#ff6b9d', '#845ec2', '#e91e8c', '#ffc75f', '#f9f871'],
                zIndex: 1000
            });

            if (Date.now() < end) {
                requestAnimationFrame(frame);
            }
        }());
    } else {
        console.warn('canvas-confetti library is not loaded.');
    }
}

function toggleConfettiEffect() {
    const imageId = document.getElementById('currentImageId').value;
    if (!imageId) return;

    fetch('/image/' + imageId + '/toggle-confetti', {
        method: 'POST'
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            const icon = document.getElementById('confettiIcon');
            const card = document.getElementById('imageCard');
            if (icon) {
                if (d.has_confetti) {
                    icon.className = 'bi bi-sparkles text-warning';
                    triggerConfetti();
                } else {
                    icon.className = 'bi bi-sparkles text-white-50';
                }
            }
            if (card) {
                card.dataset.hasConfetti = d.has_confetti ? 'true' : 'false';
            }
        } else {
            alert('Error: ' + (d.error || 'No se pudo cambiar el estado del confeti'));
        }
    })
    .catch(e => {
        console.error('Error toggling confetti:', e);
        alert('Error al conectar con el servidor.');
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function linkify(text) {
    const urlPattern = /(\b(https?):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig;
    return text.replace(urlPattern, '<a href="$1" target="_blank" style="color:#ff6b9d;text-decoration:underline;font-weight:700;">$1</a>');
}

function toggleImageCommentReplyForm(commentId, username) {
    const form = document.getElementById('img-reply-form-' + commentId);
    if (!form) return;
    if (form.style.display === 'none') {
        form.style.display = 'block';
        const input = document.getElementById('img-reply-input-' + commentId);
        if (input) {
            input.value = '';
            input.focus();
        }
    } else {
        form.style.display = 'none';
    }
}

function submitImageCommentReply(commentId, toUsername) {
    const input = document.getElementById('img-reply-input-' + commentId);
    const replyText = input ? input.value.trim() : '';
    if (!replyText) return;

    const content = '↩ @' + toUsername + ': ' + replyText;
    const imageId = document.getElementById('currentImageId').value;
    if (!imageId) return;

    const section = document.getElementById('commentsSection');
    const isNita = section && section.dataset.isNita === 'true';
    
    let username = '';
    if (isNita) {
        username = 'nitalaosita';
    } else {
        const userInp = document.querySelector('#commentForm input[name="username"]');
        username = userInp ? userInp.value.trim() : (section ? section.dataset.username : '');
    }

    if (!username) {
        alert('Por favor escribe tu nombre en el formulario principal antes de responder.');
        return;
    }

    const formData = new FormData();
    formData.append('content', content);
    formData.append('username', username);

    fetch('/image/' + imageId + '/comment', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            loadComments();
        } else {
            alert('Error: ' + d.error);
        }
    })
    .catch(() => alert('Error al enviar respuesta'));
}

function loadComments() {
    const imageId = document.getElementById('currentImageId').value;
    if (!imageId) return;
    
    fetch('/image/' + imageId + '/comments')
        .then(r => r.json())
        .then(comments => {
            const list = document.getElementById('commentsList');
            list.innerHTML = '';
            const section = document.getElementById('commentsSection');
            const isSuperuser = section && section.dataset.isSuperuser === 'true';
            const isNita = section && section.dataset.isNita === 'true';
            const currentUserId = section ? parseInt(section.dataset.userId) || null : null;

            if (comments.length === 0) {
                list.innerHTML = '<p class="text-muted small text-center">Sin comentarios aún</p>';
                return;
            }

            comments.forEach(c => {
                const canLike = isSuperuser || isNita;
                const canEdit = isSuperuser || c.is_own;
                const canDelete = isSuperuser;
                const likeClass = c.is_liked ? 'text-danger' : 'text-white-50';
                const likeIcon = c.is_liked ? 'bi-heart-fill' : 'bi-heart';

                let actionBtns = '';
                if (canLike) {
                    actionBtns += `<button class="btn btn-link p-0 me-2 ${likeClass}" onclick="toggleImageCommentLike(${c.id})" id="img-like-btn-${c.id}" title="Like" style="font-size:1.3rem;line-height:1;">
                        <i class="bi ${likeIcon}" id="img-like-icon-${c.id}"></i>
                        <span id="img-like-count-${c.id}" style="font-size:1.1rem;font-weight:600;vertical-align:middle;">${c.likes_count}</span>
                    </button>`;
                    actionBtns += `<button class="btn btn-sm btn-link p-0 me-2 text-secondary" onclick="toggleImageCommentReplyForm(${c.id}, '${c.username.replace(/'/g, "\\'")}')" title="Responder"><i class="bi bi-reply"></i> Responder</button>`;
                } else {
                    actionBtns += `<span class="text-white-50 me-2" style="font-size:1.2rem;"><i class="bi bi-heart"></i> <span id="img-like-count-${c.id}" style="font-size:1rem;font-weight:600;">${c.likes_count}</span></span>`;
                }
                if (isSuperuser) {
                    actionBtns += `<button class="btn btn-sm btn-link p-0 me-2 text-muted" onclick="editImageCommentLikes(${c.id})" title="Editar likes"><i class="bi bi-pencil-square"></i></button>`;
                }
                if (canEdit) {
                    actionBtns += `<button class="btn btn-sm btn-link p-0 me-2 text-secondary" onclick="editImageComment(${c.id})" title="Editar"><i class="bi bi-pencil"></i></button>`;
                }
                if (canDelete) {
                    actionBtns += `<button class="btn btn-sm btn-link p-0 text-danger" onclick="deleteImageComment(${c.id})" title="Eliminar"><i class="bi bi-trash"></i></button>`;
                }

                const escapedContent = escapeHtml(c.content);
                const linkedContent = linkify(escapedContent);

                const div = document.createElement('div');
                div.className = 'comment-item';
                div.id = 'img-comment-' + c.id;
                div.innerHTML = `
                    <div class="comment-header d-flex justify-content-between align-items-center">
                        <span class="comment-username">${c.username}</span>
                        <span class="comment-time">${c.created_at}</span>
                    </div>
                    <div class="comment-content" id="img-comment-content-${c.id}">${linkedContent}</div>
                    <div class="d-flex align-items-center mt-1 gap-1">${actionBtns}</div>
                    <div id="img-reply-form-${c.id}" style="display:none;" class="mt-2 ms-3">
                        <div class="input-group input-group-sm">
                            <input type="text" class="form-control form-control-dark form-control-sm" id="img-reply-input-${c.id}" placeholder="Responder a ${c.username}...">
                            <button class="btn btn-fun-pink btn-sm" onclick="submitImageCommentReply(${c.id}, '${c.username.replace(/'/g, "\\'")}')">
                                <i class="bi bi-send"></i>
                            </button>
                            <button class="btn btn-outline-secondary btn-sm" onclick="toggleImageCommentReplyForm(${c.id}, '')">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>
                    </div>
                `;
                list.appendChild(div);
            });
        })
        .catch(e => console.error('Error loading comments:', e));
}

function toggleImageCommentLike(commentId) {
    fetch('/comment/like', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment_id: commentId, comment_type: 'image' })
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            const btn = document.getElementById('img-like-btn-' + commentId);
            const icon = document.getElementById('img-like-icon-' + commentId);
            const count = document.getElementById('img-like-count-' + commentId);
            if (count) count.textContent = d.likes_count;
            if (icon) {
                icon.className = d.liked ? 'bi bi-heart-fill' : 'bi bi-heart';
            }
            if (btn) {
                btn.className = btn.className.replace(d.liked ? 'text-white-50' : 'text-danger', d.liked ? 'text-danger' : 'text-white-50');
            }
        } else {
            alert('Error: ' + (d.error || 'No tienes permiso'));
        }
    })
    .catch(() => alert('Error al dar like'));
}

function editImageCommentLikes(commentId) {
    const count = document.getElementById('img-like-count-' + commentId);
    const currentCount = count ? count.textContent : '0';
    const newCount = prompt('Nuevo número de likes:', currentCount);
    if (newCount === null) return;
    const countNum = parseInt(newCount);
    if (isNaN(countNum) || countNum < 0) {
        alert('Por favor ingresa un número válido (0 o mayor)');
        return;
    }
    fetch('/comment/edit-likes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment_id: commentId, comment_type: 'image', likes_count: countNum })
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            if (count) count.textContent = d.likes_count;
        } else {
            alert('Error: ' + d.error);
        }
    })
    .catch(() => alert('Error al editar likes'));
}

function editImageComment(commentId) {
    const contentEl = document.getElementById('img-comment-content-' + commentId);
    if (!contentEl) return;
    const current = contentEl.textContent;
    const newContent = prompt('Editar comentario:', current);
    if (newContent === null || newContent.trim() === '') return;
    const formData = new FormData();
    formData.append('content', newContent.trim());
    fetch('/image/comment/' + commentId + '/edit', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                contentEl.textContent = d.content;
            } else {
                alert('Error: ' + d.error);
            }
        })
        .catch(() => alert('Error al editar comentario'));
}

function deleteImageComment(commentId) {
    if (!confirm('¿Eliminar este comentario?')) return;
    fetch('/image/comment/' + commentId + '/delete', { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                const el = document.getElementById('img-comment-' + commentId);
                if (el) el.remove();
            } else {
                alert('Error: ' + d.error);
            }
        })
        .catch(() => alert('Error al eliminar comentario'));
}


// Search functionality
// Las funciones de búsqueda (performSearch, closeSearchAndLoad) y el modal se manejan centralizadamente en base.html

function loadImage(imageId, isVideo) {
    const img   = document.getElementById('mainImage');
    const inp   = document.getElementById('currentImageId');
    const dl    = document.getElementById('currentDownloadUrl');
    const nm    = document.getElementById('imageFilename');
    const wrap  = document.getElementById('imageWrap');
    if (!img || !inp || !wrap) return;

    fetch('/image/' + imageId + '/info')
        .then(r => r.json())
        .then(d => {
            const url = d.url;
            const currentIsVideo = img.tagName === 'VIDEO';
            const needSwap = (d.is_video !== currentIsVideo);

            if (needSwap) {
                const el = document.createElement(d.is_video ? 'video' : 'img');
                el.id        = 'mainImage';
                el.className = img.className;
                el.src       = url;
                if (d.is_video) {
                    el.controls = true;
                    el.autoplay = true;
                    el.muted    = true;
                    el.loop     = true;
                }
                el.addEventListener('click', openLightbox);
                wrap.replaceChild(el, img);
            } else {
                img.src = url;
                if (img.tagName === 'VIDEO') img.load();
            }

            inp.value = imageId;
            if (nm) nm.textContent = d.filename;
            if (dl) dl.value = d.download_url;

            // Limpiar estado de botones de rating
            document.querySelectorAll('.rbtn').forEach(b => {
                b.disabled = false;
                b.classList.remove('selected');
            });
            
            // Actualizar favoritos
            const hb = document.getElementById('heartBtn');
            if (hb) {
                const fav = !!d.is_favorited;
                hb.classList.toggle('favorited', fav);
                hb.textContent = fav ? '\u2764\uFE0F' : '\uD83E\uDD0D';
                hb.title = fav ? 'Quitar de favoritos' : 'Guardar en favoritos';
            }

            // Efecto Confeti
            const card = document.getElementById('imageCard');
            if (card) {
                card.dataset.hasConfetti = d.has_confetti ? 'true' : 'false';
            }
            const confIcon = document.getElementById('confettiIcon');
            if (confIcon) {
                confIcon.className = d.has_confetti ? 'bi bi-sparkles text-warning' : 'bi bi-sparkles text-white-50';
            }
            if (d.has_confetti) {
                setTimeout(triggerConfetti, 500);
            }

            busy = false;
            loadComments();
        })
        .catch(e => {
            console.error('Error in loadImage:', e);
            busy = false;
        });
}

document.addEventListener('DOMContentLoaded', function() {
    // Cargar comentarios al iniciar si hay imagen
    if (document.getElementById('currentImageId')) {
        loadComments();
    }

    // Disparar confeti al iniciar si la imagen tiene el efecto configurado
    const card = document.getElementById('imageCard');
    if (card && card.dataset.hasConfetti === 'true') {
        setTimeout(triggerConfetti, 500);
    }

    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const imageId = document.getElementById('currentImageId').value;
            const formData = new FormData(commentForm);
            
            fetch('/image/' + imageId + '/comment', {
                method: 'POST',
                body: formData
            })
            .then(r => r.json())
            .then(d => {
                if (d.success) {
                    commentForm.reset();
                    loadComments();
                } else if (d.error) {
                    alert(d.error);
                }
            })
            .catch(e => console.error('Error adding comment:', e));
        });
    }
});

// Cerrar menú de opciones al hacer clic fuera
document.addEventListener('click', function(e) {
    const menu = document.getElementById('optionsMenu');
    const btn = document.getElementById('floatingOptionsBtn');
    if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
        menu.style.display = 'none';
    }
});

function openStoryModal() {
    const modal = new bootstrap.Modal(document.getElementById('storyModal'));
    modal.show();
    
    // Inicializar Quill editor si no existe
    if (!quillEditor) {
        quillEditor = new Quill('#storyEditor', {
            theme: 'snow',
            placeholder: 'Escribe tu historia aquí...',
            modules: {
                toolbar: [
                    ['bold', 'italic', 'underline'],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    ['clean']
                ]
            }
        });
    }
}

function submitStory() {
    const title = document.getElementById('storyTitle').value.trim();
    const content = quillEditor ? quillEditor.root.innerHTML.trim() : '';
    
    if (!title || !content || content === '<p><br></p>') {
        alert('Por favor completa el título y el contenido de tu historia');
        return;
    }
    
    fetch('/stories/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title, content: content })
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            alert('¡Tu historia ha sido guardada!');
            const modal = bootstrap.Modal.getInstance(document.getElementById('storyModal'));
            modal.hide();
            document.getElementById('storyTitle').value = '';
            if (quillEditor) quillEditor.setText('');
        } else {
            alert('Error: ' + d.error);
        }
    })
    .catch(e => {
        alert('Error al guardar la historia');
    });
}

function rateImage(r) {
    if (busy) return;
    const id = document.getElementById('currentImageId')?.value;
    if (!id) return;
    busy = true;
    document.querySelectorAll('.rbtn').forEach(b => {
        b.disabled = true;
        if (parseInt(b.dataset.rating) === r) b.classList.add('selected');
    });
    document.getElementById('imgOverlay')?.classList.add('active');
    fetch('/rate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_id: parseInt(id), rating: r })
    })
    .then(r => r.json())
    .then(d => {
        if (d.error) { console.warn('Rate error:', d.error); loadNext(); return; }
        const n = document.getElementById('counterNum');
        if (n) n.textContent = d.total_rated;
        const rp = document.getElementById('ratePrompt');
        if (rp && d.total_rated >= 1) rp.textContent = '📊 ¿Cuál foto te gusta más?';
        if (d.total_rated > 1) {
            const gh = document.getElementById('gameHeader');
            if (gh) gh.classList.add('d-none');
        }
        // Actualizar contador de favoritos en la barra de navegación
        const navCount = document.getElementById('navFavCount');
        if (navCount && d.favorites_count !== undefined) {
            navCount.textContent = d.favorites_count;
        }
        // Si es rating 1 y el usuario es colaboradora (superusuario o nitalaosita), mostrar modal de eliminación
        console.log('DEBUG - Rating:', r, 'is_collaborator:', d.is_collaborator, 'Response:', d);
        if (r === 1 && d.is_collaborator) {
            console.log('DEBUG - Mostrando modal de eliminación');
            showDeleteImageModal();
            return;
        }
        if (d.series_message) {
            const m = document.getElementById('seriesMessage');
            const c = document.getElementById('seriesCount');
            if (m) m.textContent = d.series_message;
            if (c) c.textContent = d.total_rated;
            const modal = new bootstrap.Modal(document.getElementById('seriesModal'));
            modal.show();
            document.getElementById('continueBtn').addEventListener('click', () => loadNext(), { once: true });
        } else {
            setTimeout(() => loadNext(), 280);
        }
    })
    .catch(e => { console.error('Rate fetch error:', e); loadNext(); });
}

function loadNext() {
    fetch('/next-image')
    .then(r => r.json())
    .then(d => {
        if (d.no_more) { window.location.reload(); return; }
        const img = document.getElementById('mainImage');
        const inp = document.getElementById('currentImageId');
        const nm  = document.getElementById('imageFilename');
        const ov  = document.getElementById('imgOverlay');
        const wrap = document.getElementById('imageWrap');
        
        // Crear elemento correcto (img o video) según el tipo
        const isVideo = d.is_video;
        const newElement = document.createElement(isVideo ? 'video' : 'img');
        newElement.id = 'mainImage';
        newElement.className = 'game-img img-clickable';
        newElement.src = d.url;
        newElement.alt = d.filename;
        
        if (isVideo) {
            newElement.controls = true;
            newElement.autoplay = true;
            newElement.muted = true;
            newElement.loop = true;
        }
        
        // Función para actualizar UI después de cargar
        const updateUI = () => {
            inp.value = d.id;
            if (nm) nm.textContent = d.filename;
            wrap.replaceChild(newElement, img);
            newElement.style.opacity = '1';
            newElement.style.transition = 'opacity 0.35s ease';
            // Agregar event listener para abrir lightbox al hacer clic
            newElement.addEventListener('click', openLightbox);
            ov?.classList.remove('active');
            const dl  = document.getElementById('currentDownloadUrl');
            if (dl) dl.value = d.download_url || (d.url + '/download');
            if (d.image_message) showImageToast(d.image_message);
            const hb  = document.getElementById('heartBtn');
            if (hb) {
                const fav = !!d.is_favorited;
                hb.classList.toggle('favorited', fav);
                hb.textContent = fav ? '\u2764\uFE0F' : '\uD83E\uDD0D';
                hb.title = fav ? 'Quitar de favoritos' : 'Guardar en favoritos';
            }
            
            // Efecto Confeti
            const card = document.getElementById('imageCard');
            if (card) {
                card.dataset.hasConfetti = d.has_confetti ? 'true' : 'false';
            }
            const confIcon = document.getElementById('confettiIcon');
            if (confIcon) {
                confIcon.className = d.has_confetti ? 'bi bi-sparkles text-warning' : 'bi bi-sparkles text-white-50';
            }
            if (d.has_confetti) {
                setTimeout(triggerConfetti, 500);
            }

            document.querySelectorAll('.rbtn').forEach(b => {
                b.disabled = false;
                b.classList.remove('selected');
            });
            busy = false;
            
            // Cargar comentarios de la nueva imagen siempre
            loadComments();
            
            // Mostrar pregunta de imagen si existe
            if (d.image_question) {
                showImageQuestionModal(d.image_question);
            }
            // Mostrar mensaje programado si existe
            if (d.scheduled_message) {
                showScheduledMessageModal(d.scheduled_message);
            }
        };
        
        // Pre-cargar antes de cambiar (solo para imágenes)
        if (!isVideo) {
            const preloadImg = new Image();
            preloadImg.onload = () => {
                img.style.opacity = '0';
                setTimeout(updateUI, 50);
            };
            preloadImg.onerror = () => {
                img.style.opacity = '0';
                setTimeout(updateUI, 50);
            };
            preloadImg.src = d.url;
        } else {
            // Video no necesita preload
            img.style.opacity = '0';
            setTimeout(updateUI, 50);
        }
    })
    .catch(e => {
        console.error('Next image:', e);
        busy = false;
        document.querySelectorAll('.rbtn').forEach(b => {
            b.disabled = false;
            b.classList.remove('selected');
        });
        document.getElementById('imgOverlay')?.classList.remove('active');
    });
}

function showImageToast(msg) {
    var existing = document.getElementById('imgToast');
    if (existing) existing.remove();
    var t = document.createElement('div');
    t.id = 'imgToast';
    t.className = 'img-toast';
    t.textContent = msg;
    document.getElementById('imageCard')?.appendChild(t);
    setTimeout(function () { t.classList.add('img-toast-show'); }, 50);
    setTimeout(function () {
        t.classList.remove('img-toast-show');
        setTimeout(function () { t.remove(); }, 400);
    }, 4000);
}

function showScheduledMessageModal(messageData) {
    const messageText = document.getElementById('scheduledMessageText');
    const messageId = document.getElementById('scheduledMessageId');
    const responseInput = document.getElementById('scheduledMessageResponse');
    
    messageText.textContent = messageData.message;
    messageId.value = messageData.id;
    responseInput.value = '';
    
    const modalElement = document.getElementById('scheduledMessageModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    document.getElementById('scheduledMessageSubmit').addEventListener('click', function () {
        const response = responseInput.value.trim();
        
        fetch('/scheduled-message/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message_id: messageData.id,
                response: response
            })
        }).then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) {
                modal.hide();
                setTimeout(() => loadNext(), 300);
            } else {
                alert(d.error || 'Error al enviar respuesta');
            }
        }).catch(function() {
            alert('Error de conexión');
        });
    });
    
    document.getElementById('scheduledMessageSkip').addEventListener('click', function () {
        modal.hide();
        setTimeout(() => loadNext(), 300);
    });
}

// FUNCIÓN BLINDADA: Modal de eliminación de imágenes para colaboradoras (superusuarios)
// Esta funcionalidad es crítica y no debe ser eliminada accidentalmente
// Solo se activa cuando: rating === 1 Y usuario es superusuario
function showDeleteImageModal() {
    const imageId = document.getElementById('currentImageId').value;
    if (!imageId) {
        console.error('No se pudo obtener el ID de la imagen actual');
        loadNext();
        return;
    }
    
    document.getElementById('deleteImageId').value = imageId;
    
    const modalElement = document.getElementById('deleteImageModal');
    if (!modalElement) {
        console.error('Modal de eliminación no encontrado en el DOM');
        loadNext();
        return;
    }
    
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    // Manejar cancelación - simplemente carga la siguiente imagen
    document.getElementById('deleteImageCancel').onclick = function () {
        modal.hide();
        setTimeout(() => loadNext(), 300);
    };
    
    // Manejar confirmación - elimina la imagen y carga la siguiente
    document.getElementById('deleteImageConfirm').onclick = function () {
        const btn = this;
        btn.disabled = true;
        btn.textContent = 'Eliminando...';
        
        fetch('/image/' + imageId + '/delete', {
            method: 'POST'
        }).then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) {
                modal.hide();
                setTimeout(() => loadNext(), 300);
            } else {
                alert(d.error || 'Error al eliminar imagen');
                btn.disabled = false;
                btn.textContent = 'Eliminar Permanentemente';
            }
        }).catch(function() {
            alert('Error de conexión al eliminar la imagen');
            btn.disabled = false;
            btn.textContent = 'Eliminar Permanentemente';
        });
    };
}

function openLightbox() {
    const img = document.getElementById('mainImage');
    const fn  = document.getElementById('imageFilename');
    const dl  = document.getElementById('currentDownloadUrl');
    document.getElementById('lightboxImg').src = img.src;
    document.getElementById('lightboxFilename').textContent = fn ? fn.textContent : '';
    document.getElementById('lightboxDownload').href = dl ? dl.value : img.src;
    new bootstrap.Modal(document.getElementById('lightboxModal')).show();
}

function toggleFavorite(e) {
    e.stopPropagation();
    const btn = document.getElementById('heartBtn');
    const id  = document.getElementById('currentImageId')?.value;
    if (!id) return;
    fetch('/img/' + id + '/favorite', { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            btn.classList.toggle('favorited', d.favorited);
            btn.textContent = d.favorited ? '\u2764\uFE0F' : '\uD83E\uDD0D';
            btn.title = d.favorited ? 'Quitar de favoritos' : 'Guardar en favoritos';
            const navBtn   = document.getElementById('navFavBtn');
            const navCount = document.getElementById('navFavCount');
            if (navBtn) navBtn.classList.toggle('d-none', d.favorites_count === 0);
            if (navCount) navCount.textContent = d.favorites_count;
        });
}

document.addEventListener('DOMContentLoaded', () => {
    const img = document.getElementById('mainImage');
    if (img) {
        img.style.transition = 'opacity 0.35s ease';
        img.addEventListener('click', openLightbox);
    }
    const hb = document.getElementById('heartBtn');
    if (hb) hb.addEventListener('click', toggleFavorite);
});
