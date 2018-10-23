import $ from 'jquery';
import lang from './lang';

function url(urlStr, query = {}) {
    const r = urlStr.startsWith('http') ? new URL(urlStr) : new URL(urlStr, window.location.origin);
    query = Object.assign(parseQueryString(r.search.replace(/^\?/, '')), query);

    if (query)
        r.search = '?' + $.param(query);

    return r.href;
}

function assetUrl(urlStr) {
    if (urlStr.indexOf('/') === 0 || urlStr.indexOf('http') === 0)
        return urlStr;

    let pkgName = 'default';
    let assetPath = urlStr;
    const urlParts = urlStr.split('@');

    if (urlParts.length === 2) {
        pkgName = urlParts[0];
        assetPath = urlParts[1];
    }

    return location.origin + '/assets/' + pkgName + '/' + assetPath
}

function _loadResource(resType, resLoc, async) {
    resLoc = assetUrl(resLoc).replace(/\?v=[0-9a-f]+/, '');

    // Async is default for CSS but not for JS
    if (async === undefined)
        async = resType !== 'js';

    // Call self in async manner
    if (async === true) {
        const deferred = $.Deferred();

        setTimeout(function () {
            // It is important to pass 'false' as last argument!
            _loadResource(resType, resLoc, false);
            deferred.resolve(resLoc);
        }, 0);

        return deferred;
    }

    switch (resType) {
        case 'css':
            if (!$('link[href^="' + resLoc + '"]').length)
                $('head').append($('<link rel="stylesheet" href="' + resLoc + '">'));
            break;

        case 'js':
            if (!$('script[src^="' + resLoc + '"]').length)
                $('body').append($('<script type="text/javascript" src="' + resLoc + '"></script>'));
            break;

        default:
            throw 'Unexpected resource type: ' + resType;
    }
}

function loadCSS(location, async) {
    return _loadResource('css', location, async)
}

function loadJS(location, async) {
    return _loadResource('js', location, async)
}

function load(location, async) {
    if (location.endsWith('.css')) {
        return loadCSS(location, async);
    }
    else if (location.endsWith('.js')) {
        return loadJS(location, async);
    }
    else {
        throw 'Cannot determine type of asset for location ' + location;
    }
}

function parseQueryString(s, skipEmpty = true) {
    const r = {};

    s = s.split('&');
    for (let i = 0; i < s.length; ++i) {
        const part = s[i].split('=');
        if (part.length === 1 && part[0].length) {
            r[decodeURIComponent(part[0])] = null;
        }
        else if (part.length === 2) {
            let k = decodeURIComponent(part[0].replace('+', '%20'));
            let v = decodeURIComponent(part[1].replace('+', '%20'));

            if (k.indexOf('[]') > 0) {
                k = k.replace('[]', '');

                if (k in r && !(r[k] instanceof Array))
                    r[k] = [r[k]];
                else
                    r[k] = [];

                r[k].push(v);
            }
            else {
                r[k] = v;
            }
        }
    }

    for (let l in r) {
        if (!r.hasOwnProperty(l))
            continue;

        if (r[l] instanceof Array && r[l].length === 1)
            r[l] = r[l][0];

        if (skipEmpty === true && !r[l])
            delete r[l];
    }

    return r;
}

function parseLocation() {
    return {
        href: window.location.href,
        origin: window.location.origin,
        protocol: window.location.protocol,
        host: window.location.host,
        port: window.location.port,
        pathname: window.location.pathname,
        query: parseQueryString(window.location.search.replace(/^\?/, '')),
        hash: parseQueryString(window.location.hash.replace(/^#/, ''))
    };
}

function encodeQuery(data) {
    let r = [];
    for (let k in data) {
        if (data.hasOwnProperty(k)) {
            if (data.k instanceof Array) {
                for (let l = 0; l < data.k.length; l++) {
                    r.push(encodeURIComponent(k) + "[]=" + encodeURIComponent(data[k][l]));
                }
            }
            else {
                r.push(encodeURIComponent(k) + "=" + encodeURIComponent(data[k]));
            }
        }
    }

    return r.join("&");
}

const api = {
    url: url,
    assetUrl: assetUrl,
    loadJS: loadJS,
    loadCSS: loadCSS,
    load: load,
    parseQueryString: parseQueryString,
    parseLocation: parseLocation,
    encodeQuery: encodeQuery
};

export {lang};
export default api;
