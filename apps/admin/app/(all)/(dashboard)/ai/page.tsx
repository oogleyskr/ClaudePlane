/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// hooks
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// components
import { AIProviderStatus } from "@/components/ai-provider-status";
// local
import { InstanceAIForm } from "./form";

const InstanceAIPage = observer(function InstanceAIPage(_props: Route.ComponentProps) {
  // store
  const { fetchInstanceConfigurations, formattedConfig } = useInstance();

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  return (
    <PageWrapper
      header={{
        title: "ClaudePlane AI Configuration",
        description: "Configure your AI API credentials so ClaudePlane AI features are turned on for all your workspaces.",
      }}
    >
      {formattedConfig ? (
        <>
          <div className="mb-6">
            <AIProviderStatus />
          </div>
          <InstanceAIForm config={formattedConfig} />
        </>
      ) : (
        <Loader className="space-y-8">
          <Loader.Item height="50px" width="40%" />
          <div className="grid w-2/3 grid-cols-2 gap-x-8 gap-y-4">
            <Loader.Item height="50px" />
            <Loader.Item height="50px" />
          </div>
          <Loader.Item height="50px" width="20%" />
        </Loader>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "ClaudePlane AI Configuration - ClaudePlane Admin" }];

export default InstanceAIPage;
