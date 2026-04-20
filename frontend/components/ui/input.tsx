import { cn } from "@/lib/utils";
import { InputHTMLAttributes, forwardRef } from "react";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-8 w-full border border-stroke bg-panel px-3 text-[11px] font-mono text-bright placeholder:text-dim",
        "focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        "rounded-sm tracking-wider",
        className
      )}
      {...props}
    />
  )
);

Input.displayName = "Input";
