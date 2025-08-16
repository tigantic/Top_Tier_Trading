# Ops UI (Placeholder)

This directory is reserved for the operational dashboard built with Next.js and Tailwind CSS.  The dashboard will display live metrics (via Prometheus), logs (via Loki), and health statuses for all services.  It will also offer administrative controls such as toggling live trading and viewing backtest results.

### Design System and Theming

The ops dashboard will adopt a consistent design system based on open‑source
component libraries such as [shadcn/ui](https://ui.shadcn.com/) or
[Radix UI](https://www.radix-ui.com/).  These libraries provide accessible,
headless components that can be composed with your own styles.  Because this
repository is developed offline, external dependencies are not yet installed,
but you can scaffold the integration by defining global CSS variables and
creating placeholder components.  See `components/DesignSystemPlaceholder.tsx`
for an example.

To scaffold the UI in future phases:

1. Initialize a new Next.js project with TypeScript:
   ```sh
   npx create-next-app@latest ops-ui --typescript --app --tailwind
   ```
2. Configure environment variables in `.env.local` to point to the API service.
3. Implement pages/components for metrics, logs, and administrative actions.

This placeholder exists to satisfy the repo layout requirements and will be fleshed out in subsequent phases.

You can prepare for integration by defining CSS variables and a basic theme in
your Tailwind config.  For example, create a global CSS file with custom
properties:

```css
:root {
  --color-primary: #1e90ff;
  --color-secondary: #0066cc;
  --color-bg: #f8f9fa;
  --color-fg: #212529;
  --border-radius: 4px;
}
```

These variables can be referenced throughout your Tailwind or plain CSS
files.  Once you import shadcn/ui or Radix in an online environment, you
can map their component variables to your custom properties and achieve a
cohesive look and feel.  For now, treat this as a TODO item and document
your intended design decisions here.  The placeholder component
`DesignSystemPlaceholder` (see below) is an example of how to scaffold a
component using the anticipated design system imports.

## Using the Placeholder Components

To verify that the ops UI can compile offline, we provide a simple
metrics page and a design system placeholder component.  Start the dev
server (after you have installed dependencies in an online session):

```bash
cd ops-ui
npm install  # only required once when online
npm run dev
```

Then navigate to `/metrics` in your browser to view the
“Ops Metrics Dashboard (Placeholder)” page.  It uses the
`DesignSystemPlaceholder` component inside a simple card layout and
demonstrates how Tailwind classes can be applied without any external
dependencies.  When you are ready to integrate shadcn/ui and
Radix UI, replace the content of `DesignSystemPlaceholder.tsx` and the
metrics page with real components.

### Offline Check

Because this repository is developed offline, you can verify that the
Ops UI compiles and renders without fetching any UI libraries.  After
installing dependencies once (in an online environment), run:

```bash
cd ops-ui
npm run dev
```

The development server will start locally.  Visit `/metrics` to
confirm that the placeholder page renders correctly.  The page relies
only on Tailwind classes; no network calls are made to fetch shadcn/ui
or Radix packages.
