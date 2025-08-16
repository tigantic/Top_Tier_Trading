import React from 'react';
import DesignSystemPlaceholder from '../components/DesignSystemPlaceholder';

/**
 * Metrics Dashboard (Placeholder)
 *
 * This page displays a placeholder dashboard for future metrics.  It
 * imports the `DesignSystemPlaceholder` component to show where the
 * real dashboard will live once shadcn/ui and Radix components are
 * installed.  Offline, this page demonstrates that the ops UI
 * scaffolding compiles and renders without network access.
 */
export default function MetricsPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold mb-4">Ops Metrics Dashboard (Placeholder)</h1>
      <div className="grid grid-cols-1 gap-4">
        {/* Card placeholder for metrics visualization */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
          <DesignSystemPlaceholder />
        </div>
      </div>
    </div>
  );
}