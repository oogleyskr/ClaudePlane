/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2024-present Glider contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * Modified: Clean Glider branding with fork attribution.
 */

import React from "react";

export function AuthFooter() {
  return (
    <div className="flex flex-col items-center gap-2 mt-4">
      <span className="text-13 text-tertiary">
        Project Management
      </span>
      <span className="text-[10px] text-quaternary">
        Powered by AI
      </span>
      <span className="text-[9px] text-quaternary/60 mt-2">
        A fork of <a href="https://plane.so" target="_blank" rel="noopener noreferrer" className="hover:underline">Plane</a> &middot; made by oogley with &hearts;
      </span>
    </div>
  );
}
