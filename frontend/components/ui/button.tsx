import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", loading, children, disabled, ...props }, ref) => {
    const base =
      "inline-flex items-center justify-center gap-2 font-mono font-medium tracking-widest uppercase transition-all focus-visible:outline-none disabled:opacity-40 disabled:pointer-events-none rounded-sm border";

    const variants = {
      default:     "bg-accent/10 border-accent text-accent hover:bg-accent/20",
      outline:     "bg-transparent border-stroke-2 text-muted hover:border-accent hover:text-accent",
      ghost:       "border-transparent text-muted hover:text-bright hover:bg-panel-high",
      destructive: "bg-hot/10 border-hot/60 text-hot hover:bg-hot/20",
    };

    const sizes = {
      sm: "h-7 px-3 text-[9px]",
      md: "h-8 px-4 text-[10px]",
      lg: "h-9 px-5 text-[10px]",
    };

    return (
      <button
        ref={ref}
        className={cn(base, variants[variant], sizes[size], className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
