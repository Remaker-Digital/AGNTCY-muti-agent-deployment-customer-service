# Chat Widget Integration Guide

This guide explains how to integrate the AGNTCY Chat Widget into merchant websites for customer service interactions.

## Overview

The AGNTCY Chat Widget is an embeddable JavaScript module that provides:
- Real-time customer support chat
- Session persistence across page navigation
- Multi-language support (English, French Canadian, Spanish)
- Customizable theming via CSS variables
- OAuth authentication integration with Shopify Customer Accounts
- WCAG 2.1 accessibility compliance

## Quick Start

### 1. Get Embed Code

Use the API to generate your embed code:

```bash
curl -X POST https://api.example.com/api/v1/widget/embed-code \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "your-merchant-id",
    "primary_color": "#5c6ac4",
    "position": "bottom-right",
    "language": "en"
  }'
```

### 2. Add to Website

Copy the generated snippet into your website's HTML, just before the closing `</body>` tag:

```html
<!-- AGNTCY Chat Widget -->
<script src="https://cdn.agntcy.io/widget/agntcy-chat.min.js" async></script>
<script>
  window.addEventListener('load', function() {
    AGNTCYChat.init({
      merchantId: "your-merchant-id",
      primaryColor: "#5c6ac4",
      position: "bottom-right",
      language: "en"
    });
  });
</script>
<!-- End AGNTCY Chat Widget -->
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `merchantId` | string | required | Your unique merchant identifier |
| `primaryColor` | string | `#5c6ac4` | Primary brand color (hex) |
| `secondaryColor` | string | `#ffffff` | Secondary/background color |
| `position` | string | `bottom-right` | Widget position (`bottom-right`, `bottom-left`) |
| `language` | string | `en` | Default language (`en`, `fr-CA`, `es`) |
| `greeting` | string | varies | Custom greeting message |
| `placeholder` | string | varies | Input placeholder text |
| `showTimestamps` | boolean | `true` | Show message timestamps |
| `showPoweredBy` | boolean | `true` | Show "Powered by AGNTCY" footer |
| `autoOpen` | boolean | `false` | Auto-open widget on page load |
| `zIndex` | number | `999999` | CSS z-index for layering |
| `agentName` | string | `Support Assistant` | Agent display name |
| `agentAvatar` | string | null | URL to agent avatar image |
| `logoUrl` | string | null | URL to custom logo |

## Advanced Configuration

### Custom Theming

Override CSS variables for complete control:

```css
:root {
  --agntcy-primary-color: #your-brand-color;
  --agntcy-secondary-color: #ffffff;
  --agntcy-text-color: #212b36;
  --agntcy-bg-color: #ffffff;
  --agntcy-border-radius: 12px;
  --agntcy-font-family: 'Your Font', sans-serif;
}
```

### Dark Mode

Add the `theme-dark` class to enable dark mode:

```javascript
AGNTCYChat.init({
  merchantId: "your-merchant-id",
  // other options...
});

// Enable dark mode
document.querySelector('.agntcy-widget-container')?.classList.add('theme-dark');
```

### Multi-Language Support

The widget supports three languages:

```javascript
// English (default)
AGNTCYChat.init({ language: 'en' });

// French Canadian
AGNTCYChat.init({ language: 'fr-CA' });

// Spanish
AGNTCYChat.init({ language: 'es' });
```

## JavaScript API

### Methods

```javascript
// Initialize the widget
AGNTCYChat.init(options);

// Open the chat window
AGNTCYChat.open();

// Close the chat window
AGNTCYChat.close();

// Toggle the chat window
AGNTCYChat.toggle();

// Send a message programmatically
AGNTCYChat.sendMessage('Hello, I need help!');

// Get current session info
const session = AGNTCYChat.getSession();

// Clear session and start fresh
AGNTCYChat.clearSession();

// Update configuration dynamically
AGNTCYChat.updateConfig({ primaryColor: '#ff5722' });

// Destroy the widget completely
AGNTCYChat.destroy();
```

### Events

