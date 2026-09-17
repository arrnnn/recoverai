import * as React from "react";

import { cn } from "@/lib/utils";

const TONE_CLASSES = {
  default: "bg-card text-card-foreground border border-border",
  lavender: "bg-lavender text-lavender-fg border-0",
  blue: "bg-blue text-blue-fg border-0",
  rose: "bg-rose text-rose-fg border-0",
  ink: "bg-ink text-white border-0",
} as const;

type Tone = keyof typeof TONE_CLASSES;

function Card({
  className,
  tone = "default",
  ...props
}: React.ComponentProps<"div"> & { tone?: Tone }) {
  return (
    <div
      data-slot="card"
      className={cn(
        "flex flex-col gap-5 rounded-[1.75rem] p-6 shadow-[0_2px_16px_-6px_rgba(22,21,29,0.08)]",
        TONE_CLASSES[tone],
        className
      )}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div data-slot="card-header" className={cn("flex flex-col gap-1", className)} {...props} />
  );
}

function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn("text-base font-bold leading-none", className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-sm opacity-70", className)}
      {...props}
    />
  );
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="card-content" className={cn(className)} {...props} />;
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div data-slot="card-footer" className={cn("flex items-center", className)} {...props} />
  );
}

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };