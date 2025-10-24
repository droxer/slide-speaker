# Frontend Technical Stack

## Overview

The SlideSpeaker frontend is a modern React application built with TypeScript, utilizing a comprehensive set of tools and libraries to deliver a responsive, accessible, and performant user experience. The application follows a component-based architecture with centralized state management and internationalization support.

## Core Technologies

### Framework & Language
- **React 18** - Component-based UI library
- **TypeScript** - Typed superset of JavaScript for enhanced code quality and developer experience
- **Next.js** - React framework for production-ready applications with App Router

### State Management
- **Zustand** - Lightweight, scalable state management solution for local state
- **React Query (TanStack Query)** - Server state management for data fetching, caching, and synchronization
- **React Context** - Limited use for theme and session state

### Styling & UI
- **Sass/SCSS** - CSS preprocessor for enhanced styling capabilities
- **CSS Modules** - Scoped styling to prevent conflicts
- **Google Fonts** - Open Sans as the primary font family
- **Responsive Design** - Mobile-first approach with adaptive layouts

### Build & Development Tools
- **Webpack** - Module bundler (via Next.js)
- **Babel** - JavaScript compiler (via Next.js)
- **ESLint** - Code linting and quality enforcement
- **TypeScript Compiler** - Type checking and transpilation
- **pnpm** - Fast, disk space efficient package manager

## Architecture

### Component Structure
```
src/
├── app/                      # Next.js App Router structure
│   ├── [locale]/            # Internationalized routes
│   │   ├── creations/       # Task management pages
│   │   ├── login/           # Authentication pages
│   │   ├── profile/         # User profile pages
│   │   └── tasks/[taskId]/  # Individual task detail pages
│   ├── providers.tsx        # Application providers
│   └── ThemeProviderWrapper.tsx  # Theme provider wrapper
├── components/              # Reusable UI components
│   ├── AudioPlayer/         # Audio playback component
│   ├── VideoPlayer/         # Video playback component
│   ├── PodcastPlayer/       # Podcast audio + transcript component
│   ├── TranscriptList/      # Subtitle/cue display component
│   ├── TaskMonitor/         # Main task dashboard
│   ├── TaskCard/            # Individual task display
│   ├── UploadPanel/         # File upload interface
│   └── ...                  # Additional UI components
├── hooks/                   # Custom React hooks
├── i18n/                    # Internationalization support
├── services/                # API clients and data hooks
├── stores/                  # Zustand state management stores
├── styles/                  # Global and component styles
├── types/                   # TypeScript type definitions
└── utils/                   # Utility functions
```

### State Management Architecture

#### Zustand Stores (`src/stores/`)
Centralized local state management with persistent storage:
- **UI Store** - Modal states, toasts, search filters, pagination
- **Theme Store** - Theme mode and preferences with system integration
- **Task Store** - Task-related state like hidden tasks and defaults
- **Query Integration** - Bridge between Zustand and React Query

#### React Query Hooks (`src/services/queries.ts`)
Server state management for API data:
- **Task Queries** - Fetching and caching task data with smart refetching
- **Download Queries** - Managing download URLs and assets
- **Transcript Queries** - Handling subtitle and transcript data
- **User Profile Queries** - User-specific data with persistence

### Internationalization
- **next-intl** - Internationalization library for Next.js
- **Supported Languages** - English, Chinese (Simplified/Traditional), Thai, Korean, Japanese
- **Locale Detection** - Automatic detection with user preference override
- **Translation Management** - Centralized message catalogs in `src/i18n/messages/`

## Key Libraries & Dependencies

### UI & Components
- **react-toastify** - Notification system
- **next-themes** - Theme management (legacy, being replaced by Zustand)
- **react-dropzone** - Drag and drop file uploads
- **react-intersection-observer** - Scroll-based loading optimization

### Development & Testing
- **Jest** - Testing framework
- **React Testing Library** - Component testing utilities
- **@testing-library/jest-dom** - Custom jest matchers
- **@types/*` - TypeScript definitions

### Utility Libraries
- **clsx** - Conditional CSS class management
- **date-fns** - Date manipulation and formatting
- **lodash** - Utility functions (selective imports)
- **uuid** - Unique identifier generation

## Performance Optimizations

### Code Splitting
- **Dynamic Imports** - Lazy loading of non-critical components
- **Route-based Splitting** - Automatic code splitting by Next.js routes

### Data Fetching
- **Smart Caching** - Configurable stale-while-revalidate strategy
- **Background Polling** - Automatic updates for active tasks
- **Prefetching** - Anticipatory data loading for improved UX

### Rendering Optimizations
- **Memoization** - `React.memo` for component optimization
- **Callback Optimization** - `useCallback` and `useMemo` for performance
- **Virtualization** - Efficient rendering of large lists

## Accessibility Features

### WCAG 2.1 AA Compliance
- **Semantic HTML** - Proper element usage for screen readers
- **Keyboard Navigation** - Full keyboard operability
- **Focus Management** - Logical focus order and visible focus indicators
- **ARIA Attributes** - Accessible Rich Internet Applications support

### High Contrast Themes
- **Light High Contrast** - Enhanced visibility for low vision users
- **Dark High Contrast** - Dark mode with enhanced contrast
- **System Integration** - Automatic detection of system preferences

## Development Workflow

### Scripts
- `pnpm dev` - Start development server
- `pnpm build` - Create production build
- `pnpm start` - Start production server
- `pnpm lint` - Run ESLint
- `pnpm typecheck` - Run TypeScript compiler
- `pnpm check` - Run linting and type checking
- `pnpm test` - Run unit tests

### Code Quality
- **ESLint Configuration** - Modern flat config with TypeScript support
- **TypeScript Strict Mode** - Enhanced type safety
- **Prettier** - Code formatting (via ESLint plugin)
- **Husky** - Git hooks for pre-commit validation

## Browser Support

### Target Browsers
- **Modern Browsers** - Chrome, Firefox, Safari, Edge (last 2 versions)
- **Mobile Support** - iOS Safari, Chrome for Android
- **Progressive Enhancement** - Core functionality without JavaScript

### Polyfills
- **Minimal Polyfills** - Targeting modern browser baseline
- **Next.js Built-ins** - Automatic polyfill management

## Security Considerations

### Content Security
- **CSP Headers** - Configured via Next.js security headers
- **Sanitization** - Input validation and output encoding
- **Dependency Scanning** - Regular security audits

### Authentication
- **NextAuth.js** - Authentication framework
- **JWT** - Token-based session management
- **Secure Cookies** - HttpOnly, Secure, SameSite flags

## Deployment

### Hosting
- **Static Export** - Static site generation capabilities
- **Server-side Rendering** - Dynamic content delivery
- **Edge Runtime** - Global CDN deployment

### Environment Configuration
- **Environment Variables** - Secure configuration management
- **Build-time Variables** - Compile-time configuration
- **Runtime Variables** - Server-side configuration