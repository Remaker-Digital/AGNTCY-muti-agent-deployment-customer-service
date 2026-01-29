/**
 * ============================================================================
 * AGNTCY Chat Widget - Embedded JavaScript Customer Service Widget
 * ============================================================================
 *
 * Purpose: Provide embeddable chat widget for merchant websites
 *
 * Features:
 * - Single script embed for easy integration
 * - Configurable theming via CSS variables
 * - Session persistence (anonymous → identified → authenticated)
 * - Multi-language support (en, fr-CA, es)
 * - Responsive design (mobile/desktop)
 * - WCAG 2.1 accessibility compliance
 *
 * Usage:
 *   <script src="https://cdn.example.com/agntcy-chat.min.js"></script>
 *   <script>
 *     AGNTCYChat.init({
 *       merchantId: 'your-merchant-id',
 *       primaryColor: '#5c6ac4',
 *       position: 'bottom-right',
 *       language: 'en'
 *     });
 *   </script>
 *
 * Phase Assignment:
 * - Phase 6: MVP widget with session integration
 * - Phase 7: Headless API for custom implementations
 *
 * Related Documentation:
 * - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q1.B)
 * - Session Integration: shared/auth/session_manager.py
 *
 * Cost Impact: +$5-10/month for CDN hosting (Azure Blob + CDN)
 * ============================================================================
 */