```javascript
// Listen for widget events
window.addEventListener('agntcy:message:sent', (event) => {
  console.log('User sent:', event.detail.message);
});

window.addEventListener('agntcy:message:received', (event) => {
  console.log('Agent replied:', event.detail.message);
});

window.addEventListener('agntcy:widget:opened', () => {
  console.log('Widget opened');
});

window.addEventListener('agntcy:widget:closed', () => {
  console.log('Widget closed');
});

window.addEventListener('agntcy:session:authenticated', (event) => {
  console.log('User authenticated:', event.detail.customerName);
});
```

## Authentication Integration

### Shopify Customer Accounts

Enable login for personalized experiences:

```javascript
AGNTCYChat.init({
  merchantId: "your-merchant-id",
  enableAuth: true,
  shopifyStore: "your-store.myshopify.com"
});
```

When a user authenticates:
1. Widget displays "Login" button
2. User redirects to Shopify login
3. Returns with authenticated session
4. Access to order history and personalized support

### Session Levels

| Level | Capabilities |
|-------|--------------|
| Anonymous | General inquiries, product questions |
| Identified | Order lookup by email, basic personalization |
| Authenticated | Full order history, modify orders, payment info |

## API Endpoints

### Widget Configuration

```
GET /api/v1/widget/config/{merchant_id}
```

Returns merchant-specific widget configuration.

### Session Management

```
POST /api/v1/widget/sessions
```

Creates a new anonymous session.

```
GET /api/v1/widget/sessions/{session_id}
```

Retrieves session information.

### Embed Code Generation

```
POST /api/v1/widget/embed-code
```

Generates copy-paste ready embed code.

```
GET /api/v1/widget/embed-code/{merchant_id}
```

Alternative GET endpoint with query parameters.

### Authentication

```
POST /api/v1/widget/auth/login
```

Initiates OAuth flow with Shopify.

```
POST /api/v1/widget/auth/callback
```

Handles OAuth callback and upgrades session.

## Build and Deployment

### Local Development

```bash
cd widget
npm install
npm run dev
```

### Production Build

```bash
npm run build
```

Outputs:
- `dist/agntcy-chat.min.js` - Minified for production
- `dist/agntcy-chat.esm.js` - ES Module for bundlers
- `dist/agntcy-chat.js` - Unminified for debugging

### CDN Deployment

```bash
npm run deploy
```

Uploads to Azure Blob Storage and purges CDN cache.

## Accessibility

The widget follows WCAG 2.1 AA guidelines:
- Keyboard navigation support
- Screen reader announcements
- Focus management
- Color contrast compliance
- Reduced motion support

## Security Considerations

1. **Session Tokens**: Stored in localStorage, expire after 7 days
2. **CORS**: Widget accepts messages only from configured origins
3. **OAuth**: Uses PKCE flow for secure authentication
4. **XSS Prevention**: All user input is sanitized before display
5. **CSP**: Compatible with strict Content Security Policies

## Troubleshooting

### Widget Not Appearing

1. Check browser console for JavaScript errors
2. Verify merchantId is correct
3. Ensure script is loaded (check Network tab)
4. Check z-index conflicts with other elements

### Session Not Persisting

1. Verify localStorage is available
2. Check for privacy mode / incognito
3. Ensure cookies are not blocked

### Authentication Failing

1. Verify Shopify store URL is correct
2. Check OAuth redirect URI configuration
3. Review browser console for CORS errors

## Support

- Documentation: https://docs.agntcy.io/widget
- GitHub Issues: https://github.com/agntcy/chat-widget/issues
- Email: support@agntcy.io

## Changelog

### v1.0.0 (Phase 6)
- Initial release
- Core chat functionality
- Session management (Anonymous → Identified → Authenticated)
- Multi-language support (en, fr-CA, es)
- Shopify Customer Accounts integration
- CDN deployment via Azure Blob Storage + CDN

### Planned: v1.1.0 (Phase 7)
- File upload support
- Voice input (Web Speech API)
- Rich message types (cards, carousels)
- Headless API mode
