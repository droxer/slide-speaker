# Style Organization

This document explains how the SCSS files are organized in the project.

## Directory Structure

```
styles/
├── app.scss                 # Core application styles and resets
├── index.scss               # Main entry point that imports all styles
├── components/             # Component-specific styles
│   ├── GoogleLoginButton.scss
│   ├── task-detail.scss
│   ├── TaskMonitor.scss
│   ├── TaskProcessingModal.scss
│   └── TaskProcessingSteps.scss
├── themes/                 # Theme-specific styles
│   ├── light-theme.scss
│   └── dark-theme.scss
├── layout/                 # Layout and grid system styles (currently empty)
├── pages/                  # Page-specific styles (currently empty)
└── utilities/              # Utility classes and mixins (currently empty)
```

## Import Order

Styles are imported in the following order in `index.scss`:

1. Core styles and resets (`app.scss`)
2. Theme styles (`themes/`)
3. Component styles (`components/`)

## Naming Convention

- Component files are named using PascalCase and match the component name (e.g., `TaskMonitor.scss` for `TaskMonitor.tsx`)
- Theme files are prefixed with the theme name (e.g., `dark-theme.scss`)
- Utility files should be named descriptively (e.g., `mixins.scss`, `variables.scss`)

## Best Practices

1. Each component should have its own SCSS file in the `components/` directory
2. Theme-specific overrides should be placed in the appropriate theme file
3. Utility classes and mixins should be placed in the `utilities/` directory
4. Layout-related styles should be placed in the `layout/` directory
5. Page-specific styles should be placed in the `pages/` directory

This organization makes it easier to locate and maintain styles, and follows common conventions used in modern web development.