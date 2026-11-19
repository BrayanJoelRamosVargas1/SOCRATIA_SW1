/* Push only: never cache authenticated pages, PDFs, camera or API responses. */
self.addEventListener('push', event => {
  let data={};try{data=event.data.json();}catch{return;}
  event.waitUntil(self.registration.showNotification('Socratia',{
    body:data.body || 'Tu preparación tiene novedades.',tag:data.tag || 'socratia',
    icon:'/icon-192.png',data:{url:data.url || '/documents'}
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target=new URL(event.notification.data?.url || '/documents',self.location.origin);
  if(target.origin!==self.location.origin)return;
  event.waitUntil(clients.matchAll({type:'window'}).then(async windows=>{
    for(const client of windows){if('focus' in client){await client.navigate(target.href);return client.focus();}}
    return clients.openWindow(target.href);
  }));
});