(function(window, document) {
    'use strict';

    // ========================================================================
    // Configuration and Constants
    // ========================================================================

    const VERSION = '1.0.0';
    const DEFAULT_CONFIG = {
        merchantId: null,
        apiEndpoint: null,  // Auto-detected or configured
        primaryColor: '#5c6ac4',
        secondaryColor: '#ffffff',
        position: 'bottom-right',
        language: 'en',
        greeting: 'Hi! How can I help you today?',
        placeholder: 'Type your message...',
        buttonText: 'Chat with us',
        showTimestamps: true,
        enableSounds: false,
        enableFileUpload: false,  // Phase 7
        maxMessageLength: 4096,
        autoOpen: false,
        minimized: true,
        zIndex: 999999,
        // Session options
        persistSession: true,
        sessionStorageKey: 'agntcy_chat_session',
        // Branding
        showPoweredBy: true,
        logoUrl: null,
        agentName: 'Support Assistant',
        agentAvatar: null,
    };

    // Supported languages
    const LANGUAGES = {
        en: {
            greeting: 'Hi! How can I help you today?',
            placeholder: 'Type your message...',
            buttonText: 'Chat with us',
            sendButton: 'Send',
            typingIndicator: 'typing...',
            connectionError: 'Connection error. Retrying...',
            sessionExpired: 'Session expired. Starting new conversation.',
            poweredBy: 'Powered by AGNTCY',
            close: 'Close chat',
            minimize: 'Minimize chat',
            expand: 'Expand chat',
        },
        'fr-CA': {
            greeting: 'Bonjour! Comment puis-je vous aider?',
            placeholder: 'Tapez votre message...',
            buttonText: 'Discuter avec nous',
            sendButton: 'Envoyer',
            typingIndicator: 'en train d\'écrire...',
            connectionError: 'Erreur de connexion. Nouvelle tentative...',
            sessionExpired: 'Session expirée. Nouvelle conversation.',
            poweredBy: 'Propulsé par AGNTCY',
            close: 'Fermer le chat',
            minimize: 'Réduire le chat',
            expand: 'Agrandir le chat',
        },
        es: {
            greeting: '¡Hola! ¿Cómo puedo ayudarte hoy?',
            placeholder: 'Escribe tu mensaje...',
            buttonText: 'Chatea con nosotros',
            sendButton: 'Enviar',
            typingIndicator: 'escribiendo...',
            connectionError: 'Error de conexión. Reintentando...',
            sessionExpired: 'Sesión expirada. Iniciando nueva conversación.',
            poweredBy: 'Desarrollado por AGNTCY',
            close: 'Cerrar chat',
            minimize: 'Minimizar chat',
            expand: 'Expandir chat',
        },
    };

    // ========================================================================
    // Widget State
    // ========================================================================

    let config = { ...DEFAULT_CONFIG };
    let strings = LANGUAGES.en;
    let isOpen = false;
    let isMinimized = true;
    let isConnected = false;
    let isTyping = false;
    let sessionId = null;
    let authLevel = 'anonymous';
    let messages = [];
    let retryCount = 0;
    const MAX_RETRIES = 3;

    // DOM Elements
    let widgetContainer = null;
    let chatWindow = null;
    let messageContainer = null;
    let inputField = null;
    let sendButton = null;
    let toggleButton = null;

    // ========================================================================
    // Initialization
    // ========================================================================

    /**
     * Initialize the chat widget with configuration.
     *
     * @param {Object} options - Widget configuration options
     */
    function init(options = {}) {
        // Merge config
        config = { ...DEFAULT_CONFIG, ...options };

        // Validate required config
        if (!config.merchantId) {
            console.error('[AGNTCY Chat] merchantId is required');
            return;
        }

        // Set language strings
        strings = LANGUAGES[config.language] || LANGUAGES.en;

        // Override strings if provided
        if (options.greeting) strings.greeting = options.greeting;
        if (options.placeholder) strings.placeholder = options.placeholder;
        if (options.buttonText) strings.buttonText = options.buttonText;

        // Auto-detect API endpoint if not provided
        if (!config.apiEndpoint) {
            config.apiEndpoint = detectApiEndpoint();
        }

        // Load or create session
        loadSession();

        // Inject CSS
        injectStyles();

        // Build widget DOM
        buildWidget();

        // Bind events
        bindEvents();

        // Show greeting if auto-open
        if (config.autoOpen) {
            openChat();
        }

        console.log(`[AGNTCY Chat] Widget initialized v${VERSION}`);
        console.log(`[AGNTCY Chat] Merchant: ${config.merchantId}, Session: ${sessionId}`);
    }

    /**
     * Detect API endpoint based on current context.
     */
    function detectApiEndpoint() {
        // Check for configured endpoint in script tag
        const scripts = document.querySelectorAll('script');
        for (const script of scripts) {
            if (script.src && script.src.includes('agntcy-chat')) {
                const url = new URL(script.src);
                return `${url.protocol}//${url.host}/api/v1`;
            }
        }

        // Fallback to localhost for development
        if (window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1') {
            return 'http://localhost:8080/api/v1';
        }

        // Production default
        return '/api/v1';
    }

    // ========================================================================
    // Session Management
    // ========================================================================

    /**
     * Load existing session from storage or create new one.
     */
    function loadSession() {
        if (!config.persistSession) {
            createNewSession();
            return;
        }

        try {
            const stored = localStorage.getItem(config.sessionStorageKey);
            if (stored) {
                const data = JSON.parse(stored);
                // Check if session is still valid (7 days)
                const expiresAt = new Date(data.expiresAt);
                if (expiresAt > new Date()) {
                    sessionId = data.sessionId;
                    authLevel = data.authLevel || 'anonymous';
                    messages = data.messages || [];
                    console.log(`[AGNTCY Chat] Loaded session: ${sessionId}`);
                    return;
                }
            }
        } catch (e) {
            console.warn('[AGNTCY Chat] Failed to load session:', e);
        }

        createNewSession();
    }

    /**
     * Create a new session.
     */
    function createNewSession() {
        sessionId = generateSessionId();
        authLevel = 'anonymous';
        messages = [];
        saveSession();
        console.log(`[AGNTCY Chat] Created new session: ${sessionId}`);
    }

    /**
     * Save session to storage.
     */
    function saveSession() {
        if (!config.persistSession) return;

        try {
            const expiresAt = new Date();
            expiresAt.setDate(expiresAt.getDate() + 7);

            localStorage.setItem(config.sessionStorageKey, JSON.stringify({
                sessionId,
                authLevel,
                messages: messages.slice(-50), // Keep last 50 messages
                expiresAt: expiresAt.toISOString(),
            }));
        } catch (e) {
            console.warn('[AGNTCY Chat] Failed to save session:', e);
        }
    }

    /**
     * Generate a unique session ID.
     */
    function generateSessionId() {
        return 'widget-' + Date.now().toString(36) + '-' +
               Math.random().toString(36).substr(2, 9);
    }

    /**
     * Update session with new auth level.
     */
    function updateAuthLevel(newLevel) {
        authLevel = newLevel;
        saveSession();
        console.log(`[AGNTCY Chat] Auth level updated: ${authLevel}`);
    }

    // ========================================================================
    // Widget UI Construction
    // ========================================================================

    /**
     * Inject widget CSS styles.
     */
    function injectStyles() {
        if (document.getElementById('agntcy-chat-styles')) return;

        const style = document.createElement('style');
        style.id = 'agntcy-chat-styles';
        style.textContent = getWidgetStyles();
        document.head.appendChild(style);
    }

    /**
     * Get widget CSS with theme variables.
     */
    function getWidgetStyles() {
        return `
            /* AGNTCY Chat Widget Styles */
            :root {
                --agntcy-primary: ${config.primaryColor};
                --agntcy-secondary: ${config.secondaryColor};
                --agntcy-text: #333333;
                --agntcy-text-light: #666666;
                --agntcy-border: #e0e0e0;
                --agntcy-bg: #ffffff;
                --agntcy-bg-light: #f5f5f5;
                --agntcy-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                --agntcy-radius: 12px;
                --agntcy-font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }

            .agntcy-chat-widget {
                position: fixed;
                ${config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
                ${config.position.includes('bottom') ? 'bottom: 20px;' : 'top: 20px;'}
                z-index: ${config.zIndex};
                font-family: var(--agntcy-font);
                font-size: 14px;
                line-height: 1.5;
            }

            /* Toggle Button */
            .agntcy-chat-toggle {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: var(--agntcy-primary);
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: var(--agntcy-shadow);
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .agntcy-chat-toggle:hover {
                transform: scale(1.05);
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
            }

            .agntcy-chat-toggle:focus {
                outline: 2px solid var(--agntcy-primary);
                outline-offset: 2px;
            }

            .agntcy-chat-toggle svg {
                width: 28px;
                height: 28px;
                fill: var(--agntcy-secondary);
            }

            .agntcy-chat-toggle.open svg.chat-icon { display: none; }
            .agntcy-chat-toggle:not(.open) svg.close-icon { display: none; }

            /* Chat Window */
            .agntcy-chat-window {
                position: absolute;
                ${config.position.includes('bottom') ? 'bottom: 75px;' : 'top: 75px;'}
                ${config.position.includes('right') ? 'right: 0;' : 'left: 0;'}
                width: 370px;
                max-width: calc(100vw - 40px);
                height: 520px;
                max-height: calc(100vh - 120px);
                background: var(--agntcy-bg);
                border-radius: var(--agntcy-radius);
                box-shadow: var(--agntcy-shadow);
                display: none;
                flex-direction: column;
                overflow: hidden;
            }

            .agntcy-chat-window.open {
                display: flex;
                animation: agntcy-slide-in 0.3s ease-out;
            }

            @keyframes agntcy-slide-in {
                from {
                    opacity: 0;
                    transform: translateY(10px) scale(0.95);
                }
                to {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            /* Header */
            .agntcy-chat-header {
                background: var(--agntcy-primary);
                color: var(--agntcy-secondary);
                padding: 16px;
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .agntcy-chat-header-avatar {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: var(--agntcy-secondary);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 600;
                color: var(--agntcy-primary);
            }

            .agntcy-chat-header-info {
                flex: 1;
            }

            .agntcy-chat-header-name {
                font-weight: 600;
                font-size: 16px;
            }

            .agntcy-chat-header-status {
                font-size: 12px;
                opacity: 0.8;
            }

            .agntcy-chat-header-actions {
                display: flex;
                gap: 8px;
            }

            .agntcy-chat-header-actions button {
                background: none;
                border: none;
                cursor: pointer;
                padding: 4px;
                opacity: 0.8;
                transition: opacity 0.2s;
            }

            .agntcy-chat-header-actions button:hover {
                opacity: 1;
            }

            .agntcy-chat-header-actions svg {
                width: 20px;
                height: 20px;
                fill: var(--agntcy-secondary);
            }

            /* Messages Container */
            .agntcy-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                display: flex;
                flex-direction: column;
                gap: 12px;
                background: var(--agntcy-bg-light);
            }

            /* Message Bubbles */
            .agntcy-chat-message {
                max-width: 85%;
                padding: 12px 16px;
                border-radius: 16px;
                position: relative;
            }

            .agntcy-chat-message.user {
                align-self: flex-end;
                background: var(--agntcy-primary);
                color: var(--agntcy-secondary);
                border-bottom-right-radius: 4px;
            }

            .agntcy-chat-message.agent {
                align-self: flex-start;
                background: var(--agntcy-bg);
                color: var(--agntcy-text);
                border-bottom-left-radius: 4px;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
            }

            .agntcy-chat-message-time {
                font-size: 11px;
                opacity: 0.7;
                margin-top: 4px;
            }

            /* Typing Indicator */
            .agntcy-chat-typing {
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 12px 16px;
                background: var(--agntcy-bg);
                border-radius: 16px;
                align-self: flex-start;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
            }

            .agntcy-chat-typing span {
                width: 8px;
                height: 8px;
                background: var(--agntcy-text-light);
                border-radius: 50%;
                animation: agntcy-typing 1.4s infinite ease-in-out both;
            }

            .agntcy-chat-typing span:nth-child(1) { animation-delay: -0.32s; }
            .agntcy-chat-typing span:nth-child(2) { animation-delay: -0.16s; }

            @keyframes agntcy-typing {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }

            /* Input Area */
            .agntcy-chat-input {
                padding: 12px 16px;
                background: var(--agntcy-bg);
                border-top: 1px solid var(--agntcy-border);
                display: flex;
                gap: 8px;
                align-items: flex-end;
            }

            .agntcy-chat-input textarea {
                flex: 1;
                border: 1px solid var(--agntcy-border);
                border-radius: 20px;
                padding: 10px 16px;
                resize: none;
                max-height: 100px;
                font-family: inherit;
                font-size: 14px;
                outline: none;
                transition: border-color 0.2s;
            }

            .agntcy-chat-input textarea:focus {
                border-color: var(--agntcy-primary);
            }

            .agntcy-chat-input button {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: var(--agntcy-primary);
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.2s, opacity 0.2s;
            }

            .agntcy-chat-input button:hover:not(:disabled) {
                transform: scale(1.05);
            }

            .agntcy-chat-input button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .agntcy-chat-input button svg {
                width: 20px;
                height: 20px;
                fill: var(--agntcy-secondary);
            }

            /* Footer */
            .agntcy-chat-footer {
                padding: 8px 16px;
                text-align: center;
                font-size: 11px;
                color: var(--agntcy-text-light);
                background: var(--agntcy-bg);
                border-top: 1px solid var(--agntcy-border);
            }

            .agntcy-chat-footer a {
                color: var(--agntcy-primary);
                text-decoration: none;
            }

            /* Mobile Responsive */
            @media (max-width: 480px) {
                .agntcy-chat-window {
                    width: 100%;
                    max-width: 100%;
                    height: 100%;
                    max-height: 100%;
                    border-radius: 0;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                }

                .agntcy-chat-widget.open .agntcy-chat-toggle {
                    display: none;
                }
            }

            /* Accessibility */
            @media (prefers-reduced-motion: reduce) {
                .agntcy-chat-window.open,
                .agntcy-chat-toggle,
                .agntcy-chat-typing span {
                    animation: none;
                    transition: none;
                }
            }

            /* High Contrast */
            @media (prefers-contrast: high) {
                .agntcy-chat-message.agent {
                    border: 2px solid var(--agntcy-text);
                }
            }

            /* Screen Reader Only */
            .agntcy-sr-only {
                position: absolute;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: -1px;
                overflow: hidden;
                clip: rect(0, 0, 0, 0);
                border: 0;
            }
        `;
    }

    /**
     * Build the widget DOM structure.
     */
    function buildWidget() {
        // Create container
        widgetContainer = document.createElement('div');
        widgetContainer.className = 'agntcy-chat-widget';
        widgetContainer.setAttribute('role', 'region');
        widgetContainer.setAttribute('aria-label', 'Chat widget');

        // Create toggle button
        toggleButton = document.createElement('button');
        toggleButton.className = 'agntcy-chat-toggle';
        toggleButton.setAttribute('aria-label', strings.buttonText);
        toggleButton.innerHTML = `
            <svg class="chat-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
            </svg>
            <svg class="close-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
        `;

        // Create chat window
        chatWindow = document.createElement('div');
        chatWindow.className = 'agntcy-chat-window';
        chatWindow.setAttribute('role', 'dialog');
        chatWindow.setAttribute('aria-label', 'Chat conversation');
        chatWindow.innerHTML = buildChatWindowHTML();

        // Append to container
        widgetContainer.appendChild(chatWindow);
        widgetContainer.appendChild(toggleButton);

        // Append to body
        document.body.appendChild(widgetContainer);

        // Get references
        messageContainer = chatWindow.querySelector('.agntcy-chat-messages');
        inputField = chatWindow.querySelector('textarea');
        sendButton = chatWindow.querySelector('.agntcy-chat-input button');

        // Render stored messages
        renderMessages();

        // Add greeting if no messages
        if (messages.length === 0) {
            addMessage('agent', strings.greeting);
        }
    }

    /**
     * Build chat window HTML.
     */
    function buildChatWindowHTML() {
        const avatarInitial = config.agentName.charAt(0).toUpperCase();

        return `
            <div class="agntcy-chat-header">
                <div class="agntcy-chat-header-avatar" aria-hidden="true">
                    ${config.agentAvatar ? `<img src="${config.agentAvatar}" alt="">` : avatarInitial}
                </div>
                <div class="agntcy-chat-header-info">
                    <div class="agntcy-chat-header-name">${escapeHtml(config.agentName)}</div>
                    <div class="agntcy-chat-header-status">Online</div>
                </div>
                <div class="agntcy-chat-header-actions">
                    <button type="button" class="minimize-btn" aria-label="${strings.minimize}">
                        <svg viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
                    </button>
                    <button type="button" class="close-btn" aria-label="${strings.close}">
                        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                    </button>
                </div>
            </div>
            <div class="agntcy-chat-messages" aria-live="polite" aria-relevant="additions">
            </div>
            <div class="agntcy-chat-input">
                <textarea
                    placeholder="${escapeHtml(strings.placeholder)}"
                    aria-label="${escapeHtml(strings.placeholder)}"
                    rows="1"
                    maxlength="${config.maxMessageLength}"
                ></textarea>
                <button type="button" aria-label="${strings.sendButton}" disabled>
                    <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                </button>
            </div>
            ${config.showPoweredBy ? `
                <div class="agntcy-chat-footer">
                    <a href="https://github.com/AGNTCY" target="_blank" rel="noopener">${strings.poweredBy}</a>
                </div>
            ` : ''}
        `;
    }

    // ========================================================================
    // Event Handling
    // ========================================================================

    /**
     * Bind all event listeners.
     */
    function bindEvents() {
        // Toggle button
        toggleButton.addEventListener('click', () => {
            if (isOpen) {
                closeChat();
            } else {
                openChat();
            }
        });

        // Close button
        chatWindow.querySelector('.close-btn').addEventListener('click', closeChat);

        // Minimize button
        chatWindow.querySelector('.minimize-btn').addEventListener('click', closeChat);

        // Input field
        inputField.addEventListener('input', handleInput);
        inputField.addEventListener('keydown', handleKeyDown);

        // Send button
        sendButton.addEventListener('click', sendMessage);

        // Auto-resize textarea
        inputField.addEventListener('input', () => {
            inputField.style.height = 'auto';
            inputField.style.height = Math.min(inputField.scrollHeight, 100) + 'px';
        });

        // Keyboard navigation
        chatWindow.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeChat();
            }
        });
    }

    /**
     * Handle input changes.
     */
    function handleInput() {
        sendButton.disabled = !inputField.value.trim();
    }

    /**
     * Handle keyboard events in input.
     */
    function handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendButton.disabled) {
                sendMessage();
            }
        }
    }

    // ========================================================================
    // Chat Operations
    // ========================================================================

    /**
     * Open the chat window.
     */
    function openChat() {
        isOpen = true;
        chatWindow.classList.add('open');
        toggleButton.classList.add('open');
        toggleButton.setAttribute('aria-expanded', 'true');
        widgetContainer.classList.add('open');
        inputField.focus();
        scrollToBottom();
    }

    /**
     * Close the chat window.
     */
    function closeChat() {
        isOpen = false;
        chatWindow.classList.remove('open');
        toggleButton.classList.remove('open');
        toggleButton.setAttribute('aria-expanded', 'false');
        widgetContainer.classList.remove('open');
        toggleButton.focus();
    }

    /**
     * Send a message.
     */
    async function sendMessage() {
        const text = inputField.value.trim();
        if (!text) return;

        // Clear input
        inputField.value = '';
        inputField.style.height = 'auto';
        sendButton.disabled = true;

        // Add user message
        addMessage('user', text);

        // Show typing indicator
        showTypingIndicator();

        try {
            // Call API
            const response = await callChatApi(text);

            // Hide typing indicator
            hideTypingIndicator();

            // Add agent response
            addMessage('agent', response.response);

            // Update session if auth level changed
            if (response.auth_level && response.auth_level !== authLevel) {
                updateAuthLevel(response.auth_level);
            }

            // Reset retry count
            retryCount = 0;

        } catch (error) {
            console.error('[AGNTCY Chat] API error:', error);
            hideTypingIndicator();

            if (retryCount < MAX_RETRIES) {
                retryCount++;
                addMessage('agent', strings.connectionError);
                // Retry after delay
                setTimeout(() => sendMessageRetry(text), 2000);
            } else {
                addMessage('agent', 'Unable to connect. Please try again later.');
                retryCount = 0;
            }
        }
    }

    /**
     * Retry sending a message.
     */
    async function sendMessageRetry(text) {
        showTypingIndicator();
        try {
            const response = await callChatApi(text);
            hideTypingIndicator();
            addMessage('agent', response.response);
            retryCount = 0;
        } catch (error) {
            hideTypingIndicator();
            if (retryCount < MAX_RETRIES) {
                retryCount++;
                setTimeout(() => sendMessageRetry(text), 2000 * retryCount);
            }
        }
    }

    /**
     * Call the chat API.
     */
    async function callChatApi(message) {
        const response = await fetch(`${config.apiEndpoint}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                session_id: sessionId,
                language: config.language,
                merchant_id: config.merchantId,
            }),
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        // Update session ID if changed
        if (data.session_id && data.session_id !== sessionId) {
            sessionId = data.session_id;
            saveSession();
        }

        return data;
    }

    // ========================================================================
    // Message Rendering
    // ========================================================================

    /**
     * Add a message to the chat.
     */
    function addMessage(role, text) {
        const message = {
            id: Date.now().toString(),
            role,
            text,
            timestamp: new Date().toISOString(),
        };

        messages.push(message);
        saveSession();
        renderMessage(message);
        scrollToBottom();
    }

    /**
     * Render all stored messages.
     */
    function renderMessages() {
        messageContainer.innerHTML = '';
        messages.forEach(renderMessage);
    }

    /**
     * Render a single message.
     */
    function renderMessage(message) {
        const div = document.createElement('div');
        div.className = `agntcy-chat-message ${message.role}`;
        div.setAttribute('role', 'log');

        let html = `<div class="agntcy-chat-message-text">${escapeHtml(message.text)}</div>`;

        if (config.showTimestamps) {
            const time = new Date(message.timestamp).toLocaleTimeString(config.language, {
                hour: 'numeric',
                minute: '2-digit',
            });
            html += `<div class="agntcy-chat-message-time">${time}</div>`;
        }

        div.innerHTML = html;
        messageContainer.appendChild(div);
    }

    /**
     * Show typing indicator.
     */
    function showTypingIndicator() {
        if (isTyping) return;
        isTyping = true;

        const indicator = document.createElement('div');
        indicator.className = 'agntcy-chat-typing';
        indicator.id = 'agntcy-typing-indicator';
        indicator.setAttribute('aria-label', strings.typingIndicator);
        indicator.innerHTML = '<span></span><span></span><span></span>';

        messageContainer.appendChild(indicator);
        scrollToBottom();
    }

    /**
     * Hide typing indicator.
     */
    function hideTypingIndicator() {
        isTyping = false;
        const indicator = document.getElementById('agntcy-typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Scroll messages to bottom.
     */
    function scrollToBottom() {
        if (messageContainer) {
            messageContainer.scrollTop = messageContainer.scrollHeight;
        }
    }

    // ========================================================================
    // Utility Functions
    // ========================================================================

    /**
     * Escape HTML to prevent XSS.
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ========================================================================
    // Public API
    // ========================================================================

    /**
     * @namespace AGNTCYChat
     * @description Public API for the AGNTCY Chat Widget.
     *
     * The widget exposes these methods for programmatic control:
     * - init(): Initialize the widget with configuration
     * - open(): Open the chat window
     * - close(): Close the chat window
     * - toggle(): Toggle chat window visibility
     * - sendMessage(): Send a message programmatically
     * - getSession(): Get current session information
     * - clearSession(): Clear session and start fresh
     *
     * @example
     * // Initialize with minimal config
     * AGNTCYChat.init({ merchantId: 'shop-123' });
     *
     * @example
     * // Initialize with full config
     * AGNTCYChat.init({
     *   merchantId: 'shop-123',
     *   apiEndpoint: 'https://api.example.com/v1',
     *   primaryColor: '#5c6ac4',
     *   position: 'bottom-right',
     *   language: 'en',
     *   agentName: 'Support Bot'
     * });
     *
     * @example
     * // Programmatic control
     * AGNTCYChat.open();    // Open chat window
     * AGNTCYChat.close();   // Close chat window
     * AGNTCYChat.sendMessage('Hello!');  // Send message
     */
    window.AGNTCYChat = {
        /**
         * Initialize the chat widget.
         * @memberof AGNTCYChat
         * @param {Object} options - Configuration options
         * @param {string} options.merchantId - Required. Unique merchant identifier
         * @param {string} [options.apiEndpoint] - API endpoint URL (auto-detected if omitted)
         * @param {string} [options.primaryColor='#5c6ac4'] - Primary theme color
         * @param {string} [options.secondaryColor='#ffffff'] - Secondary theme color
         * @param {string} [options.position='bottom-right'] - Widget position (bottom-right, bottom-left, top-right, top-left)
         * @param {string} [options.language='en'] - Language code (en, fr-CA, es)
         * @param {string} [options.greeting] - Custom greeting message
         * @param {string} [options.placeholder] - Input placeholder text
         * @param {string} [options.agentName='Support Assistant'] - Agent display name
         * @param {string} [options.agentAvatar] - Agent avatar image URL
         * @param {boolean} [options.showTimestamps=true] - Show message timestamps
         * @param {boolean} [options.autoOpen=false] - Auto-open chat on load
         * @param {boolean} [options.showPoweredBy=true] - Show "Powered by AGNTCY" footer
         * @param {number} [options.zIndex=999999] - Widget z-index
         */
        init,

        /**
         * Open the chat window.
         * @memberof AGNTCYChat
         * @returns {void}
         */
        open: openChat,

        /**
         * Close the chat window.
         * @memberof AGNTCYChat
         * @returns {void}
         */
        close: closeChat,

        /**
         * Toggle chat window visibility.
         * @memberof AGNTCYChat
         * @returns {void}
         */
        toggle: () => isOpen ? closeChat() : openChat(),

        /**
         * Send a message programmatically.
         * @memberof AGNTCYChat
         * @param {string} text - Message text to send
         * @returns {void}
         * @example
         * AGNTCYChat.sendMessage('What are your shipping rates?');
         */
        sendMessage: (text) => {
            if (text) {
                inputField.value = text;
                sendMessage();
            }
        },

        /**
         * Get current session information.
         * @memberof AGNTCYChat
         * @returns {Object} Session object
         * @returns {string} return.sessionId - Current session ID
         * @returns {string} return.authLevel - Auth level (anonymous, identified, authenticated)
         * @example
         * const session = AGNTCYChat.getSession();
         * console.log(session.sessionId);  // 'widget-abc123-xyz'
         * console.log(session.authLevel);  // 'anonymous'
         */
        getSession: () => ({ sessionId, authLevel }),

        /**
         * Clear session and start fresh conversation.
         * Removes stored session from localStorage and resets messages.
         * @memberof AGNTCYChat
         * @returns {void}
         */
        clearSession: () => {
            localStorage.removeItem(config.sessionStorageKey);
            createNewSession();
            messages = [];
            if (messageContainer) {
                messageContainer.innerHTML = '';
                addMessage('agent', strings.greeting);
            }
        },

        /**
         * Widget version.
         * @memberof AGNTCYChat
         * @type {string}
         */
        version: VERSION,
    };

    // Auto-init if data-auto-init attribute present
    if (document.currentScript &&
        document.currentScript.hasAttribute('data-auto-init')) {
        document.addEventListener('DOMContentLoaded', () => {
            const merchantId = document.currentScript.getAttribute('data-merchant-id');
            if (merchantId) {
                init({ merchantId });
            }
        });
    }

})(window, document);
