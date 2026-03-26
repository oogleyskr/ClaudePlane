/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
import { PlaneLockup } from "@plane/propel/icons";

export function AuthHeader() {
  return (
    <div className="sticky top-0 flex w-full flex-shrink-0 items-center justify-between gap-6">
      <Link href="/" className="flex items-center gap-2">
        <PlaneLockup height={20} width={95} className="text-primary" />
        <span className="text-sm font-semibold text-primary tracking-tight">Glider</span>
      </Link>
      <span className="text-xs text-secondary">AI-Native Project Management</span>
    </div>
  );
}
