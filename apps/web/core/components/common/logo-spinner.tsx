/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2024-present Glider contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * Modified: Replaced Plane logo spinner with a simple CSS spinner.
 */

export function LogoSpinner() {
  return (
    <div className="flex items-center justify-center">
      <div
        className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300"
        style={{ borderTopColor: "#3b82f6" }}
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}
