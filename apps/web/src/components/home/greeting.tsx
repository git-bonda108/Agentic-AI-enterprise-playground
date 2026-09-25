"use client";

import { useGreetingWord } from "@/lib/use-client-store";

export function Greeting({ name }: { name: string }) {
  const word = useGreetingWord();
  const first = name.split(" ")[0];
  return (
    <h1 className="text-3xl font-semibold tracking-tight">
      {word}, <span className="gradient-text">{first}</span>
    </h1>
  );
}
