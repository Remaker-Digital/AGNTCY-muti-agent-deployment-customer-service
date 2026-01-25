# User Interface Design Theme Elements

This document describes elements of the style which should be used for all graphical user interfaces in this project, including the console used during development.

**Project**: AGNTCY Multi-Agent Customer Service Platform
**Phase**: All Phases
**Date**: January 24, 2026

---

## Typography

### Fonts
- **Headings (H1-H3)**: Michroma
- **Body Text**: Montserrat
- **Default Text Size**: 15px

---

## Color Palette

### Background Colors
- **Primary Background**: `#18232B` (Dark blue-gray)
- **Foreground/Container Background**: `#243340` (Medium blue-gray)

### Text Colors
- **Body Text**: `#EEEEEE` (Light gray)
- **Headings**: `#FFFFFF` (White)

### Interactive Elements
- **Link Default**: `#FFFFFF` (White)
- **Link Hover**: `#CC2222` (Red)

### Borders
- **Container Border Color**: `#555555` (Medium gray)
- **Container Border Width**: `1px`

---

## Usage Guidelines

### Console Application
The development console (`console/app.py`) should implement these theme elements for consistency with the production user interface design.

### Responsive Considerations
- Maintain minimum text size of 15px for readability
- Ensure sufficient contrast ratio for accessibility (WCAG AA compliance)
- Text color `#EEEEEE` on background `#18232B` provides 11.9:1 contrast ratio ✅

### Component Styling
- All containers should use foreground color `#243340` with `1px` border in `#555555`
- Headings should be white (`#FFFFFF`) using Michroma font
- Body text should be `#EEEEEE` using Montserrat font
- Interactive elements (links, buttons) should use white with red hover state

---

**Last Updated**: January 24, 2026
**Maintained By**: Development Team
**Status**: Active
