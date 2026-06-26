export type Theme = "light" | "dark";

interface Props {
  theme: Theme;
  onToggle: () => void;
  compact?: boolean;
}

export default function ThemeToggle({ theme, onToggle, compact = false }: Props) {
  const isDark = theme === "dark";

  return (
    <button
      className={`theme-toggle ${compact ? "theme-toggle-compact" : ""}`}
      type="button"
      onClick={onToggle}
      aria-label={isDark ? "切换到白天模式" : "切换到黑夜模式"}
      aria-pressed={isDark}
      title={isDark ? "切换到白天模式" : "切换到黑夜模式"}
    >
      <span className="theme-toggle-icon" aria-hidden="true">{isDark ? "☀" : "☾"}</span>
      {!compact && <span>{isDark ? "白天模式" : "黑夜模式"}</span>}
    </button>
  );
}
