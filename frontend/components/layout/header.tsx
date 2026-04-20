interface HeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export function Header({ title, description, actions }: HeaderProps) {
  return (
    <div
      className="flex items-center justify-between border-b border-stroke px-6 py-4"
      style={{ background: "rgba(13,19,36,0.8)", backdropFilter: "blur(8px)" }}
    >
      <div>
        <div className="flex items-center gap-3">
          <span className="text-dim font-mono text-[10px] tracking-[0.25em] uppercase">▸</span>
          <h1 className="text-sm font-semibold text-bright tracking-[0.08em] uppercase font-mono">
            {title}
          </h1>
        </div>
        {description && (
          <p className="text-[11px] text-muted mt-0.5 font-mono tracking-wider ml-5">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
