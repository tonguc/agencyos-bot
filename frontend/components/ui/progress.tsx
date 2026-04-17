import { cn } from "@/lib/utils";

interface ProgressProps {
  value: number;
  className?: string;
  color?: "blue" | "green" | "red";
}

export function Progress({ value, className, color = "blue" }: ProgressProps) {
  const colors = {
    blue: "bg-blue-500",
    green: "bg-green-500",
    red: "bg-red-500",
  };
  return (
    <div className={cn("h-1.5 w-full rounded-full bg-slate-100 overflow-hidden", className)}>
      <div
        className={cn("h-full rounded-full transition-all duration-300", colors[color])}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
