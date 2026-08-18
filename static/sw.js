'use strict';
const CACHE='photobearrate-v6',PRECACHE=['/static/manifest.json','/static/icons/icon.svg'],SKIP=['/rate','/next-image','/reset','/feedback','/set-name','/clear-name','/login','/logout','/admin','/img','/stories'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(PRECACHE)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{const req=e.request,url=new URL(req.url);if(req.method!=='GET'||url.origin!==location.origin||SKIP.some(p=>url.pathname.startsWith(p)))return;if(url.pathname.startsWith('/static/')){e.respondWith(caches.match(req).then(c=>{if(c)return c;return fetch(req).then(r=>{if(!r||r.status!==200||r.redirected)return r;const cl=r.clone();caches.open(CACHE).then(c=>c.put(req,cl));return r})}));return}});

// Manejar eventos push
self.addEventListener('push', event => {
    let payload = {};
    try { payload = JSON.parse(event.data.text()); } catch(e) {}

    const isCall = payload.type === 'call';
    const isChat = payload.type === 'chat';
    const isWelcome = payload.type === 'welcome';
    
    const options = {
        body: payload.body || (event.data ? event.data.text() : 'Tienes una nueva notificación'),
        icon: '/static/icons/icon.svg',
        badge: '/static/icons/icon.svg',
        vibrate: isCall
            ? [400,100,400,100,400,200,400,100,400,100,400]
            : isChat ? [200, 100, 200] : isWelcome ? [300, 100, 300, 100, 300] : [200, 100, 200],
        tag: isCall ? 'call-nita' : isChat ? 'chat-message' : isWelcome ? 'welcome-message' : 'default',
        renotify: isCall || isChat || isWelcome,
        requireInteraction: isCall,
        data: { type: payload.type, url: '/', dateOfArrival: Date.now() },
        actions: [
            { action: 'open', title: isCall ? '📲 Abrir' : isChat ? '💬 Ver mensaje' : isWelcome ? '🌸 Ver' : 'Ver' },
            { action: 'close', title: 'Cerrar' }
        ]
    };

    const title = payload.title || '🐻 Galería Rosa';
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// Manejar clic en notificación
self.addEventListener('notificationclick', event => {
    event.notification.close();

    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});
