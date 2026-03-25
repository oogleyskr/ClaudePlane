/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Modified by oogleyskr: Added Claude Max, custom endpoint, and multi-provider support.
 */

import { useForm } from "react-hook-form";
import { Lightbulb } from "lucide-react";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IFormattedInstanceConfiguration, TInstanceAIConfigurationKeys } from "@plane/types";
// components
import type { TControllerInputFormField } from "@/components/common/controller-input";
import { ControllerInput } from "@/components/common/controller-input";
// hooks
import { useInstance } from "@/hooks/store";

type IInstanceAIForm = {
  config: IFormattedInstanceConfiguration;
};

type AIFormValues = Record<TInstanceAIConfigurationKeys, string>;

export function InstanceAIForm(props: IInstanceAIForm) {
  const { config } = props;
  // store
  const { updateInstanceConfigurations } = useInstance();
  // form data
  const {
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<AIFormValues>({
    defaultValues: {
      LLM_API_KEY: config["LLM_API_KEY"],
      LLM_MODEL: config["LLM_MODEL"],
      LLM_PROVIDER: config["LLM_PROVIDER"],
      LLM_BASE_URL: config["LLM_BASE_URL"],
    },
  });

  const aiFormFields: TControllerInputFormField[] = [
    {
      key: "LLM_PROVIDER",
      type: "text",
      label: "LLM Provider",
      description: (
        <>
          Provider: <code>claude-max</code> (Claude Max subscription with OAuth),{" "}
          <code>anthropic</code> (Anthropic API key),{" "}
          <code>openai</code> (OpenAI-compatible endpoint for self-hosted models),{" "}
          <code>gemini</code> (Google Gemini)
        </>
      ),
      placeholder: "claude-max",
      error: Boolean(errors.LLM_PROVIDER),
      required: false,
    },
    {
      key: "LLM_MODEL",
      type: "text",
      label: "LLM Model",
      description: (
        <>
          Model ID. For Claude: <code>claude-sonnet-4-6</code>, <code>claude-opus-4-6</code>.
          For custom endpoints, use the model ID your server expects.
        </>
      ),
      placeholder: "claude-sonnet-4-6",
      error: Boolean(errors.LLM_MODEL),
      required: false,
    },
    {
      key: "LLM_API_KEY",
      type: "password",
      label: "API Key",
      description: (
        <>
          API key for your provider. For Claude Max, set to <code>auto</code> to read
          OAuth tokens from the Claude CLI credentials file automatically.
        </>
      ),
      placeholder: "auto",
      error: Boolean(errors.LLM_API_KEY),
      required: false,
    },
    {
      key: "LLM_BASE_URL",
      type: "text",
      label: "Custom Base URL (optional)",
      description: (
        <>
          For self-hosted models (vLLM, SGLang, Ollama, etc.), set the OpenAI-compatible
          API endpoint URL. Leave blank for cloud providers.
        </>
      ),
      placeholder: "http://100.95.10.94:8000/v1",
      error: Boolean(errors.LLM_BASE_URL),
      required: false,
    },
  ];

  const onSubmit = async (formData: AIFormValues) => {
    const payload: Partial<AIFormValues> = { ...formData };

    await updateInstanceConfigurations(payload)
      .then(() =>
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Success",
          message: "AI Settings updated successfully",
        })
      )
      .catch((err) => console.error(err));
  };

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <div>
          <div className="pb-1 text-18 font-medium text-primary">AI Configuration</div>
          <div className="text-13 font-regular text-tertiary">
            Configure your AI provider. Supports Claude Max (OAuth), Anthropic API,
            self-hosted models via OpenAI-compatible endpoints, and Google Gemini.
          </div>
        </div>
        <div className="grid-col grid w-full grid-cols-1 items-center justify-between gap-x-12 gap-y-8 lg:grid-cols-2">
          {aiFormFields.map((field) => (
            <ControllerInput
              key={field.key}
              control={control}
              type={field.type}
              name={field.key}
              label={field.label}
              description={field.description}
              placeholder={field.placeholder}
              error={field.error}
              required={field.required}
            />
          ))}
        </div>
      </div>

      <div className="flex flex-col items-start gap-4">
        <Button variant="primary" size="lg" onClick={handleSubmit(onSubmit)} loading={isSubmitting}>
          {isSubmitting ? "Saving" : "Save changes"}
        </Button>

        <div className="relative inline-flex items-center gap-1.5 rounded-sm border border-accent-subtle bg-accent-subtle px-4 py-2 text-caption-sm-regular text-accent-secondary">
          <Lightbulb className="size-4" />
          <div>
            Claude Max uses OAuth tokens from your Claude CLI subscription.
            Self-hosted models connect via any OpenAI-compatible API endpoint.
          </div>
        </div>
      </div>
    </div>
  );
}
