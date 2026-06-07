"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui";

export function SituationInput() {
  const [value, setValue] = useState("");
  const router = useRouter();

  function submit() {
    const trimmed = value.trim();
    if (!trimmed) return;
    router.push(`/chat?q=${encodeURIComponent(trimmed)}`);
  }

  return (
    <Input
      big
      placeholder="What is asking for your attention today?"
      value={value}
      onChange={setValue}
      onSubmit={submit}
    />
  );
}
