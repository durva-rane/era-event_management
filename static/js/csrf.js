(() => {
  const readCookie = name => document.cookie.split('; ').find(value => value.startsWith(`${name}=`))?.slice(name.length + 1) || '';
  const baseFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const method = String(init.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
    const target = new URL(typeof input === 'string' ? input : input.url, window.location.href);
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && target.origin === window.location.origin) {
      const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
      headers.set('X-CSRF-Token', decodeURIComponent(readCookie('era_csrf_token')));
      init = {...init, headers, credentials: 'same-origin'};
    }
    return baseFetch(input, init);
  };
})();
