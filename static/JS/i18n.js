document.addEventListener('DOMContentLoaded', () => {
    const i18next = window.i18next;
    const i18nextHttpBackend = window.i18nextHttpBackend;
    const i18nextBrowserLanguageDetector = window.i18nextBrowserLanguageDetector;

    if (!i18next || !i18nextHttpBackend || !i18nextBrowserLanguageDetector) {
        console.error("i18next or one of its plugins is not loaded.");
        return;
    }

    i18next
        .use(i18nextHttpBackend)
        .use(i18nextBrowserLanguageDetector)
        .init({
            fallbackLng: 'zh',
            debug: true,
            detection: {
                order: ['localStorage', 'navigator'],
                caches: ['localStorage']
            },
            backend: {
                loadPath: '/static/locales/{{lng}}/translation.json'
            }
        }, (err, t) => {
            if (err) return console.error(err);
            updateContent();
            updateHtmlLang(i18next.language);
            updateLanguageSelector(i18next.language);
        });

    function updateContent() {
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const options = JSON.parse(element.getAttribute('data-i18n-options') || '{}');
            element.innerHTML = i18next.t(key, options);
        });
        const titleElement = document.querySelector('title[data-i18n]');
        if(titleElement) {
            const titleKey = titleElement.getAttribute('data-i18n');
            document.title = i18next.t(titleKey);
        }
    }
    
    function updateHtmlLang(lng) {
        document.documentElement.lang = lng.split('-')[0];
    }

    function updateLanguageSelector(lng) {
        const languageSelector = document.getElementById('language-selector');
        if (languageSelector) {
            languageSelector.value = lng.split('-')[0];
        }
    }

    i18next.on('languageChanged', (lng) => {
        updateContent();
        updateHtmlLang(lng);
    });

    const languageSelector = document.getElementById('language-selector');
    if (languageSelector) {
        languageSelector.addEventListener('change', (e) => {
            i18next.changeLanguage(e.target.value);
        });
    }
}); 