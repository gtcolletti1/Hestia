import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      {icon && (
        <div className="text-5xl text-gray-300 dark:text-gray-600">{icon}</div>
      )}
      <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
        {title}
      </h3>
      {description && (
        <p className="max-w-sm text-sm text-gray-500 dark:text-gray-400">
          {description}
        </p>
      )}
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="touch-target mt-2 rounded-lg bg-[var(--color-accent)] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-light)] active:scale-95"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
