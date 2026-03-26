/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2024-present ClaudePlane contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * Modified: Removed third-party brand logos, replaced with ClaudePlane branding.
 */

import React from "react";

export function AuthFooter() {
  return (
    <div className="flex flex-col items-center gap-3 mt-4">
      <span className="text-13 text-tertiary">
        AI-Native Project Management
      </span>
      <span className="text-xs text-quaternary">
        Powered by Claude
      </span>
    </div>
  );
}
