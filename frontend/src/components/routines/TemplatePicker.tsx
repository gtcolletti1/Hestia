import { useQuery } from "@tanstack/react-query";
import { routines as routinesApi } from "@/api/endpoints";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import type { RoutineTemplate } from "@/types";

interface Props {
  onSelect: (template: RoutineTemplate | null) => void;
  onCancel: () => void;
}

export default function TemplatePicker({ onSelect, onCancel }: Props) {
  const { data: templates = [], isLoading, error } = useQuery<RoutineTemplate[]>({
    queryKey: ["routine-templates"],
    queryFn: async () => (await routinesApi.getTemplates()).data,
    staleTime: Infinity,
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Pick a template to start from, or build your routine from scratch.
        You can edit anything before saving.
      </p>

      {isLoading && <LoadingSpinner message="Loading templates…" />}

      {error && (
        <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Failed to load templates. You can still start from scratch below.
        </div>
      )}

      {!isLoading && (
        <div className="grid gap-3 sm:grid-cols-2">
          {templates.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              onClick={() => onSelect(tpl)}
              className="flex flex-col items-start gap-1 rounded-2xl border-2 border-gray-200 bg-white p-4 text-left transition hover:border-blue-400 hover:shadow-md active:scale-[0.98] dark:border-gray-700 dark:bg-gray-800 dark:hover:border-blue-500"
            >
              <span className="text-2xl" aria-hidden>{tpl.icon}</span>
              <span className="text-base font-semibold">{tpl.name}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {tpl.description}
              </span>
              <span className="mt-1 text-xs text-gray-400">
                {tpl.steps.length} step{tpl.steps.length !== 1 ? "s" : ""}
              </span>
            </button>
          ))}

          <button
            type="button"
            onClick={() => onSelect(null)}
            className="flex flex-col items-start gap-1 rounded-2xl border-2 border-dashed border-gray-300 bg-white p-4 text-left transition hover:border-blue-400 hover:shadow-md active:scale-[0.98] dark:border-gray-600 dark:bg-gray-800 dark:hover:border-blue-500"
          >
            <span className="text-2xl" aria-hidden>✨</span>
            <span className="text-base font-semibold">Start from scratch</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Build your own routine, step by step.
            </span>
          </button>
        </div>
      )}

      <div className="pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="min-h-[44px] w-full rounded-xl border border-gray-300 py-2 font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
