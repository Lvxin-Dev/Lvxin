document.addEventListener('DOMContentLoaded', () => {
    const i18next = window.i18next;
    const i18nextHttpBackend = window.i18nextHttpBackend;
    const i18nextBrowserLanguageDetector = window.i18nextBrowserLanguageDetector;

    // Check if required libraries are loaded
    if (!i18next || !i18nextHttpBackend || !i18nextBrowserLanguageDetector) {
        console.error("i18next or one of its plugins is not loaded.");
        return;
    }

    // Get stored language preference or default to Chinese
    const storedLang = localStorage.getItem('i18nextLng');
    const defaultLang = 'zh';

    i18next
        .use(i18nextHttpBackend)
        .use(i18nextBrowserLanguageDetector)
        .init({
            fallbackLng: defaultLang,
            lng: storedLang || defaultLang, // Use stored language or default to Chinese
            debug: false, // Set to false in production
            detection: {
                order: ['localStorage', 'navigator'],
                caches: ['localStorage'],
                lookupLocalStorage: 'i18nextLng'
            },
            backend: {
                loadPath: '/static/locales/{{lng}}/translation.json',
                requestOptions: {
                    cache: 'default'
                }
            },
            interpolation: {
                escapeValue: false // Not needed for react as it escapes by default
            }
        }, function(err, t) {
            if (err) {
                console.error('Error loading translations:', err);
                return;
            }
            // Initial content update
            updateContent();
            updateHtmlLang(i18next.language);
            updateLanguageSelector(i18next.language);
        });

    function updateContent() {
        try {
            document.querySelectorAll('[data-i18n]').forEach(element => {
                const key = element.getAttribute('data-i18n');
                if (!key) return;

                const options = {};
                try {
                    const optionsAttr = element.getAttribute('data-i18n-options');
                    if (optionsAttr) {
                        Object.assign(options, JSON.parse(optionsAttr));
                    }
                } catch (e) {
                    console.warn('Invalid data-i18n-options:', e);
                }

                const translation = i18next.t(key, options);
                if (translation !== key) { // Only update if we got a valid translation
                    if (element.tagName.toLowerCase() === 'input' && element.type === 'text') {
                        element.placeholder = translation;
                    } else if (element.tagName.toLowerCase() === 'button') {
                        // For buttons, update both inner text and any relevant attributes
                        element.innerHTML = translation;
                        if (element.getAttribute('title')) {
                            element.setAttribute('title', translation);
                        }
                    } else {
                        element.innerHTML = translation;
                    }
                }
            });

            // Update document title if it has a data-i18n attribute
            const titleElement = document.querySelector('title[data-i18n]');
            if (titleElement) {
                const titleKey = titleElement.getAttribute('data-i18n');
                const translation = i18next.t(titleKey);
                if (translation !== titleKey) {
                    document.title = translation;
                }
            }
        } catch (error) {
            console.error('Error updating content:', error);
        }
    }
    window.updateI18nContent = updateContent;
    
    function updateHtmlLang(lng) {
        document.documentElement.lang = lng.split('-')[0];
    }

    function updateLanguageSelector(lng) {
        const languageSelector = document.getElementById('language-selector');
        if (languageSelector) {
            const simpleLng = lng.split('-')[0];
            languageSelector.value = simpleLng;
            localStorage.setItem('i18nextLng', simpleLng);
        }
    }

    // Listen for language changes
    i18next.on('languageChanged', (lng) => {
        updateContent();
        updateHtmlLang(lng);
        updateLanguageSelector(lng);
        localStorage.setItem('i18nextLng', lng.split('-')[0]);
    });

    // Set up language selector
    const languageSelector = document.getElementById('language-selector');
    if (languageSelector) {
        // Set initial value to Chinese if no stored preference
        if (!storedLang) {
            languageSelector.value = defaultLang;
        }
        
        languageSelector.addEventListener('change', (e) => {
            const newLang = e.target.value;
            i18next.changeLanguage(newLang).catch(err => {
                console.error('Error changing language:', err);
            });
        });
    }
}); 