import $ from 'jquery';

const translations = require('../../../../static/assets/plugins.assetman/translations.json');

function current() {
    return document.documentElement.getAttribute('lang');
}

function fallback() {
    return translations.langs[0];
}

function t(msg_id, args, language) {
    if (typeof language === 'undefined')
        language = current();

    // Search for language
    if (translations.langs.indexOf(language) < 0) {
        if (translations.langs.length && language !== fallback())
            return t(msg_id, args, fallback());
        else
            return msg_id;
    }

    let pkg = $('meta[name="pytsite-theme"]').attr('content'); // Default package
    const msg_parts = msg_id.split('@');

    // Split message ID into package name and message ID
    if (msg_parts.length === 2) {
        pkg = msg_parts[0];
        msg_id = msg_parts[1];
    }

    // If package is not found in translations for given language
    if (!(pkg in translations.translations[language])) {
        if (!pkg.startsWith('plugins.')) {
            // Try to search translation with 'plugins' package name
            return t(`plugins.${pkg}@${msg_id}`);
        }
        else if (language !== fallback()) {
            // Try to translate via fallback language
            return t(`${pkg}@${msg_id}`, args, fallback());
        }
        else {
            // Return string as is
            console.warn(`Translations is not found for package '${pkg}', language '${language}'`);
            return `${pkg}@${msg_id}`;
        }
    }

    // Get all translations for package
    const pkg_strings = translations.translations[language][pkg];

    // If message ID is not found in package translations
    if (!(msg_id in pkg_strings)) {
        if (language !== fallback()) {
            // Try to translate via fallback language
            return t(`${pkg}@${msg_id}`, args, fallback());
        }
        else {
            // Return string as is
            console.warn("Translation message ID '" + msg_id + "' is not found for package '" + pkg + "', language '" + language + "'");
            return `${pkg}@${msg_id}`;
        }
    }

    // Processing placeholders
    let translation = pkg_strings[msg_id];
    for (let k in args) {
        if (args.hasOwnProperty(k))
            translation = translation.replace(`:${k}`, args[k]);
    }

    return translation;
}

const api = {
    current: current,
    t: t,
};

export default api;
