"use client";

import { useState } from "react";
import { Code2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CopyButton } from "@/components/playground/copy-button";
import { buildSnippet, SNIPPET_LANGS } from "@/lib/code-snippets";
import type { CatalogModel, ChatParams } from "@/lib/playground-types";

export function CodeDialog({ model, prompt, params }: { model?: CatalogModel; prompt: string; params: ChatParams }) {
  const [open, setOpen] = useState(false);
  const gateway = typeof window !== "undefined" ? `${window.location.origin}/gateway` : "https://playground.example.com/gateway";
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={<Button variant="outline" size="sm" aria-label="View code" />}
      >
        <Code2 className="size-3.5" /> View code
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Get code</DialogTitle>
          <DialogDescription>The same request against the playground gateway. Keys are issued per person in Admin.</DialogDescription>
        </DialogHeader>
        {model && (
          <Tabs defaultValue="python">
            <TabsList>
              {SNIPPET_LANGS.map((l) => <TabsTrigger key={l.id} value={l.id}>{l.label}</TabsTrigger>)}
            </TabsList>
            {SNIPPET_LANGS.map((l) => {
              const code = buildSnippet(l.id, model, prompt, params, gateway);
              return (
                <TabsContent key={l.id} value={l.id}>
                  <div className="relative">
                    <pre className="max-h-[420px] overflow-auto rounded-xl border bg-[#0d0d18] p-4 font-mono text-[12.5px] leading-6 text-slate-100" data-testid={`snippet-${l.id}`}>{code}</pre>
                    <div className="absolute right-2 top-2"><CopyButton text={code} /></div>
                  </div>
                </TabsContent>
              );
            })}
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}
